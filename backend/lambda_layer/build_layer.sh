#!/usr/bin/env bash
# =============================================================================
# Build AWS Lambda Layer — TrackChain Backend
#
# Usage:
#   cd backend
#   bash lambda_layer/build_layer.sh
#
# Produces: lambda_layer/trackchain-layer.zip
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER_DIR="${SCRIPT_DIR}/python/lib/python3.11/site-packages"
OUTPUT="${SCRIPT_DIR}/trackchain-layer.zip"

echo "==> Cleaning previous build..."
rm -rf "${SCRIPT_DIR}/python" "${OUTPUT}"
mkdir -p "${LAYER_DIR}"

echo "==> Installing dependencies..."
pip install \
  --no-cache-dir \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  -r "${SCRIPT_DIR}/requirements.txt" \
  -t "${LAYER_DIR}" \
  --upgrade 2>&1 | tail -5

echo "==> Stripping __pycache__ and .dist-info to reduce size..."
find "${LAYER_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${LAYER_DIR}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "${LAYER_DIR}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

echo "==> Packaging..."
cd "${SCRIPT_DIR}"
zip -qr "${OUTPUT}" python/

LAYER_SIZE=$(du -h "${OUTPUT}" | cut -f1)
echo "==> Done: ${OUTPUT} (${LAYER_SIZE})"
echo "    Upload via: sam deploy  OR  AWS Lambda Layers console"
