#!/usr/bin/env bash
# Savvy — One-click local startup (Linux / macOS / WSL)
# Usage: chmod +x start.sh && ./start.sh

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SVC_DIR="$ROOT/microservices"
FE_DIR="$ROOT/frontend"

echo ""
echo "========================================"
echo "  Savvy — Local Dev Startup"
echo "========================================"
echo ""

# ── 1. Check Docker ───────────────────────────────────────────────────────────
echo "[1/5] Checking Docker..."
if ! docker info &>/dev/null; then
  echo "      ERROR: Docker is not running. Start Docker first."
  exit 1
fi
echo "      Docker OK"

# ── 2. Ensure .env exists ─────────────────────────────────────────────────────
echo "[2/5] Checking .env file..."
if [ ! -f "$SVC_DIR/.env" ]; then
  if [ -f "$SVC_DIR/.env.example" ]; then
    cp "$SVC_DIR/.env.example" "$SVC_DIR/.env"
    echo ""
    echo "  !! .env not found — copied from .env.example"
    echo "  !! REQUIRED: Open microservices/.env and set:"
    echo "  !!   SECRET_KEY  (generate: python3 -c \"import secrets; print(secrets.token_hex(32))\")"
    echo "  !!   ANTHROPIC_API_KEY"
    echo "  !!   AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY"
    echo ""
    read -p "  Continue anyway with defaults? [y/N] " ans
    if [[ "$ans" != "y" && "$ans" != "Y" ]]; then exit 0; fi
  else
    echo "      ERROR: No .env or .env.example found in microservices/"
    exit 1
  fi
else
  echo "      .env found OK"
fi

# ── 3. Ensure frontend/.env.local exists ─────────────────────────────────────
echo "[3/5] Checking frontend env..."
if [ ! -f "$FE_DIR/.env.local" ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > "$FE_DIR/.env.local"
  echo "      Created frontend/.env.local"
else
  echo "      frontend/.env.local found OK"
fi

# ── 4. Start Docker Compose ───────────────────────────────────────────────────
echo "[4/5] Starting Docker Compose..."
cd "$SVC_DIR"

echo "      Starting infrastructure..."
docker compose up -d user-db finance-db bank-db notification-db redis zookeeper kafka chromadb

echo "      Waiting 10 seconds for databases to be ready..."
sleep 10

echo "      Starting microservices..."
docker compose up -d
echo "      Docker Compose started OK"

cd "$ROOT"

# ── 5. Start frontend ─────────────────────────────────────────────────────────
echo "[5/5] Starting frontend (Next.js)..."
if ! command -v node &>/dev/null; then
  echo "      WARNING: Node.js not found. Install Node.js 20+ to run the frontend."
else
  cd "$FE_DIR"
  if [ ! -d "node_modules" ]; then
    echo "      Running npm install first..."
    npm install
  fi
  npm run dev &
  FE_PID=$!
  echo "      Frontend started (PID: $FE_PID)"
  cd "$ROOT"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Savvy is starting up!"
echo "========================================"
echo ""
echo "  Frontend      http://localhost:3000"
echo "  API Gateway   http://localhost:8000"
echo "  API Docs      http://localhost:8000/docs"
echo ""
echo "  View logs:    docker compose logs -f  (run from microservices/)"
echo "  Stop Docker:  docker compose down     (run from microservices/)"
echo ""
echo "  NOTE: Services may take 20-30 seconds to fully initialize."
echo ""
