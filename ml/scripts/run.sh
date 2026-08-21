#!/usr/bin/env bash
# =============================================================================
# TrackChain Master ML Training Orchestrator
# Trains all 5 Phase 2 models in dependency order with checkpointing.
#
# Usage:
#   chmod +x ml/scripts/run.sh
#   ./ml/scripts/run.sh [--epochs-yolo N] [--epochs-bilstm N] [--epochs-vae N]
#                       [--resume] [--skip-yolo] [--skip-patchcore]
#
# Output:
#   - Trained weights in artifacts/checkpoints/
#   - ONNX/INT8 exports in artifacts/exports/
#   - Training logs in artifacts/logs/
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$REPO_ROOT/artifacts/logs"
CHECKPOINT_DIR="$REPO_ROOT/artifacts/checkpoints"
EXPORT_DIR="$REPO_ROOT/artifacts/exports"
DATA_ROOT="$REPO_ROOT/data"

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

EPOCHS_YOLO=${EPOCHS_YOLO:-50}
EPOCHS_BILSTM=${EPOCHS_BILSTM:-20}
EPOCHS_VAE=${EPOCHS_VAE:-30}
BATCH_SIZE=${BATCH_SIZE:-16}
RESUME=false
SKIP_YOLO=false
SKIP_PATCHCORE=false
SKIP_BILSTM=false
SKIP_VAE=false

# Auto-detect CUDA GPU
if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    DEFAULT_DEVICE="0"
    DEVICE_INFO=$(python -c "import torch; print(f'CUDA GPU 0 ({torch.cuda.get_device_name(0)})')")
else
    DEFAULT_DEVICE="cpu"
    DEVICE_INFO="CPU (No CUDA device found)"
fi
TRAIN_DEVICE=${TRAIN_DEVICE:-"$DEFAULT_DEVICE"}

# --- Color output ------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }
header(){ echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}";
          echo -e "${BLUE}  $*${NC}";
          echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"; }

# --- Argument parsing --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --epochs-yolo)    EPOCHS_YOLO="$2"; shift 2;;
        --epochs-bilstm)  EPOCHS_BILSTM="$2"; shift 2;;
        --epochs-vae)     EPOCHS_VAE="$2"; shift 2;;
        --batch)          BATCH_SIZE="$2"; shift 2;;
        --resume)         RESUME=true; shift;;
        --skip-yolo)      SKIP_YOLO=true; shift;;
        --skip-patchcore) SKIP_PATCHCORE=true; shift;;
        --skip-bilstm)    SKIP_BILSTM=true; shift;;
        --skip-vae)       SKIP_VAE=true; shift;;
        *) err "Unknown option: $1"; exit 1;;
    esac
done

# --- Setup -------------------------------------------------------------------
cd "$REPO_ROOT"
mkdir -p "$LOG_DIR" "$CHECKPOINT_DIR/vision" "$CHECKPOINT_DIR/geometry" "$EXPORT_DIR"

START_TIME=$(date +%s)
header "TrackChain Phase 2 — Master ML Training Pipeline"
info "Repo root:      $REPO_ROOT"
info "Compute Device: $DEVICE_INFO"
info "YOLO epochs:    $EPOCHS_YOLO"
info "Bi-LSTM epochs: $EPOCHS_BILSTM"
info "VAE epochs:     $EPOCHS_VAE"
info "Batch size:     $BATCH_SIZE"
info "Resume mode:    $RESUME"

# --- Helper: checkpoint-aware run --------------------------------------------
run_step() {
    local step_name="$1"
    local checkpoint="$2"
    shift 2
    local cmd=("$@")

    if [[ "$RESUME" == true && -f "$checkpoint" ]]; then
        warn "[$step_name] Checkpoint exists, skipping: $checkpoint"
        return 0
    fi

    info "[$step_name] Starting..."
    if "${cmd[@]}" 2>&1 | tee "$LOG_DIR/${step_name}.log"; then
        touch "$checkpoint"
        ok "[$step_name] Completed successfully"
    else
        err "[$step_name] FAILED. See log: $LOG_DIR/${step_name}.log"
        return 1
    fi
}

# =============================================================================
# STEP 1: Data Verification & Generation
# =============================================================================
header "STEP 1/7: Data Verification & Generation"

if ! python -c "import os
assert os.path.exists('$DATA_ROOT/external/rail_defects/train/images'), 'YOLO data missing'
assert os.path.exists('$DATA_ROOT/external/rail_normal_only/train/good'), 'PatchCore data missing'
print('[OK] Vision datasets verified')" 2>/dev/null; then
    err "Vision datasets not found. Ensure '$DATA_ROOT/external/rail_defects' and '$DATA_ROOT/external/rail_normal_only' exist."
    exit 1
fi

run_step "generate_trc" \
    "$CHECKPOINT_DIR/.trc_data.done" \
    python ml/scripts/generate_trc_telemetry.py \
        --mode telemetry \
        --output "$DATA_ROOT/processed/synthetic_trc_run_001.csv"

