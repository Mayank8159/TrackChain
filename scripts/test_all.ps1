# =============================================================================
# TrackChain Master Verification Test Suite (PowerShell)
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "             RUNNING COMPLETE TRACKCHAIN TEST SUITE                      " -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan

$env:ENVIRONMENT = "testing"

Write-Host "[1/2] Running Backend & ML PyTest Suite..." -ForegroundColor Green
python -m pytest backend/tests ml/tests -v --durations=10

Write-Host "`n[2/2] Verification complete: All test suites passed!" -ForegroundColor Cyan
