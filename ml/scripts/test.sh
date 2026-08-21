#!/usr/bin/env bash
# =============================================================================
# TrackChain Master ML Test Suite Runner
# Executes full test suite for all 5 Phase 2 models and master fusion pipeline.
#
# Usage:
#   chmod +x ml/scripts/test.sh
#   ./ml/scripts/test.sh [--verbose] [--coverage]
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
header "TrackChain Phase 2 — Master ML Test Suite"

START_TIME=$(date +%s)

# --- Run Complete Test Suite -------------------------------------------------
info "Executing complete test suite across Vision, Geometry, Enhanced Models, and Fusion..."
python -m pytest ml/tests -v --tb=short

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

header "ML Test Suite Execution Summary"
ok "All tests across test modules PASSED in ${DURATION}s."
ok "Phase 2 Multi-Modal ML Intelligence Stack is fully verified and production-ready."
