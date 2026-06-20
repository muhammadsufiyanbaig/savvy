#!/usr/bin/env bash
# Sprint 4 — Step 6: Apply all K8s manifests
# Run: bash scripts/06-deploy.sh
# Prereq: steps 01–05 done, images pushed to GHCR
set -euo pipefail

ORG="${GITHUB_ORG:-YOUR_ORG}"  # set env: export GITHUB_ORG=myorgname

if [[ "$ORG" == "YOUR_ORG" ]]; then
  echo "ERROR: Set GITHUB_ORG env var first:"
  echo "  export GITHUB_ORG=<your-github-username-or-org>"
  exit 1
fi

echo "Deploying Savvy to K8s (org: $ORG)..."

# Replace YOUR_ORG placeholder in all manifests
find k8s/services -name "deployment.yaml" -exec \
  sed -i "s|ghcr.io/YOUR_ORG/|ghcr.io/${ORG}/|g" {} \;

# ── Apply in dependency order ─────────────────────────────────────────────────
echo "1. Namespace..."
kubectl apply -f k8s/namespace.yaml

echo "2. Secrets (External Secrets)..."
kubectl apply -f k8s/secrets/cluster-secret-store.yaml
kubectl apply -f k8s/secrets/external-secret.yaml

echo "Waiting for savvy-secrets to sync..."
kubectl wait externalsecret savvy-secrets -n savvy \
  --for=condition=Ready --timeout=120s

echo "3. Infrastructure (Redis, ChromaDB, Kafka)..."
kubectl apply -f k8s/infrastructure/redis.yaml
kubectl apply -f k8s/infrastructure/chromadb.yaml
kubectl apply -f k8s/infrastructure/kafka/zookeeper.yaml
kubectl apply -f k8s/infrastructure/kafka/kafka.yaml

echo "Waiting for infrastructure pods..."
kubectl rollout status statefulset/redis -n savvy --timeout=3m
kubectl rollout status statefulset/zookeeper -n savvy --timeout=3m
kubectl rollout status statefulset/kafka -n savvy --timeout=5m

echo "4. Services..."
for SVC in api-gateway user-service finance-service bank-service \
           statement-analysis-service ai-recommendation-service \
           notification-service frontend; do
  kubectl apply -f "k8s/services/${SVC}/"
done

echo "Waiting for service rollouts..."
for SVC in api-gateway user-service finance-service bank-service \
           statement-analysis-service ai-recommendation-service \
           notification-service frontend; do
  kubectl rollout status "deployment/${SVC}" -n savvy --timeout=5m
done

echo "5. Ingress..."
kubectl apply -f k8s/ingress/ingress.yaml

echo "6. Monitoring..."
kubectl apply -f k8s/monitoring/service-monitor.yaml
kubectl apply -f k8s/monitoring/alerts.yaml

# ── Status ────────────────────────────────────────────────────────────────────
echo ""
echo "=== Pods ==="
kubectl get pods -n savvy

echo ""
echo "=== Services ==="
kubectl get svc -n savvy

echo ""
echo "=== Ingress ==="
kubectl get ingress -n savvy

echo ""
echo "✅ Savvy deployed!"
echo ""
echo "Next steps:"
echo "  1. Get NGINX LoadBalancer hostname:"
echo "     kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
echo ""
echo "  2. Add Route53 ALIAS records:"
echo "     savvy.app     → ALIAS → above hostname"
echo "     api.savvy.app → ALIAS → above hostname"
echo ""
echo "  3. Wait for cert-manager to issue TLS cert (~2 min after DNS propagates)"
echo "     kubectl describe certificate -n savvy"
