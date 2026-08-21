# =============================================================================
# TrackChain Production Launch Orchestrator (Windows PowerShell)
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "                TRACKCHAIN PRODUCTION SYSTEM LAUNCH                      " -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan

$env:ENVIRONMENT = "production"
$Port = if ($env:PORT) { $env:PORT } else { "8000" }

Write-Host "[1/4] Checking Python environment and dependencies..." -ForegroundColor Green
python -m pip install -q -r backend/requirements.txt

Write-Host "[2/4] Initializing database tables..." -ForegroundColor Green
python -c "import sys, os; sys.path.insert(0, os.path.abspath('backend')); from src.db.session import engine, Base; Base.metadata.create_all(bind=engine)"

Write-Host "[3/4] Checking database initial seed..." -ForegroundColor Green
python scripts/seed.py

Write-Host "[4/4] Starting FastAPI backend on http://127.0.0.1:$Port..." -ForegroundColor Green
uvicorn src.main:app --app-dir backend --host 0.0.0.0 --port $Port --log-level info --access-log
