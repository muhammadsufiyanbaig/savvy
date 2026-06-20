#!/usr/bin/env bash
# generate-dev-certs.sh — Create a local CA + per-service TLS certs for mTLS dev testing.
#
# Usage:
#   bash scripts/generate-dev-certs.sh
#
# Output directory: microservices/certs/
#   ca/          — root CA key + cert (DO NOT ship in images)
#   <service>/   — server.key, server.crt, client.key, client.crt for each service
#
# Production note: replace this with cert-manager (K8s) or AWS ACM PCA.
# The docker-compose snippet below shows how to mount certs into containers.
#
# docker-compose mount example (production-like dev):
#
#   api-gateway:
#     volumes:
#       - ./certs/api-gateway/server.key:/certs/server.key:ro
#       - ./certs/api-gateway/server.crt:/certs/server.crt:ro
#       - ./certs/ca/ca.crt:/certs/ca.crt:ro
#     environment:
#       - TLS_KEY=/certs/server.key
#       - TLS_CERT=/certs/server.crt
#       - TLS_CA=/certs/ca.crt
#
# Each downstream service does the same; the api-gateway client cert is presented
# on outbound httpx calls using:
#   httpx.AsyncClient(cert=("/certs/client.crt", "/certs/client.key"), verify="/certs/ca.crt")

set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/.." && pwd)/microservices/certs"
DAYS=365

SERVICES=(
  api-gateway
  user-service
  finance-service
  bank-service
  statement-analysis-service
  ai-recommendation-service
  notification-service
)

echo "==> Generating certs in: $CERT_DIR"
mkdir -p "$CERT_DIR/ca"

# ── Root CA ────────────────────────────────────────────────────────────────────
if [[ ! -f "$CERT_DIR/ca/ca.key" ]]; then
  echo "==> Creating root CA"
  openssl genrsa -out "$CERT_DIR/ca/ca.key" 4096
  openssl req -new -x509 \
    -key "$CERT_DIR/ca/ca.key" \
    -out "$CERT_DIR/ca/ca.crt" \
    -days $((DAYS * 3)) \
    -subj "/CN=Savvy-Dev-CA/O=Savvy/OU=Internal"
else
  echo "==> Root CA already exists — skipping"
fi

# ── Per-service certs ─────────────────────────────────────────────────────────
for SVC in "${SERVICES[@]}"; do
  DIR="$CERT_DIR/$SVC"
  mkdir -p "$DIR"

  echo "==> $SVC"

  # Server cert (for mTLS server side)
  openssl genrsa -out "$DIR/server.key" 2048
  openssl req -new \
    -key "$DIR/server.key" \
    -out "$DIR/server.csr" \
    -subj "/CN=$SVC/O=Savvy/OU=Internal"
  openssl x509 -req \
    -in "$DIR/server.csr" \
    -CA "$CERT_DIR/ca/ca.crt" \
    -CAkey "$CERT_DIR/ca/ca.key" \
    -CAcreateserial \
    -out "$DIR/server.crt" \
    -days $DAYS \
    -extfile <(printf "subjectAltName=DNS:%s,DNS:localhost\n" "$SVC")
  rm "$DIR/server.csr"

  # Client cert (presented by api-gateway when calling this service)
  openssl genrsa -out "$DIR/client.key" 2048
  openssl req -new \
    -key "$DIR/client.key" \
    -out "$DIR/client.csr" \
    -subj "/CN=$SVC-client/O=Savvy/OU=Internal"
  openssl x509 -req \
    -in "$DIR/client.csr" \
    -CA "$CERT_DIR/ca/ca.crt" \
    -CAkey "$CERT_DIR/ca/ca.key" \
    -CAcreateserial \
    -out "$DIR/client.crt" \
    -days $DAYS
  rm "$DIR/client.csr"

  echo "   server.key  server.crt  client.key  client.crt — OK"
done

echo ""
echo "Done. Add microservices/certs/ to .gitignore — never commit private keys."
echo "Mount via docker-compose volumes (see script header) or K8s Secrets."
