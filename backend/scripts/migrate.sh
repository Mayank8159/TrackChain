#!/usr/bin/env bash
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "TrackChain Database Migration"
cd "$(dirname "$0")/.."
source venv/bin/activate

if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

if [ "${1:-}" == "create" ]; then
    info "Generating new migration..."
    alembic revision --autogenerate -m "${2:-auto_migration}"
else
    info "Applying migrations to database..."
    alembic upgrade head
fi
ok "Migration complete"
