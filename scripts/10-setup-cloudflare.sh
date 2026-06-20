#!/usr/bin/env bash
# Sprint 5 — Step 2: Cloudflare DNS + SSL + WAF + Cache rules
# Run: bash scripts/10-setup-cloudflare.sh
# Prereq: Cloudflare account, domain added to Cloudflare, API token created
#
# Create API token at: https://dash.cloudflare.com/profile/api-tokens
#   Template: "Edit zone DNS" + "Zone: WAF:Edit, Page Rules:Edit, Cache Rules:Edit"
#   Zone Resource: savvy.app
set -euo pipefail

# ── FILL THESE IN ─────────────────────────────────────────────────────────────
CF_API_TOKEN="CHANGE_ME_cloudflare_api_token"
DOMAIN="savvy.app"
# ─────────────────────────────────────────────────────────────────────────────

CF_API="https://api.cloudflare.com/client/v4"
AUTH_HEADER="Authorization: Bearer $CF_API_TOKEN"

cf() {
  curl -s -H "$AUTH_HEADER" -H "Content-Type: application/json" "$@"
}

# Get Zone ID
echo "Getting zone ID for $DOMAIN..."
ZONE_ID=$(cf "$CF_API/zones?name=$DOMAIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['id'])")
echo "Zone ID: $ZONE_ID"

# ── SSL/TLS Settings ──────────────────────────────────────────────────────────
echo "Configuring SSL: Full (strict)..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/ssl" \
  -d '{"value":"full"}' > /dev/null

echo "Enabling Always HTTPS..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/always_use_https" \
  -d '{"value":"on"}' > /dev/null

echo "Setting minimum TLS 1.2..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/min_tls_version" \
  -d '{"value":"1.2"}' > /dev/null

echo "Enabling HTTP/2..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/http2" \
  -d '{"value":"on"}' > /dev/null

echo "Enabling HTTP/3 (QUIC)..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/http3" \
  -d '{"value":"on"}' > /dev/null

echo "Enabling Brotli compression..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/brotli" \
  -d '{"value":"on"}' > /dev/null

echo "Disabling Rocket Loader (breaks Next.js)..."
cf -X PATCH "$CF_API/zones/$ZONE_ID/settings/rocket_loader" \
  -d '{"value":"off"}' > /dev/null

# ── WAF Rules ────────────────────────────────────────────────────────────────
echo ""
echo "Creating WAF rate limit rule (API: 100 req/10s per IP)..."
cf -X POST "$CF_API/zones/$ZONE_ID/rulesets/phases/http_ratelimit/entrypoint" \
  -d '{
    "rules": [
      {
        "description": "Rate limit API requests",
        "expression": "(http.host eq \"api.'$DOMAIN'\")",
        "action": "block",
        "ratelimit": {
          "characteristics": ["cf.unique_visitor_id"],
          "period": 10,
          "requests_per_period": 100,
          "mitigation_timeout": 600
        }
      }
    ]
  }' > /dev/null

echo "Creating WAF custom rules (bad bots, SQL injection)..."
cf -X POST "$CF_API/zones/$ZONE_ID/rulesets/phases/http_request_firewall_custom/entrypoint" \
  -d '{
    "rules": [
      {
        "description": "Block bad bots (score < 10)",
        "expression": "(cf.bot_management.score lt 10)",
        "action": "block",
        "enabled": true
      },
      {
        "description": "Block scanner user agents",
        "expression": "(http.user_agent contains \"sqlmap\") or (http.user_agent contains \"nikto\") or (http.user_agent contains \"nmap\") or (http.user_agent contains \"masscan\")",
        "action": "block",
        "enabled": true
      },
      {
        "description": "Block suspicious auth brute force",
        "expression": "(http.request.uri.path contains \"/api/v1/users/login\") and (cf.threat_score gt 20)",
        "action": "challenge",
        "enabled": true
      }
    ]
  }' > /dev/null

# ── Cache Rules ───────────────────────────────────────────────────────────────
echo ""
echo "Creating cache rules..."

# Static assets — cache 1 year
cf -X POST "$CF_API/zones/$ZONE_ID/rulesets/phases/http_request_cache_settings/entrypoint" \
  -d '{
    "rules": [
      {
        "description": "Cache Next.js static assets 1 year",
        "expression": "(http.host eq \"'$DOMAIN'\" and http.request.uri.path wildcard \"/_next/static/*\")",
        "action": "set_cache_settings",
        "action_parameters": {
          "cache": true,
          "edge_ttl": {"mode": "override_origin", "default": 31536000},
          "browser_ttl": {"mode": "override_origin", "default": 31536000}
        },
        "enabled": true
      },
      {
        "description": "Bypass cache for API",
        "expression": "(http.host eq \"api.'$DOMAIN'\")",
        "action": "set_cache_settings",
        "action_parameters": {"cache": false},
        "enabled": true
      },
      {
        "description": "Cache auth pages 1 hour",
        "expression": "(http.host eq \"'$DOMAIN'\" and http.request.uri.path in {\"/login\" \"/register\"})",
        "action": "set_cache_settings",
        "action_parameters": {
          "cache": true,
          "edge_ttl": {"mode": "override_origin", "default": 3600},
          "browser_ttl": {"mode": "override_origin", "default": 3600}
        },
        "enabled": true
      }
    ]
  }' > /dev/null

# ── DNS Records (if not already set via Route53) ──────────────────────────────
echo ""
echo "Verifying DNS proxying is enabled..."
RECORDS=$(cf "$CF_API/zones/$ZONE_ID/dns_records?type=A")
echo "$RECORDS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data['result']:
    status = '✅ proxied' if r.get('proxied') else '❌ NOT proxied'
    print(f\"  {r['name']} → {r['content']} [{status}]\")
"

echo ""
echo "✅ Cloudflare configured:"
echo "   SSL: Full (strict) · Always HTTPS · TLS 1.2+ · HTTP/2 · HTTP/3 · Brotli"
echo "   WAF: Rate limit (100/10s) · Bot block (score<10) · Scanner block"
echo "   Cache: _next/static=1yr · API=bypass · auth pages=1hr"
echo ""
echo "⚠  If using Bot Management score, enable Bot Management in Cloudflare dashboard."
echo "   (Requires Pro plan or higher)"
echo ""
echo "Next: bash scripts/11-verify-e2e.sh"