run_step "generate_geometry" \
    "$CHECKPOINT_DIR/.geometry_data.done" \
    python ml/scripts/generate_trc_telemetry.py \
        --mode geometry_sequences --num_samples 5000 \
        --output "$DATA_ROOT/processed/geometry_sequences/"

run_step "generate_normal" \
    "$CHECKPOINT_DIR/.normal_data.done" \
    python ml/scripts/generate_trc_telemetry.py \
        --mode normal_sequences --num_samples 3000 \
        --output "$DATA_ROOT/processed/normal_sequences/"

# =============================================================================
# STEP 2: YOLO Training (Phase 2.1)
# =============================================================================
header "STEP 2/7: YOLOv8n Visual Defect Detector"

if [[ "$SKIP_YOLO" == true ]]; then
    warn "Skipping YOLO (--skip-yolo)"
else
    run_step "train_yolo" \
        "$CHECKPOINT_DIR/vision/.yolo_train.done" \
        python ml/scripts/train_detector.py \
            --data "$DATA_ROOT/external/rail_defects/data.yaml" \
            --epochs "$EPOCHS_YOLO" \
            --batch "$BATCH_SIZE" \
            --device "$TRAIN_DEVICE"

    run_step "export_yolo_onnx" \
        "$EXPORT_DIR/.yolo_onnx.done" \
        python ml/inference/exporters.py \
            --model "$CHECKPOINT_DIR/vision/yolov8n_rail_best.pt" \
            --format onnx

    run_step "export_yolo_int8" \
        "$EXPORT_DIR/.yolo_int8.done" \
        python ml/inference/exporters.py \
            --model "$CHECKPOINT_DIR/vision/yolov8n_rail_best.pt" \
            --format int8
fi

# =============================================================================
# STEP 3: PatchCore Memory Bank (Phase 2.2)
# =============================================================================
header "STEP 3/7: PatchCore Visual Anomaly Detector"

if [[ "$SKIP_PATCHCORE" == true ]]; then
    warn "Skipping PatchCore (--skip-patchcore)"
else
    run_step "train_patchcore" \
        "$CHECKPOINT_DIR/vision/.patchcore_train.done" \
        python ml/scripts/train_anomaly.py \
            --coreset_ratio 0.10 \
            --fpr_target 0.01 \
            --device "$TRAIN_DEVICE"
fi

# =============================================================================
# STEP 4: Physics Verification (Phase 2.3) — no training
# =============================================================================
header "STEP 4/7: EN 13848 Physics Verification"

python -c "
import pandas as pd
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
det = EN13848PhysicsThresholdDetector()
df = pd.read_csv('$DATA_ROOT/processed/synthetic_trc_run_001.csv')
signals = det.predict(df)
fired = signals[0].fired
score = signals[0].value
print(f'Physics fired: {fired}, score: {score:.3f}')
assert fired and abs(score - 0.625) < 0.05, 'Physics math failed!'
"
touch "$CHECKPOINT_DIR/geometry/.physics_verify.done"
ok "[physics_verify] EN 13848 math verified"

# =============================================================================
# STEP 5: Bi-LSTM Training (Phase 2.4)
# =============================================================================
header "STEP 5/7: Bi-LSTM Geometry Fault Typing"

if [[ "$SKIP_BILSTM" == true ]]; then
    warn "Skipping Bi-LSTM (--skip-bilstm)"
else
    run_step "train_bilstm" \
        "$CHECKPOINT_DIR/geometry/.bilstm_train.done" \
        python ml/scripts/train_fault_classifier.py \
            --epochs "$EPOCHS_BILSTM" \
            --batch_size "$BATCH_SIZE"
fi

# =============================================================================
# STEP 6: Seq-VAE Training (Phase 2.5)
# =============================================================================
header "STEP 6/7: Sequence VAE Novel Geometry Detector"

if [[ "$SKIP_VAE" == true ]]; then
    warn "Skipping Seq-VAE (--skip-vae)"
else
    run_step "train_vae" \
        "$CHECKPOINT_DIR/geometry/.vae_train.done" \
        python ml/scripts/train_sequence_vae.py \
            --epochs "$EPOCHS_VAE" \
            --beta 0.01 \
            --latent_dim 16
fi

# =============================================================================
# STEP 7: Final Test Suite
# =============================================================================
header "STEP 7/7: Full Test Suite Verification"

run_step "tests" \
    "$CHECKPOINT_DIR/.tests.done" \
    python -m pytest ml/tests -v --tb=short

# =============================================================================
# Summary
# =============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

header "Phase 2 Training COMPLETE"
ok "Duration: ${DURATION}s"
ok "Checkpoints: $CHECKPOINT_DIR/"
ok "Exports:     $EXPORT_DIR/"
ok "Logs:        $LOG_DIR/"
echo ""
ok "Next step: Run ./ml/scripts/calibrate.sh to fit calibration parameters."
