# =============================================================================
# TrackChain Docker Deployment Orchestrator (PowerShell)
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "             DEPLOYING TRACKCHAIN CONTAINER INFRASTRUCTURE               " -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan

Write-Host "[1/3] Building Docker containers (FastAPI + TimescaleDB + MinIO)..." -ForegroundColor Green
docker-compose build

Write-Host "[2/3] Starting backend services in detached mode..." -ForegroundColor Green
docker-compose up -d

Write-Host "[3/3] Checking container health status..." -ForegroundColor Green
docker-compose ps

Write-Host "`n=========================================================================" -ForegroundColor Cyan
Write-Host "TrackChain is live:" -ForegroundColor Green
Write-Host " - API Base URL:       http://localhost:8000"
Write-Host " - API Documentation:  http://localhost:8000/docs"
Write-Host " - Prometheus Metrics: http://localhost:8000/metrics"
Write-Host " - MinIO S3 Console:   http://localhost:9001"
Write-Host "=========================================================================" -ForegroundColor Cyan
