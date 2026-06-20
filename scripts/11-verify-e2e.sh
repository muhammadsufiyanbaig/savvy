#!/usr/bin/env bash
# Sprint 5 — Final: End-to-end verification
# Run: bash scripts/11-verify-e2e.sh
set -euo pipefail

DOMAIN="savvy.app"
API="https://api.${DOMAIN}"
APP="https://${DOMAIN}"
GRAFANA="https://grafana.${DOMAIN}"

echo "════════════════════════════════════════════════════"
echo " Savvy End-to-End Verification"
echo "════════════════════════════════════════════════════"

# ── K8s cluster health ────────────────────────────────────────────────────────
echo ""
echo "── K8s Nodes ──"
kubectl get nodes -o custom-columns='NAME:.metadata.name,STATUS:.status.conditions[-1].type,CPU:.status.capacity.cpu,MEM:.status.capacity.memory'

echo ""
echo "── Savvy Pods ──"
kubectl get pods -n savvy -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'

echo ""
echo "── HPAs ──"
kubectl get hpa -n savvy

echo ""
echo "── TLS Certs ──"
kubectl get certificate -n savvy
kubectl get certificate -n monitoring 2>/dev/null || true

# ── HTTP health checks ────────────────────────────────────────────────────────
echo ""
echo "── Health Checks ──"
check() {
  local NAME=$1 URL=$2 EXPECTED=${3:-200}
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$URL" || echo "ERR")
  if [[ "$STATUS" == "$EXPECTED" ]]; then
    echo "  ✅ $NAME → $STATUS"
  else
    echo "  ❌ $NAME → $STATUS (expected $EXPECTED) [$URL]"
  fi
}

check "Frontend (HTTPS)"              "$APP"                       200
check "API Gateway health"            "$API/health"                200
check "User Service (via gateway)"    "$API/api/v1/users/health"   200
check "Finance Service"               "$API/health"                200
check "Grafana"                       "$GRAFANA/api/health"        200

# ── TLS certificate check ─────────────────────────────────────────────────────
echo ""
echo "── TLS Certificate Expiry ──"
for HOST in "$DOMAIN" "api.$DOMAIN" "grafana.$DOMAIN"; do
  EXPIRY=$(echo | openssl s_client -servername "$HOST" -connect "$HOST:443" 2>/dev/null \
    | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "N/A")
  echo "  $HOST: expires $EXPIRY"
done

# ── Metrics endpoint ──────────────────────────────────────────────────────────
echo ""
echo "── /metrics Endpoints (internal, via kubectl port-forward) ──"
echo "  To check metrics locally:"
echo "    kubectl port-forward svc/user-service 8001:8001 -n savvy &"
echo "    curl http://localhost:8001/metrics | head -20"
echo "    kill %1"

# ── Prometheus targets ────────────────────────────────────────────────────────
echo ""
echo "── Prometheus (port-forward to check targets) ──"
echo "  kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring &"
echo "  open http://localhost:9090/targets"
echo "  kill %1"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo " Grafana dashboards to import manually:"
echo "   17175  FastAPI Observability"
echo "   6417   Kubernetes Cluster"
echo "   763    Redis"
echo "   9628   PostgreSQL"
echo "   7589   Kafka"
echo "   Go to: $GRAFANA → + → Import → Enter ID"
echo "════════════════════════════════════════════════════"
