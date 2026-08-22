#!/usr/bin/env bash
set -euo pipefail

# --- Colors & Logging ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "TrackChain Backend Build Pipeline"
cd "$(dirname "$0")/.." # Move to backend root

info "Building ECS Fargate Docker Image..."
docker build -t trackchain-backend:latest -f Dockerfile .
ok "Docker image built successfully"

if [ -d "lambda_layer" ]; then
    info "Packaging Lambda Dependency Layer..."
    cd lambda_layer
    zip -r trackchain-layer.zip python/ > /dev/null
    cd ..
    ok "Lambda layer packaged: lambda_layer/trackchain-layer.zip"
fi

header "Build Complete"
