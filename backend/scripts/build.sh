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
cd "$(dirname "$0")/.."

TARGET="${1:-all}"

if [[ "$TARGET" == "dev" || "$TARGET" == "all" ]]; then
    info "Building Development Docker Image (Dockerfile.dev)..."
    docker build -t trackchain-backend:dev -f Dockerfile.dev .
    ok "Dev image built: trackchain-backend:dev"
fi

if [[ "$TARGET" == "prod" || "$TARGET" == "all" ]]; then
    info "Building Production ECS Fargate Docker Image (Dockerfile)..."
    docker build -t trackchain-backend:latest -f Dockerfile .
    ok "Production image built: trackchain-backend:latest"
fi

if [[ "$TARGET" == "lambda" ]]; then
    info "Building AWS Lambda Image (Dockerfile.lambda)..."
    docker build -t trackchain-backend:lambda -f Dockerfile.lambda .
    ok "Lambda image built: trackchain-backend:lambda"
fi

header "Build Complete"
