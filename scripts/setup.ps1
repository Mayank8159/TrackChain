# One-shot local setup: install JS deps, create venvs, pull env templates.

param(
    [switch]$SkipPython
)

$ErrorActionPreference = 'Stop'
Write-Host "🚄 TrackChain Monorepo Setup Initializing..." -ForegroundColor Cyan

# 1. Environment Templates
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  + Created root .env" -ForegroundColor Green
}
if (-not (Test-Path "backend/.env")) {
    Copy-Item "backend/.env.example" "backend/.env"
    Write-Host "  + Created backend/.env" -ForegroundColor Green
}
if (-not (Test-Path "app/.env.local")) {
    Copy-Item "app/.env.local.example" "app/.env.local"
    Write-Host "  + Created app/.env.local" -ForegroundColor Green
}

# 2. Node / JS dependencies
Write-Host "📦 Installing Node dependencies via pnpm..." -ForegroundColor Yellow
pnpm install

# 3. Python environment
if (-not $SkipPython) {
    Write-Host "🐍 Setting up Python environments..." -ForegroundColor Yellow
    if (-not (Test-Path "venv")) {
        python -m venv venv
    }
    .\venv\Scripts\Activate.ps1
    pip install -r backend/requirements.txt
    pip install -r ml/requirements.txt
}

Write-Host "✅ TrackChain Setup Complete. Run .\scripts\dev.ps1 to start development servers." -ForegroundColor Green
