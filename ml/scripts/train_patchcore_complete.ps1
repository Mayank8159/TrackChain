# ============================================================================
# TrackChain Complete Enhanced PatchCore Training Pipeline (Windows PowerShell)
# Multi-source dataset expansion, multi-scale feature extraction (3x3, 5x5, 7x7),
# FAISS memory banks, Nelder-Mead sigmoid calibration, and TPR/FPR benchmark.
# ============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path "$ScriptDir\..\.."
$env:PYTHONPATH = "$RepoRoot;$env:PYTHONPATH"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "TrackChain Enhanced PatchCore Complete Training Pipeline (PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$YoloData = "data/external/rail_defects_expanded"
$NormalData = "data/external/rail_normal_expanded"
$Config = "ml/configs/patchcore_enhanced.yaml"
$Output = "artifacts/checkpoints/vision/patchcore_enhanced"

Set-Location $RepoRoot

# Ensure output directories
New-Item -ItemType Directory -Force -Path "$Output", "artifacts/calibration", "artifacts/validation/patchcore" | Out-Null

# Step 1: Expand dataset
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 1/4] Expanding and synchronizing normal dataset..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/scripts/expand_patchcore_dataset.py --yolo-data $YoloData --output $NormalData --target-count 800 --augment-factor 8

# Step 2: Train Enhanced PatchCore multi-scale model
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 2/4] Training Enhanced PatchCore (Multi-Scale FAISS & Calibration)..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/scripts/train_patchcore_enhanced.py --data "$NormalData/dataset_config.yaml" --config $Config --output $Output --device auto

# Step 3: Verify validation metrics
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 3/4] Verifying Validation Metrics..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
if (Test-Path "$Output/validation_metrics.json") {
    Get-Content "$Output/validation_metrics.json"
} else {
    Write-Host "[WARNING] No validation_metrics.json found" -ForegroundColor Yellow
}

# Step 4: Verification & Inference Testing
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 4/4] Verifying PatchCore model and calibration artifacts..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python -c "
import sys
sys.path.append('.')
from ml.models.vision.patchcore_enhanced import EnhancedPatchCore
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from pathlib import Path
import numpy as np

# 1. Test EnhancedPatchCore loading
model = EnhancedPatchCore()
model.load(Path('$Output'))
print(f'[OK] EnhancedPatchCore loaded with {len(model.memory_banks)} memory banks (scales: {list(model.memory_banks.keys())})')

# 2. Test PatchCoreAnomalyDetector wrapper integration
detector = PatchCoreAnomalyDetector(checkpoint_path=Path('$Output'))
dummy = np.ones((224, 224, 3), dtype=np.uint8) * 128
sigs = detector.predict(dummy)
print(f'[OK] PatchCoreAnomalyDetector emitted {len(sigs)} contract signal(s). Score: {sigs[0].calibrated_prob:.2%}, Anomaly: {sigs[0].is_anomaly}')
"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "Enhanced PatchCore Training Pipeline COMPLETE!" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Model Checkpoint:  $Output"
Write-Host "Memory Banks:      $Output/memory_bank_*.index"
Write-Host "Calibration JSON:  artifacts/calibration/patchcore_calibration.json"
Write-Host "Validation Plot:   $Output/score_distribution.png"
Write-Host "Validation JSON:   $Output/validation_metrics.json"
Write-Host "======================================================================"
