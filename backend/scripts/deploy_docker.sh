#!/usr/bin/env bash
set -euo pipefail

# --- Colors & Logging ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "Deploying TrackChain Container Infrastructure"
cd "$(dirname "$0")/../.."

info "[1/3] Building Docker containers (FastAPI + TimescaleDB + MinIO)..."
docker compose build

info "[2/3] Starting backend services in detached mode..."
docker compose up -d

info "[3/3] Checking container health status..."
docker compose ps

header "TrackChain Container Stack Live"
ok "API Base URL:       http://localhost:8000"
ok "API Documentation:  http://localhost:8000/docs"
ok "Prometheus Metrics: http://localhost:8000/metrics"
ok "MinIO S3 Console:   http://localhost:9001"
