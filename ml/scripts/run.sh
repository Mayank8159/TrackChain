#!/usr/bin/env bash
# =============================================================================
# TrackChain Master ML Training Orchestrator
# Trains all 5 Phase 2 models in dependency order with SMART checkpointing.
#
# Usage:
#   chmod +x ml/scripts/run.sh
#   ./ml/scripts/run.sh                              # Runs ONLY missing/failed steps
#   ./ml/scripts/run.sh --force                      # Re-runs EVERYTHING (overwrites)
#   ./ml/scripts/run.sh --clean                      # Wipes all checkpoints
#   ./ml/scripts/run.sh --skip-yolo --skip-patchcore # Skips specific steps
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

# Flags
FORCE=false
CLEAN=false
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
        --force)          FORCE=true; shift;;
        --clean)          CLEAN=true; shift;;
        --skip-yolo)      SKIP_YOLO=true; shift;;
        --skip-patchcore) SKIP_PATCHCORE=true; shift;;
        --skip-bilstm)    SKIP_BILSTM=true; shift;;
        --skip-vae)       SKIP_VAE=true; shift;;
        *) err "Unknown option: $1"; exit 1;;
    esac
done

# --- Setup & Clean Logic -----------------------------------------------------
cd "$REPO_ROOT"
mkdir -p "$LOG_DIR" "$CHECKPOINT_DIR/vision" "$CHECKPOINT_DIR/geometry" "$EXPORT_DIR"

if [[ "$CLEAN" == true ]]; then
    warn "Cleaning all checkpoints, exports, and logs..."
    find "$CHECKPOINT_DIR" -name "*.done" -type f -delete
    find "$EXPORT_DIR" -name "*.done" -type f -delete
    ok "Clean complete. Re-run without --clean to start training."
    exit 0
fi

START_TIME=$(date +%s)
header "TrackChain Phase 2 — Master ML Training Pipeline"
info "Repo root:      $REPO_ROOT"
info "Compute Device: $DEVICE_INFO"
info "YOLO epochs:    $EPOCHS_YOLO"
info "Bi-LSTM epochs: $EPOCHS_BILSTM"
info "VAE epochs:     $EPOCHS_VAE"
info "Batch size:     $BATCH_SIZE"
info "Force retrain:  $FORCE"

# --- Helper: checkpoint-aware run --------------------------------------------
run_step() {
    local step_name="$1"
    local checkpoint="$2"
    shift 2
    local cmd=("$@")

    # SMART CHECKPOINTING: Skip if .done file exists and --force is not used
    if [[ "$FORCE" == false && -f "$checkpoint" ]]; then
        info "[$step_name] Already completed (checkpoint found). Skipping."
        return 0
    fi

    info "[$step_name] Starting..."
    
    # Temporarily disable exit-on-error to capture the exact exit code of the piped command
    set +e
    "${cmd[@]}" 2>&1 | tee "$LOG_DIR/${step_name}.log"
    local status=${PIPESTATUS[0]}
    set -e
    
    if [[ $status -eq 0 ]]; then
        touch "$checkpoint"
        ok "[$step_name] Completed successfully"
    else
        err "[$step_name] FAILED (exit code $status). See log: $LOG_DIR/${step_name}.log"
        exit 1
    fi
}

# =============================================================================
# STEP 1: Data Verification & Generation
# =============================================================================
header "STEP 1/7: Data Verification & Generation"

if ! python -c "import os
has_yolo = os.path.exists('$DATA_ROOT/external/rail_defects_expanded/train/images') or os.path.exists('$DATA_ROOT/external/rail_defects/train/images')
has_patch = os.path.exists('$DATA_ROOT/external/rail_normal_expanded/train/good') or os.path.exists('$DATA_ROOT/external/rail_normal_only/train/good')
assert has_yolo, 'YOLO dataset missing'
assert has_patch, 'PatchCore dataset missing'
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

YOLO_DATA="$DATA_ROOT/external/rail_defects/data.yaml"
if [[ -f "$DATA_ROOT/external/rail_defects_expanded/data.yaml" ]]; then
    YOLO_DATA="$DATA_ROOT/external/rail_defects_expanded/data.yaml"
