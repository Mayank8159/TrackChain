#!/usr/bin/env bash
# Fetch public datasets (RSDDs, NEU, fastener sets).

set -e

DATA_DIR="data/external"
mkdir -p "$DATA_DIR"

echo "Downloading RSDDs (Rail Surface Defect Database)..."
# curl -L -o "$DATA_DIR/rsdds.zip" "https://example.com/rsdds.zip"
# unzip -q "$DATA_DIR/rsdds.zip" -d "$DATA_DIR/rsdds"

echo "Downloading NEU Surface Defect Dataset..."
# curl -L -o "$DATA_DIR/neu.zip" "https://example.com/neu.zip"
# unzip -q "$DATA_DIR/neu.zip" -d "$DATA_DIR/neu"

echo "Dataset download placeholder complete."
