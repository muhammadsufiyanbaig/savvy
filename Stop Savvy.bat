@echo off
title Savvy - Stopping...
color 0C
cls

echo.
echo  Stopping Savvy...
echo  ==================
echo.

:: Stop Next.js (kill node processes on port 3000)
echo [1/2] Stopping frontend (Next.js)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo       Frontend stopped [OK]
echo.

:: Stop Docker Compose services
echo [2/2] Stopping backend microservices...
cd /d "C:\Users\I-TECH\OneDrive\Desktop\Projects\Applications\Savvy\microservices"
docker compose down
echo       All containers stopped [OK]
echo.

echo  ==================
echo   Savvy stopped.
echo  ==================
echo.
pause
