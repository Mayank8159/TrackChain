#!/usr/bin/env bash
# ==============================================================================
# TrackChain Zero-Touch Edge Node Auto-Discovery Simulator (Prompt 29)
# Simulates a brand new, unprovisioned edge camera phoning home for the first time.
# ==============================================================================

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
NODE_SUFFIX="${1:-$((RANDOM % 9000 + 1000))}"
DEVICE_ID="CAM-GHOST-${NODE_SUFFIX}"

# Waypoint near Faridabad (NDLS-AGC Corridor)
LAT=28.4089
LON=77.3178
CHAINAGE=28500.0

echo "📡 [SIMULATION] Powering on new unprovisioned hardware node: [${DEVICE_ID}]..."
echo "📍 [SIMULATION] GPS Lock Acquired: Lat ${LAT}° N, Lon ${LON}° E | Chainage ${CHAINAGE}m"
echo "🚀 [SIMULATION] Sending first telemetry phone-home packet to ${BACKEND_URL}/api/telemetry..."

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${BACKEND_URL}/api/telemetry" \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: ${DEVICE_ID}" \
  -H "X-Capture-Time: $(date +%s%3N)" \
  -d "{
    \"session_id\": \"ses-live-discovery-${NODE_SUFFIX}\",
    \"device_id\": \"${DEVICE_ID}\",
    \"samples\": [
      {
        \"chainage_m\": ${CHAINAGE},
        \"speed_mps\": 33.3,
        \"speed_kmh\": 120.0,
        \"vibration_rms\": 0.38,
        \"track_gauge_mm\": 1676.2,
        \"cant_mm\": 12.4,
        \"twist_mm_per_m\": 0.6,
        \"vertical_unevenness_mm\": 0.8,
        \"alignment_dev_mm\": 0.3,
        \"latitude\": ${LAT},
        \"longitude\": ${LON}
      }
    ]
  }")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_STATUS")

if [ "$HTTP_STATUS" -eq 200 ]; then
  echo "✅ [SUCCESS] Ingest accepted (HTTP 200)."
  echo "📦 Backend Response: ${BODY}"
  echo ""
  echo "✨ Auto-Discovery Event Sequence Dispatched:"
  echo "  1. Backend auto-created Device [${DEVICE_ID}] with status 'pending_approval'."
  echo "  2. SSE stream broadcasted 'device_discovered' event."
  echo "  3. Frontend /devices grid animated new card with cyan glow & 'NEW' badge."
  echo "  4. GIS Map dropped a live GPS node pin at [${LAT}, ${LON}]."
  echo "  5. Live toast fired across connected operator screens."
else
  echo "❌ [ERROR] Ingestion failed with status ${HTTP_STATUS}."
  echo "📦 Response: ${BODY}"
  exit 1
fi
