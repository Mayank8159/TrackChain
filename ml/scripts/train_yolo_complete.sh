#!/usr/bin/env bash
# ============================================================================
# Complete YOLO Training Pipeline for TrackChain
# Aggregates datasets, trains custom model, exports ONNX/INT8, calibrates,
# and generates comprehensive validation reports.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

echo "======================================================================"
echo "TrackChain YOLO Complete Training Pipeline"
echo "======================================================================"

# Configuration
DATA_ROOT="data/external/rail_defects"
EXPANDED_DATA="data/external/rail_defects_expanded"
CONFIG="ml/configs/detector.yaml"
OUTPUT="artifacts/checkpoints/vision"
DEVICE=${1:-auto}

cd "$REPO_ROOT"
mkdir -p "$OUTPUT" "artifacts/exports" "artifacts/calibration" "artifacts/validation/yolo"

# Auto-detect CUDA GPU
if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    DEVICE_INFO=$(python -c "import torch; print(f'CUDA GPU 0 ({torch.cuda.get_device_name(0)})')")
    [ "$DEVICE" = "auto" ] && DEVICE="0"
else
    DEVICE_INFO="CPU"
    [ "$DEVICE" = "auto" ] && DEVICE="cpu"
fi

echo "Repo root:      $REPO_ROOT"
echo "Compute Device: $DEVICE_INFO ($DEVICE)"
echo ""

# Step 1: Expand dataset
echo "----------------------------------------------------------------------"
echo "[STEP 1/6] Expanding and aggregating dataset..."
echo "----------------------------------------------------------------------"
python ml/scripts/expand_yolo_dataset.py \
    --data-root "$DATA_ROOT" \
    --output-root "$EXPANDED_DATA" \
    --target-per-class 250 \
    --augment-factor 10

TRAIN_COUNT=$(ls "$EXPANDED_DATA/train/images" 2>/dev/null | wc -l || echo 0)
VALID_COUNT=$(ls "$EXPANDED_DATA/valid/images" 2>/dev/null | wc -l || echo 0)
echo ""
echo "Dataset expansion verified: Train=$TRAIN_COUNT, Valid=$VALID_COUNT"

# Step 2: Train custom YOLO model
echo ""
echo "----------------------------------------------------------------------"
echo "[STEP 2/6] Training YOLO detector model..."
echo "----------------------------------------------------------------------"
python ml/scripts/train_detector.py \
    --data "$EXPANDED_DATA/data.yaml" \
    --config "$CONFIG" \
    --output-dir "$OUTPUT" \
    --device "$DEVICE"

BEST_MODEL="$OUTPUT/yolov8n_rail_best.pt"
if [ ! -f "$BEST_MODEL" ]; then
    BEST_MODEL="$OUTPUT/yolov8n_rail_run/weights/best.pt"
fi

# Step 3: Export to ONNX
echo ""
echo "----------------------------------------------------------------------"
echo "[STEP 3/6] Exporting model to ONNX runtime..."
echo "----------------------------------------------------------------------"
python ml/inference/exporters.py \
    --model "$BEST_MODEL" \
    --format onnx \
    --outdir artifacts/exports

# Step 4: Export to INT8
echo ""
echo "----------------------------------------------------------------------"
echo "[STEP 4/6] Exporting model to INT8 quantized edge runtime..."
echo "----------------------------------------------------------------------"
python ml/inference/exporters.py \
    --model "$BEST_MODEL" \
    --format int8 \
    --outdir artifacts/exports

# Step 5: Calibrate model
echo ""
echo "----------------------------------------------------------------------"
echo "[STEP 5/6] Calibrating YOLO model probabilities (Temperature Scaling)..."
echo "----------------------------------------------------------------------"
python ml/scripts/calibrate_yolo.py \
    --model "$BEST_MODEL" \
    --val-data "$EXPANDED_DATA/data.yaml" \
    --output "artifacts/calibration/yolo_temp.json" \
    --device "$DEVICE"

# Step 6: Validate and generate metrics report
echo ""
echo "----------------------------------------------------------------------"
echo "[STEP 6/6] Running comprehensive validation suite..."
echo "----------------------------------------------------------------------"
python ml/scripts/validate_yolo.py \
    --model "$BEST_MODEL" \
    --data "$EXPANDED_DATA/data.yaml" \
    --output "artifacts/validation/yolo" \
    --device "$DEVICE"

echo ""
echo "======================================================================"
echo "TrackChain YOLO Upgrade Pipeline COMPLETE!"
echo "======================================================================"
echo "Trained Weights:   $BEST_MODEL"
echo "ONNX Export:       artifacts/exports/yolov8n_rail_best.onnx"
echo "INT8 Edge Export:  artifacts/exports/yolov8n_rail_best_int8.onnx"
echo "Calibration:       artifacts/calibration/yolo_temp.json"
echo "Validation Report: artifacts/validation/yolo/validation_report.json"
echo "======================================================================"
