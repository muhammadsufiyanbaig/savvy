#!/usr/bin/env bash
# Sprint 4 — Step 8: Verify full deployment
# Run after DNS propagates and certs are issued.
set -euo pipefail

DOMAIN="savvy.app"
API="https://api.${DOMAIN}"
APP="https://${DOMAIN}"

echo "=== Cluster Nodes ==="
kubectl get nodes -o wide

echo ""
echo "=== Savvy Pods ==="
kubectl get pods -n savvy -o wide

echo ""
echo "=== Services ==="
kubectl get svc -n savvy

echo ""
echo "=== Ingress ==="
kubectl get ingress -n savvy -o wide

echo ""
echo "=== TLS Certificates ==="
kubectl get certificate -n savvy

echo ""
echo "=== HPAs ==="
kubectl get hpa -n savvy

echo ""
echo "=== Health Checks ==="
for SVC_PATH in \
  "api-gateway:$API/health" \
  "user-service:$API/api/v1/users/health" \
  "frontend:$APP"; do
  NAME="${SVC_PATH%%:*}"
  URL="${SVC_PATH#*:}"
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL" || echo "FAIL")
  if [[ "$STATUS" == "200" ]]; then
    echo "  ✅ $NAME → HTTP $STATUS"
  else
    echo "  ❌ $NAME → HTTP $STATUS ($URL)"
  fi
done

echo ""
echo "=== External Secrets ==="
kubectl get externalsecret -n savvy

echo ""
echo "=== Recent Events (errors only) ==="
kubectl get events -n savvy --field-selector type=Warning --sort-by='.lastTimestamp' | tail -20
