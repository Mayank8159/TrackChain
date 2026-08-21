#!/usr/bin/env bash
# =============================================================================
# TrackChain Master ML Test Suite Runner (Phase 2.7 tc.v1 SOTA)
# Executes test pyramid: Registry -> Calibration -> Integration -> Fusion -> Robustness -> Roundtrip -> Performance
#
# Usage:
#   chmod +x ml/scripts/test.sh
#   ./ml/scripts/test.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }
header(){ echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}";
          echo -e "${BLUE}  $*${NC}";
          echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"; }

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

header "TrackChain Phase 2.7 — Final Verification Test Suite"

START_TIME=$(date +%s)

# --- 1. Artifact Registry Check ----------------------------------------------
info "[1/8] Testing Model Registry & Artifact Consistency..."
python -m pytest ml/tests/test_final_registry.py -v --tb=short

# --- 2. Calibration Synchronization -----------------------------------------
info "[2/8] Testing Calibration Synchronization ([0,1] domain)..."
python -m pytest ml/tests/test_final_calibration_sync.py -v --tb=short

# --- 3. Multimodal Integration -----------------------------------------------
info "[3/8] Testing Multimodal 5-Model End-to-End Pipeline..."
python -m pytest ml/tests/test_final_integration.py -v --tb=short

# --- 4. Fusion Decision Matrix -----------------------------------------------
info "[4/8] Testing Fusion Decision Truth Table & Cross-Modal Boost..."
python -m pytest ml/tests/test_final_fusion_matrix.py -v --tb=short

# --- 5. Robustness & Stress --------------------------------------------------
info "[5/8] Testing Robustness to Missing/Corrupt/NaN Inputs..."
python -m pytest ml/tests/test_final_robustness.py -v --tb=short

# --- 6. Backend Contract Round-Trip ------------------------------------------
info "[6/8] Testing tc.v1 Schema Serialization & Backend Contract..."
python -m pytest ml/tests/test_final_backend_roundtrip.py -v --tb=short

# --- 7. Edge Deployment Latency & Performance --------------------------------
info "[7/8] Testing Edge Deployment Latency & Performance Benchmarks..."
python -m pytest ml/tests/test_final_edge_performance.py -v --tb=short

# --- 8. Core Unit & Signal Contract Suite ------------------------------------
info "[8/8] Running Complete Unit & Signal Contract Suite..."
python -m pytest ml/tests/test_signal_contract.py ml/tests/test_calibration_sync.py ml/tests/test_vae_evt_normalization.py ml/tests/test_patchcore_enhanced.py ml/tests/test_yolo_custom_pipeline.py -v --tb=short

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

header "Phase 2.7 Verification Summary: All Gates PASSED in ${DURATION}s"
ok "1. Artifact Consistency:   PASSED (checkpoints, exports & manifests valid)"
ok "2. Calibration Sync:       PASSED (all 5 models in [0,1] domain, threshold=0.50)"
ok "3. Multimodal Integration: PASSED (clean, known, novel, compound defects)"
ok "4. Fusion Decision Matrix:  PASSED (truth table & cross-modal 1.5x boost)"
ok "5. Robustness & Safety:    PASSED (missing frames, NaNs, empty segments)"
ok "6. Backend Round-Trip:     PASSED (tc.v1 schema preserved ML -> API -> DB)"
ok "7. Edge Performance:       PASSED (real-time latency budget >= 15 FPS)"
ok "8. Unit & Contract Tests:  PASSED (signal contracts & normalization guards)"
echo ""
ok "TrackChain ML Stack is 100% sealed, verified, and production-ready."
