# Savvy — Stop all local services
# Usage: PS> .\stop.ps1

$root   = $PSScriptRoot
$svcDir = Join-Path $root "microservices"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Savvy — Stopping all services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $svcDir
docker compose down
Set-Location $root

Write-Host ""
Write-Host "  All Docker services stopped." -ForegroundColor Green
Write-Host "  (Frontend window can be closed manually or Ctrl+C in its terminal)" -ForegroundColor Gray
Write-Host ""
