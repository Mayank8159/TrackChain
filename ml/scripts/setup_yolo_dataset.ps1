# =============================================================================
# setup_yolo_dataset.ps1
# Downloads and structures the Railway Track Fault dataset for YOLOv8 training.
# Run this from the root of the TrackChain repository.
# =============================================================================
$ErrorActionPreference = 'Stop'

$targetDir = "data\external\rail_defects"
$kaggleDataset = "shubhamparmar1405/railway-track-fault-detection"

# 1. Create directory structure matching YOLO format
Write-Host "Creating YOLO dataset directories in $targetDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$targetDir\train\images" | Out-Null
New-Item -ItemType Directory -Force -Path "$targetDir\train\labels" | Out-Null
New-Item -ItemType Directory -Force -Path "$targetDir\valid\images" | Out-Null
New-Item -ItemType Directory -Force -Path "$targetDir\valid\labels" | Out-Null
New-Item -ItemType Directory -Force -Path "$targetDir\test\images"  | Out-Null
New-Item -ItemType Directory -Force -Path "$targetDir\test\labels"  | Out-Null

# 2. Download dataset if kaggle CLI is present
Write-Host "Checking for Kaggle dataset download ($kaggleDataset)..." -ForegroundColor Cyan
$downloaded = $false
if (Get-Command kaggle -ErrorAction SilentlyContinue) {
    try {
        New-Item -ItemType Directory -Force -Path "$targetDir\raw" | Out-Null
        kaggle datasets download -d $kaggleDataset -p "$targetDir\raw" --unzip
        Write-Host "Downloaded and unzipped dataset from Kaggle." -ForegroundColor Green
        $downloaded = $true
    }
    catch {
        Write-Warning "Kaggle download failed: $_"
    }
}

if (-not $downloaded) {
    Write-Host "[INFO] Generating synthetic starter samples for immediate training verification..." -ForegroundColor Yellow
    python -c "
import numpy as np
from PIL import Image, ImageDraw
import os

for split in ['train', 'valid', 'test']:
    for i in range(8 if split=='train' else 4):
        img_p = f'data/external/rail_defects/{split}/images/sample_{i:03d}.jpg'
        lbl_p = f'data/external/rail_defects/{split}/labels/sample_{i:03d}.txt'
        
        # Create synthetic track image
        img = Image.new('RGB', (640, 640), color=(70, 75, 80))
        draw = ImageDraw.Draw(img)
        # Draw rails
        draw.line([(180, 0), (180, 640)], fill=(180, 190, 200), width=16)
        draw.line([(460, 0), (460, 640)], fill=(180, 190, 200), width=16)
        # Draw sleepers
        for y in range(40, 640, 80):
            draw.rectangle([60, y, 580, y + 30], fill=(40, 30, 20))
        
        # Add defect box
        cls_id = i % 4
        # Normalized bbox: class x_center y_center width height
        x_c, y_c, w, h = 0.28, 0.45, 0.08, 0.08
        draw.rectangle([int((x_c-w/2)*640), int((y_c-h/2)*640), int((x_c+w/2)*640), int((y_c+h/2)*640)], outline=(255, 0, 0), width=2)
        
        img.save(img_p)
        with open(lbl_p, 'w') as f:
            f.write(f'{cls_id} {x_c:.4f} {y_c:.4f} {w:.4f} {h:.4f}\n')
print('[OK] Synthetic dataset split generated successfully.')
"
}

# 3. Create data.yaml for Ultralytics with absolute forward-slash path
$classes = @("missing_fastener", "defective_clip", "crack", "obstruction")
$fullPath = (Resolve-Path $targetDir).Path.Replace('\', '/')

$yamlContent = @"
path: $fullPath
train: train/images
val: valid/images
test: test/images

nc: $($classes.Count)
names:
  0: missing_fastener
  1: defective_clip
  2: crack
  3: obstruction
"@

Set-Content -Path "$targetDir\data.yaml" -Value $yamlContent -Encoding UTF8

Write-Host "`nDataset setup complete!" -ForegroundColor Green
Write-Host "Config file created at: $targetDir\data.yaml" -ForegroundColor Green
