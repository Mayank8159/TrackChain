#!/usr/bin/env bash
# =============================================================================
# TrackChain Docker Deployment Orchestrator
# =============================================================================

set -e

echo "========================================================================="
echo "             DEPLOYING TRACKCHAIN CONTAINER INFRASTRUCTURE               "
echo "========================================================================="

echo "[1/3] Building Docker containers (FastAPI + TimescaleDB + MinIO)..."
docker-compose build

echo "[2/3] Starting backend services in detached mode..."
docker-compose up -d

echo "[3/3] Checking container health status..."
docker-compose ps

echo ""
echo "========================================================================="
echo "TrackChain is live:"
echo " - API Base URL:       http://localhost:8000"
echo " - API Documentation:  http://localhost:8000/docs"
echo " - Prometheus Metrics: http://localhost:8000/metrics"
echo " - MinIO S3 Console:   http://localhost:9001"
echo "========================================================================="
