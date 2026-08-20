# =============================================================================
# extract_normal_dataset.ps1
# Extracts normal (defect-free) track images for PatchCore unsupervised training.
# Run from the repository root (D:\TrackChain).
# =============================================================================
$ErrorActionPreference = 'Stop'

$yoloRoot = "data\external\rail_defects"
$patchcoreRoot = "data\external\rail_normal_only"

Write-Host "Extracting normal-only railway images to $patchcoreRoot..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$patchcoreRoot\train\good" | Out-Null
New-Item -ItemType Directory -Force -Path "$patchcoreRoot\valid\good" | Out-Null
New-Item -ItemType Directory -Force -Path "$patchcoreRoot\test\good"  | Out-Null
New-Item -ItemType Directory -Force -Path "$patchcoreRoot\test\defect" | Out-Null

$copiedTrain = 0
$copiedValid = 0

function Copy-NormalImages($split, [ref]$count) {
    $imgDir = "$yoloRoot\$split\images"
    $lblDir = "$yoloRoot\$split\labels"
    $destDir = "$patchcoreRoot\$split\good"
    
    if (Test-Path $imgDir) {
        Get-ChildItem $imgDir -Filter *.jpg | ForEach-Object {
            $lblFile = Join-Path $lblDir ($_.BaseName + ".txt")
            # If label file doesn't exist, or is empty (0 bytes), it's a normal image
            if (-not (Test-Path $lblFile) -or ((Get-Item $lblFile).Length -eq 0)) {
                Copy-Item $_.FullName -Destination $destDir -Force
                $count.Value++
            }
        }
    }
}

Copy-NormalImages "train" ([ref]$copiedTrain)
Copy-NormalImages "valid" ([ref]$copiedValid)

# If no normal-only images exist, generate synthetic clean track images
if ($copiedTrain -eq 0) {
    Write-Host "[INFO] Generating synthetic defect-free baseline images for PatchCore..." -ForegroundColor Yellow
    python -c "
from PIL import Image, ImageDraw
import os

for split, count in [('train/good', 12), ('valid/good', 6), ('test/good', 4), ('test/defect', 4)]:
    os.makedirs(f'data/external/rail_normal_only/{split}', exist_ok=True)
    for i in range(count):
        img = Image.new('RGB', (640, 640), color=(70, 75, 80))
        draw = ImageDraw.Draw(img)
        # Rails
        draw.line([(180, 0), (180, 640)], fill=(180, 190, 200), width=16)
        draw.line([(460, 0), (460, 640)], fill=(180, 190, 200), width=16)
        # Sleepers
        for y in range(40, 640, 80):
            draw.rectangle([60, y, 580, y + 30], fill=(40, 30, 20))
            # Normal fasteners
            draw.rectangle([155, y + 5, 175, y + 25], fill=(120, 130, 140))
            draw.rectangle([465, y + 5, 485, y + 25], fill=(120, 130, 140))

        if 'defect' in split:
            # Add an oil stain / novel visual anomaly (irregular shape)
            draw.ellipse([260, 260, 380, 380], fill=(20, 15, 10))

        img.save(f'data/external/rail_normal_only/{split}/normal_{i:03d}.jpg')
print('[OK] Generated PatchCore normal-only and anomaly test splits.')
"
}

Write-Host "`nPatchCore dataset ready in: $patchcoreRoot" -ForegroundColor Green
