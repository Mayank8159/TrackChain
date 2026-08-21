#!/bin/bash
# ============================================================================
# TrackChain Complete Enhanced PatchCore Training Pipeline (Bash)
# Multi-source dataset expansion, multi-scale feature extraction (3x3, 5x5, 7x7),
# FAISS memory banks, Nelder-Mead sigmoid calibration, and TPR/FPR benchmark.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"

echo "======================================================================"
echo "TrackChain PatchCore Complete Training Pipeline"
echo "======================================================================"

# Configuration
YOLO_DATA="data/external/rail_defects_expanded"
NORMAL_DATA="data/external/rail_normal_expanded"
CONFIG="ml/configs/patchcore_enhanced.yaml"
OUTPUT="artifacts/checkpoints/vision/patchcore_enhanced"

cd "$REPO_ROOT"

# Ensure output directories
mkdir -p "$OUTPUT" artifacts/calibration artifacts/validation/patchcore

# Step 1: Expand dataset
echo ""
echo "[STEP 1/4] Expanding normal dataset..."
echo "----------------------------------------------------------------------"
python ml/scripts/expand_patchcore_dataset.py \
    --yolo-data "$YOLO_DATA" \
    --output "$NORMAL_DATA" \
    --target-count 800 \
    --augment-factor 8

# Step 2: Train Enhanced PatchCore multi-scale model
echo ""
echo "[STEP 2/4] Training Enhanced PatchCore (Multi-Scale FAISS & Calibration)..."
echo "----------------------------------------------------------------------"
python ml/scripts/train_patchcore_enhanced.py \
    --data "$NORMAL_DATA/dataset_config.yaml" \
    --config "$CONFIG" \
    --output "$OUTPUT" \
    --device auto

# Step 3: Verify training results
echo ""
echo "[STEP 3/4] Verifying validation metrics..."
echo "----------------------------------------------------------------------"

if [ -f "$OUTPUT/validation_metrics.json" ]; then
    echo "Validation metrics:"
    cat "$OUTPUT/validation_metrics.json" | python -m json.tool
else
    echo "[WARNING] No validation metrics found"
fi

# Step 4: Test inference pipeline
echo ""
echo "[STEP 4/4] Testing inference pipeline..."
echo "----------------------------------------------------------------------"

python -c "
import sys
sys.path.append('.')
from ml.models.vision.patchcore_enhanced import EnhancedPatchCore
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from pathlib import Path
import numpy as np

# 1. Test EnhancedPatchCore loading
model = EnhancedPatchCore()
model.load(Path('$OUTPUT'))
print(f'[OK] EnhancedPatchCore loaded with {len(model.memory_banks)} memory banks (scales: {list(model.memory_banks.keys())})')

# 2. Test PatchCoreAnomalyDetector wrapper integration
detector = PatchCoreAnomalyDetector(checkpoint_path=Path('$OUTPUT'))
dummy = np.ones((224, 224, 3), dtype=np.uint8) * 128
sigs = detector.predict(dummy)
print(f'[OK] PatchCoreAnomalyDetector emitted {len(sigs)} contract signal(s). Score: {sigs[0].calibrated_prob:.2%}, Anomaly: {sigs[0].is_anomaly}')
"

echo ""
echo "======================================================================"
echo "Enhanced PatchCore Training Pipeline Complete!"
echo "======================================================================"
echo "Model Checkpoint:  $OUTPUT"
echo "Memory Banks:      $OUTPUT/memory_bank_*.index"
echo "Calibration JSON:  artifacts/calibration/patchcore_calibration.json"
echo "Validation Plot:   $OUTPUT/score_distribution.png"
echo "Validation JSON:   $OUTPUT/validation_metrics.json"
echo "======================================================================"
