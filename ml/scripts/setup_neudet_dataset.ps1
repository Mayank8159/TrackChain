# =============================================================================
# setup_neudet_dataset.ps1
# Downloads and prepares the NEU-DET (Steel Surface) dataset for PatchCore memory bank.
# Run from the repository root (D:\TrackChain).
# =============================================================================
$ErrorActionPreference = 'Stop'

$targetDir = "data\external\neudet"
$kaggleDataset = "pkdarshitcarder/neu-surface-defect-database"
$patchcoreTrainGood = "data\external\rail_normal_only\train\good"
$patchcoreValidGood = "data\external\rail_normal_only\valid\good"

New-Item -ItemType Directory -Force -Path "$targetDir\raw" | Out-Null
New-Item -ItemType Directory -Force -Path $patchcoreTrainGood | Out-Null
New-Item -ItemType Directory -Force -Path $patchcoreValidGood | Out-Null

$downloaded = $false
if (Get-Command kaggle -ErrorAction SilentlyContinue) {
    try {
        Write-Host "Checking for Kaggle NEU-DET download ($kaggleDataset)..." -ForegroundColor Cyan
        kaggle datasets download -d $kaggleDataset -p "$targetDir\raw" --unzip
        Write-Host "Downloaded NEU-DET dataset from Kaggle." -ForegroundColor Green
        $downloaded = $true
    }
    catch {
        Write-Warning "Kaggle download failed: $_"
    }
}

if ($downloaded) {
    $normalDirs = Get-ChildItem "$targetDir\raw" -Recurse -Directory | Where-Object { $_.Name -match "CRAKING_FREE|NORMAL|rolled_scale|good" }
    if ($normalDirs) {
        $files = Get-ChildItem $normalDirs[0].FullName -Filter *.jpg
        $trainCount = [int]($files.Count * 0.7)
        for ($i = 0; $i -lt $files.Count; $i++) {
            if ($i -lt $trainCount) {
                Copy-Item $files[$i].FullName -Destination $patchcoreTrainGood -Force
            } else {
                Copy-Item $files[$i].FullName -Destination $patchcoreValidGood -Force
            }
        }
        Write-Host "[OK] Extracted $($files.Count) normal metallic surface images to $patchcoreTrainGood" -ForegroundColor Green
    }
} else {
    Write-Host "[INFO] Generating high-resolution synthetic metallic rail surface textures..." -ForegroundColor Yellow
    python -c "
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

for split, count in [('train/good', 20), ('valid/good', 10), ('test/good', 5)]:
    out_dir = f'data/external/rail_normal_only/{split}'
    os.makedirs(out_dir, exist_ok=True)
    for i in range(count):
        # Base steel gradient texture
        arr = np.random.normal(120, 10, (224, 224, 3)).astype(np.uint8)
        # Add smooth steel rolling streaks
        for row in range(0, 224, 4):
            arr[row:row+2, :, :] = np.clip(arr[row:row+2, :, :].astype(int) + np.random.randint(-15, 15), 0, 255)
        
        img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=0.8))
        img.save(f'{out_dir}/steel_normal_{i:03d}.jpg')
print('[OK] Generated synthetic metallic texture training and validation samples.')
"
}

Write-Host "`nPatchCore metallic surface dataset ready in: data\external\rail_normal_only" -ForegroundColor Green
