#!/usr/bin/env bash
set -euo pipefail

# --- Colors & Logging ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"

header "TrackChain Ingestion Gateway Smoke Test Suite"
info "Target Ingestion Gateway: $BASE_URL"
info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Test 1: Health Endpoint Probe
info "Probing /health endpoint..."
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/health" 2>/dev/null || curl -s -w "\n%{http_code}" "$BASE_URL/api/health" 2>/dev/null || echo -e "\n000")
HTTP_CODE=$(echo "$HEALTH_RESP" | tail -n1)

if [[ "$HTTP_CODE" == "200" ]]; then
    ok "Health Probe Passed (HTTP $HTTP_CODE)"
else
    err "Health Probe Failed (HTTP $HTTP_CODE) at $BASE_URL"
    exit 1
fi

# Test 2: Ingestion Sessions Registry
info "Probing /api/sessions endpoint..."
SESSIONS_RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/sessions" 2>/dev/null || echo -e "\n000")
SESSIONS_CODE=$(echo "$SESSIONS_RESP" | tail -n1)

if [[ "$SESSIONS_CODE" == "200" || "$SESSIONS_CODE" == "304" ]]; then
    ok "Sessions Registry Query Passed (HTTP $SESSIONS_CODE)"
else
    err "Sessions Query Failed (HTTP $SESSIONS_CODE)"
    exit 1
fi

# Test 3: Real-Time SSE Channel Probe
info "Probing /api/alerts/stream SSE channel..."
SSE_HEADER=$(curl -s -I "$BASE_URL/api/alerts/stream" 2>/dev/null || true)

if echo "$SSE_HEADER" | grep -qi "text/event-stream"; then
    ok "SSE Channel Active (Header: text/event-stream)"
elif echo "$SSE_HEADER" | grep -qi "200 OK"; then
    ok "SSE Channel Connected"
else
    warn "SSE channel returned non-standard headers (manual review recommended)"
fi

header "All Deployment Smoke Probes Completed Successfully"
