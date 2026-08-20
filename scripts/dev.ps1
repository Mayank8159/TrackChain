# Start the full local dev stack (db, backend, web) with hot reload.

$ErrorActionPreference = 'Stop'
Write-Host "🚀 Launching TrackChain Development Stack..." -ForegroundColor Cyan

# Start Next.js web application and backend concurrently using turbo
pnpm dev
