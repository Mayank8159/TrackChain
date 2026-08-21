#!/usr/bin/env bash
# =============================================================================
# Build AWS Lambda Layer with pinned dependencies (tc.v1 SOTA)
# =============================================================================

set -e

LAYER_DIR="python/lib/python3.11/site-packages"
mkdir -p "$LAYER_DIR"

pip install -r requirements.txt -t "$LAYER_DIR" --upgrade

# Package layer zip
zip -r trackchain-layer.zip python/

echo "Lambda layer built successfully: trackchain-layer.zip"
echo "Upload to AWS Lambda Layers console or deploy via AWS SAM template.yaml."
