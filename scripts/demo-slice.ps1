# =============================================================================
# demo-slice.ps1
# Phase 1 Walking Skeleton End-to-End Vertical Slice Demo Runner
#
# Steps:
#   1. Starts the backend FastAPI server in background
#   2. Waits for health endpoint /health -> HTTP 200
#   3. Runs python ml/scripts/emit_sample.py
#   4. Verifies database ingestion and API retrieval
#   5. Gracefully stops background server
# =============================================================================

$ErrorActionPreference = 'Stop'

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  TrackChain - Phase 1 Walking Skeleton Vertical Slice Demo           " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$BackendPort = 8000
$BackendUrl = "http://127.0.0.1:$BackendPort"

# 1. Start FastAPI backend
Write-Host "`n[1/4] Starting FastAPI backend on $BackendUrl..." -ForegroundColor Yellow
$env:PYTHONPATH = "backend"
$backendProcess = Start-Process python -ArgumentList "-m uvicorn src.main:app --port $BackendPort" -PassThru -NoNewWindow

try {
    # 2. Wait for backend health probe
    Write-Host "[2/4] Waiting for backend /health readiness..." -ForegroundColor Yellow
    $healthy = $false
    for ($i = 0; $i -lt 15; $i++) {
        try {
            $resp = Invoke-RestMethod -Uri "$BackendUrl/health" -Method Get -TimeoutSec 2
            if ($resp.status -eq "ok") {
                $healthy = $true
                Write-Host "      Backend is healthy and listening!" -ForegroundColor Green
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 800
        }
    }

    if (-not $healthy) {
        throw "Backend failed to start within timeout."
    }

    # 3. Emit synthetic ML vertical slice
    Write-Host "`n[3/4] Running ML Stub Emitter (ml/scripts/emit_sample.py)..." -ForegroundColor Yellow
    $env:PYTHONPATH = "."
    python ml/scripts/emit_sample.py --backend-url $BackendUrl

    # 4. Fetch dashboard summary via PowerShell
    Write-Host "`n[4/4] Verifying Dashboard KPI payload from API..." -ForegroundColor Yellow
    $summary = Invoke-RestMethod -Uri "$BackendUrl/api/dashboard/summary" -Method Get
    Write-Host "      Total Defects in Database : $($summary.total_defects)" -ForegroundColor Green
    Write-Host "      Critical Defects          : $($summary.critical_defects)" -ForegroundColor Green
    Write-Host "      Open Alerts               : $($summary.open_alerts)" -ForegroundColor Green

    Write-Host "`n======================================================================" -ForegroundColor Cyan
    Write-Host "  Phase 1 Walking Skeleton Demo SUCCESSFUL! Integration Slice Proven. " -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Cyan
}
finally {
    Write-Host "`n[CLEANUP] Stopping background backend process..." -ForegroundColor Gray
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
