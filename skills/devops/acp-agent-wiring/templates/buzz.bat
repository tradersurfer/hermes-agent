@echo off
REM ===========================================================================
REM buzz.bat — ONE COMMAND to boot up Buzz: Docker + relay + all 7 agents.
REM
REM Usage:  buzz.bat
REM
REM Handles:
REM   1. Docker Desktop check/start
REM   2. Buzz containers (postgres, redis, minio) start
REM   3. Relay startup on ws://127.0.0.1:3000 (IPv4) via WSL2
REM   4. All 7 department agents with correct identities
REM
REM All processes are fully daemonized (setsid + nohup + disown).
REM After running, open Buzz Desktop or http://localhost:4173 in a browser.
REM ===========================================================================
@echo off
echo === Starting Buzz stack ===

REM --- Step 1: Ensure Docker Desktop ---
echo Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
  echo Starting Docker Desktop...
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  timeout /t 60 /nobreak >nul
  docker info >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Docker failed to start. Please start Docker Desktop manually.
    exit /b 1
  )
)
echo Docker: OK

REM --- Step 2: Start containers ---
echo Starting containers...
docker start buzz-postgres buzz-redis buzz-minio >nul 2>&1
timeout /t 5 /nobreak >nul
echo Containers: started

REM --- Step 3: Relay + Agents via WSL2 ---
echo Launching relay + agents...
wsl.exe -d Ubuntu -- bash /home/jordan/buzzup.sh
timeout /t 90 /nobreak >nul

echo === Buzz startup complete ===
echo Relay: ws://127.0.0.1:3000
echo Agent logs: /home/jordan/buzzlogs/acp_*.log
echo.
echo To launch Buzz Desktop: Open from Windows Start Menu.