fi

if [[ "$SKIP_YOLO" == true ]]; then
    warn "Skipping YOLO (--skip-yolo)"
else
    run_step "train_yolo" \
        "$CHECKPOINT_DIR/vision/.yolo_train.done" \
        python ml/scripts/train_detector.py \
            --data "$YOLO_DATA" \
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

PATCHCORE_DATA="$DATA_ROOT/external/rail_normal_only"
if [[ -d "$DATA_ROOT/external/rail_normal_expanded/train/good" ]]; then
    PATCHCORE_DATA="$DATA_ROOT/external/rail_normal_expanded"
    info "Using expanded PatchCore dataset (800+ images)"
fi

if [[ "$SKIP_PATCHCORE" == true ]]; then
    warn "Skipping PatchCore (--skip-patchcore)"
else
    run_step "train_patchcore" \
        "$CHECKPOINT_DIR/vision/.patchcore_train.done" \
        python ml/scripts/train_anomaly.py \
            --data-path "$PATCHCORE_DATA" \
            --coreset_ratio 0.10 \
            --fpr_target 0.01 \
            --device "$TRAIN_DEVICE"
fi

# =============================================================================
# STEP 4: Physics Verification (Phase 2.3) — no training
# =============================================================================
header "STEP 4/7: EN 13848 Physics Verification"

if [[ "$FORCE" == false && -f "$CHECKPOINT_DIR/geometry/.physics_verify.done" ]]; then
    info "[physics_verify] Already completed. Skipping."
else
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
fi

# =============================================================================
# STEP 5: Bi-LSTM Training (Phase 2.4) - ENHANCED
# =============================================================================
header "STEP 5/7: Bi-LSTM Geometry Fault Classifier (Enhanced)"

if [[ "$SKIP_BILSTM" == true ]]; then
    warn "Skipping Bi-LSTM (--skip-bilstm)"
else
    run_step "train_bilstm" \
        "$CHECKPOINT_DIR/geometry/.bilstm_train.done" \
        python ml/scripts/train_fault_classifier_enhanced.py \
            --epochs "$EPOCHS_BILSTM" \
            --hidden-size 128 \
            --num-layers 3 \
            --batch_size 128 \
            --lr 0.0005 \
            --label-smoothing 0.1 \
            --dropout 0.4 \
            --data-path "$DATA_ROOT/processed/geometry_sequences/" \
            --save-path "$CHECKPOINT_DIR/geometry/bilstm_fault_typing_enhanced.pt"
fi

# =============================================================================
# STEP 6: Seq-VAE Training (Phase 2.5) - FIXED AND ENHANCED
# =============================================================================
header "STEP 6/7: Sequence VAE Novel Geometry Detector (Enhanced)"

if [[ "$SKIP_VAE" == true ]]; then
    warn "Skipping Seq-VAE (--skip-vae)"
else
    run_step "train_vae" \
        "$CHECKPOINT_DIR/geometry/.vae_train.done" \
        python ml/scripts/train_sequence_vae_enhanced.py \
            --epochs "$EPOCHS_VAE" \
            --beta 0.01 \
            --latent-dim 16 \
            --batch-size 64 \
            --lr 0.001 \
            --kl-annealing \
            --annealing-epochs 10 \
            --data-path "$DATA_ROOT/processed/normal_sequences/" \
            --save-path "$CHECKPOINT_DIR/geometry/sequence_vae_enhanced.pt"
fi

# =============================================================================
# STEP 7: Final Test Suite
# =============================================================================
header "STEP 7/7: Full Test Suite Verification"

run_step "full_test_suite" \
    "$CHECKPOINT_DIR/.tests.done" \
    bash ml/scripts/test.sh

ELAPSED=$(( $(date +%s) - START_TIME ))
echo ""
header "TrackChain Phase 2 — Training Pipeline Complete in ${ELAPSED}s"
ok "Checkpoints: $CHECKPOINT_DIR/"
ok "Exports:     $EXPORT_DIR/"
ok "Logs:        $LOG_DIR/"
echo ""
ok "Next step: Run ./ml/scripts/calibrate.sh to fit calibration parameters."