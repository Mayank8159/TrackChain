# TrackChain Final Capstone Demo Launcher (tc.v1 SOTA)
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  TrackChain Multi-Modal Edge Intelligence Demo Launcher" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:PYTHONPATH = "$RepoRoot;$($env:PYTHONPATH)"

Write-Host "[INFO] Launching Phase 2.7 Capstone Demo..." -ForegroundColor Yellow
python ml/scripts/final_demo.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Demo completed with status 0 (SUCCESS)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Demo failed with exit code $LASTEXITCODE" -ForegroundColor Red
}
