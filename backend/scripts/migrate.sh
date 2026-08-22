#!/usr/bin/env bash
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "TrackChain Database Migration"
cd "$(dirname "$0")/.."
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Robust .env loader function
load_env() {
    local env_file="${1:-.env}"
    if [ -f "$env_file" ]; then
        info "Loading environment from $env_file..."
        set -a
        source "$env_file" 2>/dev/null || while IFS= read -r line || [ -n "$line" ]; do
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue
            if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                key="${BASH_REMATCH[1]}"
                val="${BASH_REMATCH[2]}"
                val="${val%\"}"
                val="${val#\"}"
                val="${val%\'}"
                val="${val#\'}"
                export "$key"="$val"
            fi
        done < "$env_file"
        set +a
        ok "Environment variables loaded"
    fi
}

load_env ".env"

if [ "${1:-}" == "create" ]; then
    info "Generating new migration..."
    alembic revision --autogenerate -m "${2:-auto_migration}"
else
    info "Applying migrations to database..."
    alembic upgrade head
fi
ok "Migration complete"
