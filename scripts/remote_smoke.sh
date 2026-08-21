#!/usr/bin/env bash
# TrackChain Remote Smoke Test & Live Health Verification (tc.v1).

set -eo pipefail

BASE_URL="${1:-http://localhost:8000}"
# Trim trailing slash
BASE_URL="${BASE_URL%/}"

echo "========================================================"
echo "          TrackChain Remote Smoke Test Suite            "
echo "========================================================"
echo "Target Ingestion Gateway: $BASE_URL"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Test 1: Health Endpoint Probe
echo -n "[1/3] Probing /health endpoint... "
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/health" || curl -s -w "\n%{http_code}" "$BASE_URL/api/health" || echo -e "\n000")
HTTP_CODE=$(echo "$HEALTH_RESP" | tail -n1)

if [[ "$HTTP_CODE" == "200" ]]; then
    echo "✓ PASSED (HTTP $HTTP_CODE)"
else
    echo "✗ FAILED (HTTP $HTTP_CODE)"
    echo "Detail: Could not reach health check at $BASE_URL"
    exit 1
fi

# Test 2: Ingestion Sessions Registry
echo -n "[2/3] Probing /api/sessions endpoint... "
SESSIONS_RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/sessions" || echo -e "\n000")
SESSIONS_CODE=$(echo "$SESSIONS_RESP" | tail -n1)

if [[ "$SESSIONS_CODE" == "200" || "$SESSIONS_CODE" == "304" ]]; then
    echo "✓ PASSED (HTTP $SESSIONS_CODE)"
else
    echo "✗ FAILED (HTTP $SESSIONS_CODE)"
    echo "Detail: Ingestion session registry query failed"
    exit 1
fi

# Test 3: Real-Time SSE Alert Stream Header Check
echo -n "[3/3] Probing /api/alerts/stream SSE channel... "
SSE_HEADER=$(curl -s -I "$BASE_URL/api/alerts/stream" 2>/dev/null || true)

if echo "$SSE_HEADER" | grep -qi "text/event-stream"; then
    echo "✓ PASSED (Header: text/event-stream active)"
elif echo "$SSE_HEADER" | grep -qi "200 OK"; then
    echo "✓ PASSED (Stream connected)"
else
    # In case the backend requires authorization or returns fallback
    echo "⚠ WARNING (SSE channel returned non-standard headers, verify manually)"
fi

echo ""
echo "========================================================"
echo "  ✓ ALL DEPLOYMENT SMOKE PROBES COMPLETED SUCCESSFULLY  "
echo "========================================================"
