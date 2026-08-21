# ============================================================================
# TrackChain Complete YOLO Training Pipeline (PowerShell)
# Aggregates datasets, trains custom model, exports ONNX/INT8, calibrates,
# and generates comprehensive validation reports.
# ============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path "$ScriptDir\..\.."
$env:PYTHONPATH = "$RepoRoot;$env:PYTHONPATH"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "TrackChain YOLO Complete Training Pipeline (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$DataRoot = "data/external/rail_defects"
$ExpandedData = "data/external/rail_defects_expanded"
$Config = "ml/configs/detector.yaml"
$Output = "artifacts/checkpoints/vision"

Set-Location $RepoRoot

# Ensure output directories
New-Item -ItemType Directory -Force -Path "$Output", "artifacts/exports", "artifacts/calibration", "artifacts/validation/yolo" | Out-Null

# Auto-detect CUDA
$HasCuda = python -c "import torch; print('true' if torch.cuda.is_available() else 'false')"
if ($HasCuda -eq "true") {
    $Device = "0"
    Write-Host "[INFO] CUDA GPU detected. Using device: 0" -ForegroundColor Green
} else {
    $Device = "cpu"
    Write-Host "[INFO] No CUDA GPU detected. Using CPU fallback." -ForegroundColor Yellow
}

# Step 1: Expand dataset
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 1/6] Expanding and aggregating dataset..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/scripts/expand_yolo_dataset.py --data-root $DataRoot --output-root $ExpandedData --target-per-class 250 --augment-factor 10

# Step 2: Train custom model
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 2/6] Training YOLO detector model..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/scripts/train_detector.py --data "$ExpandedData/data.yaml" --config $Config --output-dir $Output --device $Device

$BestModel = "$Output/yolov8n_rail_best.pt"
if (-not (Test-Path $BestModel)) {
    $BestModel = "$Output/yolov8n_rail_run/weights/best.pt"
}

# Step 3: Export to ONNX
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 3/6] Exporting model to ONNX runtime..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/inference/exporters.py --model $BestModel --format onnx --outdir artifacts/exports

# Step 4: Export to INT8
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 4/6] Exporting model to INT8 edge runtime..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/inference/exporters.py --model $BestModel --format int8 --outdir artifacts/exports

# Step 5: Calibrate model
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 5/6] Calibrating YOLO model probabilities..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/scripts/calibrate_yolo.py --model $BestModel --val-data "$ExpandedData/data.yaml" --output "artifacts/calibration/yolo_temp.json" --device $Device

# Step 6: Validate model
Write-Host "`n----------------------------------------------------------------------" -ForegroundColor Blue
Write-Host "[STEP 6/6] Running comprehensive validation suite..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Blue
python ml/scripts/validate_yolo.py --model $BestModel --data "$ExpandedData/data.yaml" --output "artifacts/validation/yolo" --device $Device

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "TrackChain YOLO Upgrade Pipeline COMPLETE!" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Trained Weights:   $BestModel"
Write-Host "ONNX Export:       artifacts/exports/yolov8n_rail_best.onnx"
Write-Host "INT8 Edge Export:  artifacts/exports/yolov8n_rail_best_int8.onnx"
Write-Host "Calibration:       artifacts/calibration/yolo_temp.json"
Write-Host "Validation Report: artifacts/validation/yolo/validation_report.json"
Write-Host "======================================================================"
