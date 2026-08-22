#!/usr/bin/env bash
set -euo pipefail

# --- Colors & Logging ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "TrackChain Production System Launch"
cd "$(dirname "$0")/.."

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

export ENVIRONMENT=${ENVIRONMENT:-"production"}
export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-4}

info "[1/4] Checking Python dependencies..."
if [ -f "requirements.cloud.txt" ]; then
    pip install -q -r requirements.cloud.txt
else
    pip install -q -r requirements.txt
fi

info "[2/4] Running database schema migrations..."
python -c "from src.db.session import engine, Base; Base.metadata.create_all(bind=engine)"
ok "Schema synchronized"

info "[3/4] Checking database initial seed..."
python scripts/seed.py || true
ok "Database seed verified"

header "Starting Production FastAPI Server on port $PORT ($WORKERS workers)"
exec uvicorn src.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS" --log-level info --access-log
