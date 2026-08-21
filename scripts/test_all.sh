#!/usr/bin/env bash
# =============================================================================
# TrackChain Master Verification Test Suite (Linux / macOS)
# =============================================================================

set -e

echo "========================================================================="
echo "             RUNNING COMPLETE TRACKCHAIN TEST SUITE                      "
echo "========================================================================="

export ENVIRONMENT="testing"

echo "[1/2] Running Backend & ML PyTest Suite..."
python -m pytest backend/tests ml/tests -v --durations=10

echo ""
echo "[2/2] Verification complete: All test suites passed!"
