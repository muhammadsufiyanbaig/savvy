# Savvy — One-click local startup (Windows PowerShell)
# Usage: Right-click → "Run with PowerShell"  OR  PS> .\start.ps1

$ErrorActionPreference = "Stop"
$root    = $PSScriptRoot
$svcDir  = Join-Path $root "microservices"
$feDir   = Join-Path $root "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Savvy — Local Dev Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Docker is running ────────────────────────────────────────────────
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    docker info 2>&1 | Out-Null
    Write-Host "      Docker OK" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Docker Desktop is not running. Start it first." -ForegroundColor Red
    exit 1
}

# ── 2. Ensure microservices/.env exists ───────────────────────────────────────
Write-Host "[2/5] Checking .env file..." -ForegroundColor Yellow
$envFile    = Join-Path $svcDir ".env"
$envExample = Join-Path $svcDir ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host ""
        Write-Host "  !! .env not found — copied from .env.example" -ForegroundColor Yellow
        Write-Host "  !! REQUIRED: Open microservices/.env and set:" -ForegroundColor Yellow
        Write-Host "  !!   SECRET_KEY  (generate: python -c `"import secrets; print(secrets.token_hex(32))`")" -ForegroundColor Yellow
        Write-Host "  !!   ANTHROPIC_API_KEY  (for AI features)" -ForegroundColor Yellow
        Write-Host "  !!   AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY  (for bank statements)" -ForegroundColor Yellow
        Write-Host ""
        $ans = Read-Host "  Continue anyway with defaults? [y/N]"
        if ($ans -ne "y" -and $ans -ne "Y") { exit 0 }
    } else {
        Write-Host "      ERROR: Neither .env nor .env.example found in microservices/" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "      .env found OK" -ForegroundColor Green
}

# ── 3. Ensure frontend/.env.local exists ─────────────────────────────────────
Write-Host "[3/5] Checking frontend env..." -ForegroundColor Yellow
$feEnv = Join-Path $feDir ".env.local"
if (-not (Test-Path $feEnv)) {
    "NEXT_PUBLIC_API_URL=http://localhost:8000" | Out-File -FilePath $feEnv -Encoding utf8
    Write-Host "      Created frontend/.env.local" -ForegroundColor Green
} else {
    Write-Host "      frontend/.env.local found OK" -ForegroundColor Green
}

# ── 4. Start infrastructure + microservices via docker compose ────────────────
Write-Host "[4/5] Starting Docker Compose..." -ForegroundColor Yellow
Set-Location $svcDir

Write-Host "      Starting infrastructure (databases, Redis, Kafka, ChromaDB)..."
docker compose up -d user-db finance-db bank-db notification-db redis zookeeper kafka chromadb
if (-not $?) {
    Write-Host "      ERROR: Infrastructure failed to start. Check: docker compose logs" -ForegroundColor Red
    Set-Location $root
    exit 1
}

Write-Host "      Waiting 10 seconds for databases to be ready..."
Start-Sleep -Seconds 10

Write-Host "      Starting microservices..."
docker compose up -d
if (-not $?) {
    Write-Host "      ERROR: Services failed to start. Check: docker compose logs" -ForegroundColor Red
    Set-Location $root
    exit 1
}

Write-Host "      Docker Compose started OK" -ForegroundColor Green
Set-Location $root

# ── 5. Start frontend in a new terminal window ───────────────────────────────
Write-Host "[5/5] Starting frontend (Next.js)..." -ForegroundColor Yellow

$nodeCheck = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCheck) {
    Write-Host "      WARNING: Node.js not found. Install Node.js 20+ to run the frontend." -ForegroundColor Yellow
    Write-Host "      Skipping frontend startup." -ForegroundColor Yellow
} else {
    $nmPath = Join-Path $feDir "node_modules"
    if (-not (Test-Path $nmPath)) {
        Write-Host "      node_modules not found — running npm install first..."
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$feDir'; npm install; npm run dev" -WindowStyle Normal
    } else {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$feDir'; npm run dev" -WindowStyle Normal
    }
    Write-Host "      Frontend starting in new window..." -ForegroundColor Green
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Savvy is starting up!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend      http://localhost:3000" -ForegroundColor White
Write-Host "  API Gateway   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs      http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  View logs:    docker compose logs -f  (run from microservices/)" -ForegroundColor Gray
Write-Host "  Stop all:     .\stop.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  NOTE: Services may take 20-30 seconds to fully initialize." -ForegroundColor Yellow
Write-Host "        Watch logs if anything is unresponsive." -ForegroundColor Yellow
Write-Host ""
