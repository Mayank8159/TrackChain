#!/usr/bin/env bash
set -euo pipefail

# --- Colors & Logging ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "TrackChain Backend Local Dev Server"
cd "$(dirname "$0")/.."

# Virtual Environment Setup
if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

info "Installing dependencies..."
pip install -q -r requirements.txt

# Robust .env loader function
load_env() {
    local env_file="${1:-.env}"
    if [ -f "$env_file" ]; then
        info "Loading environment from $env_file..."
        set -a
        # shellcheck disable=SC1090
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
    else
        warn "$env_file not found. Using default environment variables."
    fi
}

load_env ".env"

header "Starting Uvicorn (FastAPI)"
ok "Server running at http://localhost:8000"
ok "API Docs available at http://localhost:8000/docs"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
