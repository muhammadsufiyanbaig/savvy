#!/usr/bin/env bash
# Sprint 4 — Step 7: Route53 ALIAS records after ingress LB is ready
# Run: bash scripts/07-setup-dns.sh
set -euo pipefail

DOMAIN="savvy.app"

# Get Zone ID
ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name "$DOMAIN" \
  --query "HostedZones[0].Id" --output text | sed 's|/hostedzone/||')

if [[ -z "$ZONE_ID" ]]; then
  echo "ERROR: No Route53 zone found for $DOMAIN"
  echo "  Run scripts/03-setup-databases.sh first."
  exit 1
fi

# Get NGINX LB hostname
LB_HOST=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

if [[ -z "$LB_HOST" ]]; then
  echo "ERROR: NGINX LoadBalancer not ready yet."
  echo "  Wait a few minutes and re-run."
  exit 1
fi

echo "Zone: $ZONE_ID"
echo "LB Host: $LB_HOST"
echo ""

# Get LB Hosted Zone ID (NLB in us-east-1 = Z26RNL4JYFTOTI)
# See: https://docs.aws.amazon.com/general/latest/gr/elb.html
LB_ZONE_ID="Z26RNL4JYFTOTI"  # NLB us-east-1

create_alias() {
  local SUBDOMAIN=$1
  local FQDN="${SUBDOMAIN}.${DOMAIN}"

  aws route53 change-resource-record-sets \
    --hosted-zone-id "$ZONE_ID" \
    --change-batch "{
      \"Changes\": [{
        \"Action\": \"UPSERT\",
        \"ResourceRecordSet\": {
          \"Name\": \"${FQDN}.\",
          \"Type\": \"A\",
          \"AliasTarget\": {
            \"HostedZoneId\": \"${LB_ZONE_ID}\",
            \"DNSName\": \"${LB_HOST}.\",
            \"EvaluateTargetHealth\": true
          }
        }
      }]
    }"
  echo "  ✅ $FQDN → $LB_HOST"
}

# Root domain A record
aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch "{
    \"Changes\": [{
      \"Action\": \"UPSERT\",
      \"ResourceRecordSet\": {
        \"Name\": \"${DOMAIN}.\",
        \"Type\": \"A\",
        \"AliasTarget\": {
          \"HostedZoneId\": \"${LB_ZONE_ID}\",
          \"DNSName\": \"${LB_HOST}.\",
          \"EvaluateTargetHealth\": true
        }
      }
    }]
  }"
echo "  ✅ $DOMAIN → $LB_HOST"

create_alias "api"
create_alias "www"

echo ""
echo "✅ DNS records set."
echo ""
echo "Wait for cert-manager to issue TLS cert (~2 minutes after DNS propagates):"
echo "  kubectl get certificate -n savvy -w"
echo "  kubectl describe certificaterequest -n savvy"
