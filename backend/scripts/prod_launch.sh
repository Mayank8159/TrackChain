#!/usr/bin/env bash
# =============================================================================
# TrackChain Production Launch Orchestrator (Linux / Container)
# =============================================================================

set -e

echo "========================================================================="
echo "                TRACKCHAIN PRODUCTION SYSTEM LAUNCH                      "
echo "========================================================================="

# 1. Environment Check
export ENVIRONMENT=${ENVIRONMENT:-"production"}
export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-4}

echo "[1/4] Checking Python environment and dependencies..."
python -m pip install -q -r backend/requirements.txt

# 2. Database Migrations
echo "[2/4] Running database schema migrations..."
cd backend
python -c "from src.db.session import engine, Base; Base.metadata.create_all(bind=engine)"
cd ..

# 3. Seed Reference Track Network Data (if DB is empty)
echo "[3/4] Checking database initial seed..."
python scripts/seed.py

# 4. Start Production Gunicorn / Uvicorn Server
echo "[4/4] Starting FastAPI backend on port $PORT with $WORKERS worker processes..."
exec uvicorn src.main:app --app-dir backend --host 0.0.0.0 --port "$PORT" --workers "$WORKERS" --log-level info --access-log
