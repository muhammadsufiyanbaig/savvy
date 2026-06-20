@echo off
title Savvy - Starting...
color 0A
cls

echo.
echo  ███████╗ █████╗ ██╗   ██╗██╗   ██╗██╗   ██╗
echo  ██╔════╝██╔══██╗██║   ██║██║   ██║╚██╗ ██╔╝
echo  ███████╗███████║██║   ██║██║   ██║ ╚████╔╝
echo  ╚════██║██╔══██║╚██╗ ██╔╝╚██╗ ██╔╝  ╚██╔╝
echo  ███████║██║  ██║ ╚████╔╝  ╚████╔╝    ██║
echo  ╚══════╝╚═╝  ╚═╝  ╚═══╝    ╚═══╝     ╚═╝
echo.
echo  Financial Management System - Launcher
echo  ========================================
echo.

:: ── Step 1: Start Docker Desktop if not running ──────────────────────────────
echo [1/5] Checking Docker Desktop...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo       Docker not running. Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo       Waiting for Docker to start
    :docker_wait
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if %errorlevel% neq 0 (
        set /p "dummy=       Still waiting... (press any key to skip wait)" <nul
        echo .
        goto docker_wait
    )
)
echo       Docker is running [OK]
echo.

:: ── Step 2: Start backend services ───────────────────────────────────────────
echo [2/5] Starting backend microservices...
cd /d "C:\Users\I-TECH\OneDrive\Desktop\Projects\Applications\Savvy\microservices"

docker compose up -d >nul 2>&1
if %errorlevel% neq 0 (
    echo       First run or Kafka volume stale - cleaning volumes and retrying...
    docker compose down -v >nul 2>&1
    docker compose up -d
) else (
    echo       All containers started [OK]
)
echo.

:: ── Step 3: Wait for gateway health ──────────────────────────────────────────
echo [3/5] Waiting for services to become healthy...
set attempts=0
:health_wait
set /a attempts+=1
if %attempts% gtr 30 (
    echo       Warning: Services taking long to start. Continuing anyway...
    goto health_done
)
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 3 /nobreak >nul
    echo|set /p="."
    goto health_wait
)
echo.
echo       API Gateway healthy [OK]
:health_done
echo.

:: ── Step 4: Start Next.js frontend ───────────────────────────────────────────
echo [4/5] Starting frontend (Next.js)...
start "Savvy Frontend" cmd /k "cd /d C:\Users\I-TECH\OneDrive\Desktop\Projects\Applications\Savvy\frontend && echo Starting Next.js dev server... && npm run dev"
echo       Frontend starting in new window...
echo.

:: ── Step 5: Wait for frontend then open browser ──────────────────────────────
echo [5/5] Opening browser...
timeout /t 6 /nobreak >nul
:frontend_wait
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    goto frontend_wait
)
start "" http://localhost:3000
echo       Browser opened at http://localhost:3000 [OK]
echo.

:: ── Done ─────────────────────────────────────────────────────────────────────
echo  ========================================
echo   Savvy is running!
echo.
echo   Frontend : http://localhost:3000
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo  ========================================
echo.
echo  Close the "Savvy Frontend" window to stop frontend.
echo  To stop backend: run "Stop Savvy.bat"
echo.
pause
