# =============================================================================
# verify_and_scaffold_assets.ps1
# Verifies dataset placement and enforces the Base/Trained artifact structure.
# Run from the monorepo root (D:\TrackChain).
# =============================================================================
$ErrorActionPreference = 'Stop'
$root = Get-Location

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " TrackChain Asset & Dataset Verification " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Verify Dataset Placement
$datasetYaml = Join-Path $root "data\external\rail_defects\data.yaml"
if (Test-Path $datasetYaml) {
    Write-Host "[OK] Dataset found at: data\external\rail_defects\" -ForegroundColor Green
} else {
    Write-Host "[WARN] Dataset missing! Running setup_yolo_dataset.ps1..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File ml\scripts\setup_yolo_dataset.ps1
}

# 2. Enforce Artifact Structure (Base vs Trained vs Exports)
$artifactDirs = @(
    "artifacts\base\vision",
    "artifacts\base\geometry",
    "artifacts\checkpoints\vision",
    "artifacts\checkpoints\geometry",
    "artifacts\exports\vision",
    "artifacts\exports\geometry",
    "artifacts\calibration"
)

Write-Host "`nScaffolding Artifact Directories..." -ForegroundColor Cyan
foreach ($dir in $artifactDirs) {
    $fullPath = Join-Path $root $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "  [+] Created $dir" -ForegroundColor Gray
    } else {
        Write-Host "  [=] Exists  $dir" -ForegroundColor DarkGray
    }
}

# 3. Check for Base YOLO weights (Download / move if missing)
$baseYolo = Join-Path $root "artifacts\base\vision\yolov8n.pt"
if (-not (Test-Path $baseYolo)) {
    Write-Host "`n[INFO] Fetching base YOLOv8n weights into artifacts\base\vision\yolov8n.pt..." -ForegroundColor Yellow
    python -c "
from ultralytics import YOLO
import shutil
import os
from pathlib import Path

target = Path('artifacts/base/vision/yolov8n.pt')
target.parent.mkdir(parents=True, exist_ok=True)

if os.path.exists('yolov8n.pt'):
    shutil.copy('yolov8n.pt', target)
else:
    m = YOLO('yolov8n.pt')
    if os.path.exists('yolov8n.pt'):
        shutil.move('yolov8n.pt', target)
print('[OK] Base YOLOv8n weights ready at:', target)
"
    if (Test-Path $baseYolo) {
        Write-Host "[OK] Base weights stored in artifacts\base\vision\yolov8n.pt" -ForegroundColor Green
    }
} else {
    Write-Host "`n[OK] Base YOLO weights found in artifacts\base\vision\yolov8n.pt" -ForegroundColor Green
}

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host " Asset Structure Verified & Synced!      " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
