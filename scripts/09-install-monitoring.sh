#!/usr/bin/env bash
# Sprint 5 — Step 1: Install Prometheus + Grafana via kube-prometheus-stack
# Run: bash scripts/09-install-monitoring.sh
# Prereq: kubectl configured to savvy-cluster, Helm installed
set -euo pipefail

DOMAIN="savvy.app"
GRAFANA_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-CHANGE_ME_grafana_password}"

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo update

echo "Installing kube-prometheus-stack..."
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword="$GRAFANA_PASSWORD" \
  --set grafana.ingress.enabled=true \
  --set grafana.ingress.ingressClassName=nginx \
  --set "grafana.ingress.hosts[0]=grafana.${DOMAIN}" \
  --set "grafana.ingress.tls[0].secretName=grafana-tls" \
  --set "grafana.ingress.tls[0].hosts[0]=grafana.${DOMAIN}" \
  --set "grafana.ingress.annotations.cert-manager\\.io/cluster-issuer=letsencrypt-prod" \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.retentionSize=45GB \
  --set-string prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp2 \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false \
  --wait --timeout=10m

echo "Applying Savvy ServiceMonitor + alerts..."
kubectl apply -f k8s/monitoring/service-monitor.yaml
kubectl apply -f k8s/monitoring/alerts.yaml

echo "Applying Grafana dashboards ConfigMap..."
kubectl apply -f k8s/monitoring/grafana-dashboards.yaml

echo ""
echo "=== Grafana access ==="
echo "  URL: https://grafana.${DOMAIN}"
echo "  User: admin"
echo "  Pass: $GRAFANA_PASSWORD"
echo ""
echo "Waiting for Grafana pod..."
kubectl rollout status deployment/kube-prometheus-stack-grafana -n monitoring --timeout=5m

echo ""
echo "✅ Monitoring stack ready."
echo ""
echo "Next: bash scripts/10-setup-cloudflare.sh"
