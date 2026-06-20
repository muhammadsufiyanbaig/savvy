#!/usr/bin/env bash
# Sprint 4 — Step 5: K8s add-ons via Helm
# Run: bash scripts/05-install-addons.sh
# Prereq: helm installed  (brew install helm)
#         kubectl configured to savvy-cluster
set -euo pipefail

REGION="us-east-1"
CLUSTER_NAME="savvy-cluster"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Installing K8s add-ons..."
echo ""

# ── Helm repos ────────────────────────────────────────────────────────────────
helm repo add eks              https://aws.github.io/eks-charts          2>/dev/null || true
helm repo add ingress-nginx    https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
helm repo add jetstack         https://charts.jetstack.io                  2>/dev/null || true
helm repo add external-secrets https://charts.external-secrets.io          2>/dev/null || true
helm repo update

# ── AWS Load Balancer Controller ──────────────────────────────────────────────
echo "Installing AWS Load Balancer Controller..."
# IRSA: create IAM role for LBC
eksctl create iamserviceaccount \
  --cluster="$CLUSTER_NAME" \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn="arn:aws:iam::aws:policy/AWSLoadBalancerControllerIAMPolicy" \
  --override-existing-serviceaccounts \
  --approve \
  2>/dev/null || echo "  SA exists"

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --set clusterName="$CLUSTER_NAME" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait

# ── NGINX Ingress ─────────────────────────────────────────────────────────────
echo ""
echo "Installing NGINX Ingress Controller..."
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"=nlb \
  --wait

# Get the LoadBalancer hostname (use for Route53 A record)
echo ""
echo "NGINX LoadBalancer hostname (add as Route53 ALIAS for savvy.app and api.savvy.app):"
kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
echo ""

# ── cert-manager ─────────────────────────────────────────────────────────────
echo ""
echo "Installing cert-manager..."
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true \
  --set replicaCount=2 \
  --wait

echo "Applying ClusterIssuers..."
kubectl apply -f k8s/cert-manager/cluster-issuer.yaml

# ── External Secrets Operator ─────────────────────────────────────────────────
echo ""
echo "Installing External Secrets Operator..."
helm upgrade --install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace \
  --wait

# IRSA for External Secrets Operator to read Secrets Manager
echo "Creating IRSA for external-secrets..."
eksctl create iamserviceaccount \
  --cluster="$CLUSTER_NAME" \
  --namespace=savvy \
  --name=savvy-secrets-sa \
  --attach-policy-arn="arn:aws:iam::${ACCOUNT_ID}:policy/savvy-secrets-read" \
  --override-existing-serviceaccounts \
  --approve \
  2>/dev/null || echo "  SA exists"

# Patch ClusterSecretStore to use IRSA
cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-store
spec:
  provider:
    aws:
      service: SecretsManager
      region: ${REGION}
      auth:
        jwt:
          serviceAccountRef:
            name: savvy-secrets-sa
            namespace: savvy
EOF

echo ""
echo "✅ Add-ons installed."
echo "Next: run scripts/06-deploy.sh"
