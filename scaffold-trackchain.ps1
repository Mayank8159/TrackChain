# =============================================================================
# scaffold-trackchain.ps1
# Creates the TrackChain monorepo layout: directories + named stub files.
# Each file gets a one-line description header (no implementation).
#
# Usage:
#   .\scaffold-trackchain.ps1                     # creates ./TrackChain
#   .\scaffold-trackchain.ps1 -Root C:\dev\tc     # custom root
#   .\scaffold-trackchain.ps1 -Force              # overwrite existing files
# =============================================================================
param(
    [string]$Root = (Join-Path (Get-Location) 'TrackChain'),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# ---- Build a description-only stub appropriate to the file type -------------
function New-StubContent([string]$FileName, [string]$Desc) {
    $ext = ([System.IO.Path]::GetExtension($FileName)).ToLower()
    if ($ext -in '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs') {
        return "// $Desc"
    }
    elseif ($ext -eq '.css') {
        return "/* $Desc */"
    }
    elseif ($ext -eq '.md') {
        return "# $Desc"
    }
    elseif ($ext -eq '.json') {
        # keep JSON valid while still carrying the description
        return "{`n  `"_comment`": `"$Desc`"`n}"
    }
    else {
        # py, yaml, toml, sh, ps1, Dockerfile, Makefile, gitignore, env, etc.
        return "# $Desc"
    }
}

# ---- The full layout: relative path -> description -------------------------
$files = @(
    # ---- Root ----------------------------------------------------------------
    @{ Path = 'README.md';                Desc = 'TrackChain monorepo overview, quickstart, and links to architecture and ML design docs.' }
    @{ Path = '.gitignore';               Desc = 'Ignore node_modules, venv, artifacts, data, env files, and OS junk.' }
    @{ Path = '.editorconfig';            Desc = 'Consistent formatting across editors: indent, charset, newline.' }
    @{ Path = 'package.json';             Desc = 'Monorepo root. Defines JS/TS workspaces (app, packages/shared) and root scripts.' }
    @{ Path = 'pnpm-workspace.yaml';      Desc = 'pnpm workspace definition for the JS/TS packages.' }
    @{ Path = 'turbo.json';               Desc = 'Turborepo pipeline config for cached build/dev/test across packages.' }
    @{ Path = 'Makefile';                 Desc = 'Developer targets: setup, dev, test, docker-up, ml-train, ml-evaluate.' }
    @{ Path = 'docker-compose.yml';       Desc = 'Local stack: Postgres/TimescaleDB, backend API, Next.js web, MinIO (S3-compatible) for video.' }
    @{ Path = '.env.example';             Desc = 'Template for root environment variables (compose project, ports).' }

    # ---- app/ : Next.js frontend (App Router) --------------------------------
    @{ Path = 'app/package.json';                 Desc = 'Next.js web app. Depends on packages/shared types; calls the backend API.' }
    @{ Path = 'app/next.config.mjs';              Desc = 'Next.js config: env passthrough, image domains, API rewrites to backend.' }
    @{ Path = 'app/tsconfig.json';                Desc = 'TypeScript config with path aliases (@/*) for the app.' }
    @{ Path = 'app/tailwind.config.ts';           Desc = 'Tailwind CSS theme and content globs.' }
    @{ Path = 'app/postcss.config.mjs';           Desc = 'PostCSS plugins (tailwindcss, autoprefixer).' }
    @{ Path = 'app/.env.local.example';           Desc = 'Frontend env template: NEXT_PUBLIC_API_BASE_URL and feature flags.' }
    @{ Path = 'app/public/.gitkeep';              Desc = 'Static assets directory placeholder.' }
    @{ Path = 'app/src/app/layout.tsx';           Desc = 'Root App Router layout: global nav, providers, and page shell.' }
    @{ Path = 'app/src/app/page.tsx';             Desc = 'Dashboard home: KPI cards, recent defects, and live status.' }
    @{ Path = 'app/src/app/globals.css';          Desc = 'Global styles and Tailwind base layer.' }
    @{ Path = 'app/src/app/defects/page.tsx';     Desc = 'Defects table + filters; links each defect to evidence image and video offset.' }
    @{ Path = 'app/src/app/map/page.tsx';         Desc = 'GIS view: GNSS track polyline with severity-colored defect markers.' }
    @{ Path = 'app/src/app/video/page.tsx';       Desc = 'Video playback synced with telemetry graphs; seeks to defect timestamps.' }
    @{ Path = 'app/src/components/charts/TelemetryChart.tsx';   Desc = 'Time-series chart for speed, vibration RMS, roll/pitch vs chainage.' }
    @{ Path = 'app/src/components/charts/DefectTimeline.tsx';   Desc = 'Defect counts per km section and severity distribution.' }
    @{ Path = 'app/src/components/map/TrackMap.tsx';            Desc = 'Leaflet/OSM map component rendering the track and defect markers.' }
    @{ Path = 'app/src/components/ui/Card.tsx';                 Desc = 'Reusable card container for dashboard panels.' }
    @{ Path = 'app/src/components/ui/StatBadge.tsx';            Desc = 'Small badge for KPI values and severity levels.' }
    @{ Path = 'app/src/lib/api.ts';               Desc = 'Typed backend client: fetch telemetry, defects, sessions, and presigned media URLs.' }
    @{ Path = 'app/src/lib/types.ts';             Desc = 'Frontend DTO types; mirrors packages/shared contracts.' }
    @{ Path = 'app/src/hooks/useTelemetry.ts';    Desc = 'Hook to fetch/poll telemetry series for a session.' }
    @{ Path = 'app/src/hooks/useDefects.ts';      Desc = 'Hook to fetch/poll defect events with filters.' }

    # ---- backend/ : FastAPI "backend proper" ---------------------------------
    @{ Path = 'backend/pyproject.toml';           Desc = 'Python project metadata and dependencies for the FastAPI service.' }
    @{ Path = 'backend/requirements.txt';         Desc = 'Pinned backend dependencies (FastAPI, SQLAlchemy, boto3, etc.).' }
    @{ Path = 'backend/Dockerfile';               Desc = 'Container build for the backend API.' }
    @{ Path = 'backend/.env.example';             Desc = 'Backend env template: DATABASE_URL, S3 bucket, auth secrets.' }
    @{ Path = 'backend/alembic.ini';              Desc = 'Alembic config pointing at db/migrations for schema versioning.' }
    @{ Path = 'backend/src/__init__.py';          Desc = 'Backend package marker.' }
    @{ Path = 'backend/src/main.py';              Desc = 'FastAPI entrypoint: app factory, CORS, router mounting, startup/shutdown.' }
    @{ Path = 'backend/src/config.py';            Desc = 'Settings loader (pydantic-settings) reading environment variables.' }
    @{ Path = 'backend/src/api/__init__.py';      Desc = 'API package marker.' }
    @{ Path = 'backend/src/api/deps.py';          Desc = 'Shared FastAPI dependencies: DB session, auth, pagination.' }
    @{ Path = 'backend/src/api/routes/__init__.py'; Desc = 'Routes package marker.' }
    @{ Path = 'backend/src/api/routes/health.py';   Desc = 'Liveness/readiness endpoints for orchestration.' }
    @{ Path = 'backend/src/api/routes/telemetry.py'; Desc = 'POST batched telemetry rows and GET downsampled series for graphs.' }
    @{ Path = 'backend/src/api/routes/defects.py';   Desc = 'POST defect events; GET defect list with severity/class filters.' }
    @{ Path = 'backend/src/api/routes/sessions.py';  Desc = 'Session/run management: create, list, and summarize runs.' }
    @{ Path = 'backend/src/api/routes/media.py';     Desc = 'Issue presigned S3 upload/download URLs for video segments and images.' }
    @{ Path = 'backend/src/core/__init__.py';     Desc = 'Core package marker.' }
    @{ Path = 'backend/src/core/security.py';     Desc = 'Device tokens/JWT verification and role-based access.' }
    @{ Path = 'backend/src/core/logging.py';      Desc = 'Structured logging setup for the API.' }
    @{ Path = 'backend/src/db/__init__.py';       Desc = 'DB package marker.' }
    @{ Path = 'backend/src/db/session.py';        Desc = 'SQLAlchemy engine/session factory for Postgres/TimescaleDB.' }
    @{ Path = 'backend/src/db/models.py';         Desc = 'ORM models: telemetry, defects, sessions, media metadata.' }
    @{ Path = 'backend/src/db/migrations/env.py'; Desc = 'Alembic migration environment bound to the app models.' }
    @{ Path = 'backend/src/db/migrations/README.md'; Desc = 'How to create and apply schema migrations.' }
    @{ Path = 'backend/src/services/__init__.py'; Desc = 'Services package marker.' }
    @{ Path = 'backend/src/services/s3.py';       Desc = 'S3 client: presigned URLs, bucket checks; works with AWS or MinIO.' }
    @{ Path = 'backend/src/services/alerts.py';   Desc = 'Alert dispatch (email/SMS) when a defect crosses a severity threshold.' }
    @{ Path = 'backend/src/schemas/__init__.py';  Desc = 'Schemas package marker.' }
    @{ Path = 'backend/src/schemas/telemetry.py'; Desc = 'Pydantic request/response models for telemetry payloads.' }
    @{ Path = 'backend/src/schemas/defects.py';   Desc = 'Pydantic models for defect events and query filters.' }
    @{ Path = 'backend/tests/__init__.py';        Desc = 'Tests package marker.' }
    @{ Path = 'backend/tests/test_health.py';     Desc = 'Smoke tests for health and basic API wiring.' }

    # ---- ml/ : the machine-learning package ----------------------------------
    @{ Path = 'ml/pyproject.toml';                Desc = 'Python project metadata and dependencies for the ML package.' }
    @{ Path = 'ml/requirements.txt';              Desc = 'Pinned ML dependencies (torch, ultralytics, sklearn, etc.).' }
    @{ Path = 'ml/README.md';                     Desc = 'ML package overview: two-stream design, calibration, and rule fusion.' }
    @{ Path = 'ml/__init__.py';                   Desc = 'ML package marker.' }
    @{ Path = 'ml/core/__init__.py';              Desc = 'Core package marker.' }
    @{ Path = 'ml/core/schema.py';                Desc = 'Shared contracts: ChainageWindow, GeometryFeatures, CalibratedSignal, SegmentDecision.' }
    @{ Path = 'ml/core/chainage.py';              Desc = 'Resample all sensor streams onto the common distance (chainage) axis.' }
    @{ Path = 'ml/core/registry.py';              Desc = 'Load any model by name from artifacts/checkpoints.' }
    @{ Path = 'ml/data/__init__.py';              Desc = 'Data package marker.' }
    @{ Path = 'ml/data/synthetic.py';             Desc = 'Generate synthetic vision and geometry data with known fault signatures.' }
    @{ Path = 'ml/data/datasets.py';              Desc = 'PyTorch Datasets for RSDDs, NEU, and fastener imagery.' }
    @{ Path = 'ml/data/loaders.py';               Desc = 'DataLoader builders with train/val splits and augmentation.' }
    @{ Path = 'ml/features/__init__.py';          Desc = 'Features package marker.' }
    @{ Path = 'ml/features/en13848.py';           Desc = 'Deterministic EN 13848 physics features: twist, cross-level, versine, unevenness.' }
    @{ Path = 'ml/models/__init__.py';            Desc = 'Models package marker.' }
    @{ Path = 'ml/models/vision/__init__.py';     Desc = 'Vision models package marker.' }
    @{ Path = 'ml/models/vision/detector.py';     Desc = 'YOLOv8 wrapper for known discrete defects (what + where).' }
    @{ Path = 'ml/models/vision/anomaly.py';      Desc = 'PatchCore normal-only anomaly detector for novel surface defects.' }
    @{ Path = 'ml/models/vision/texture_classifier.py'; Desc = 'Optional CNN texture classifier (e.g. corrugation) if a labeled class is required.' }
    @{ Path = 'ml/models/geometry/__init__.py';   Desc = 'Geometry models package marker.' }
    @{ Path = 'ml/models/geometry/physics_detector.py'; Desc = 'Threshold detector on EN 13848 features for known geometry faults.' }
    @{ Path = 'ml/models/geometry/fault_classifier.py'; Desc = 'Bi-LSTM that types flagged geometry windows from physics features.' }
    @{ Path = 'ml/models/geometry/sequence_vae.py'; Desc = 'Sequence VAE trained on normal geometry to flag novel patterns.' }
    @{ Path = 'ml/calibration/__init__.py';       Desc = 'Calibration package marker.' }
    @{ Path = 'ml/calibration/temperature.py';    Desc = 'Temperature/Platt scaling to turn network logits into true probabilities.' }
    @{ Path = 'ml/calibration/fpr_threshold.py';  Desc = 'Set anomaly-score operating thresholds at a target false-positive rate.' }
    @{ Path = 'ml/fusion/__init__.py';            Desc = 'Fusion package marker.' }
    @{ Path = 'ml/fusion/rules.py';               Desc = 'Rule-based fusion over calibrated signals with persistence (OK/KNOWN/NOVEL).' }
    @{ Path = 'ml/training/__init__.py';          Desc = 'Training package marker.' }
    @{ Path = 'ml/training/base_trainer.py';      Desc = 'Shared training loop: checkpointing, logging, early stopping.' }
    @{ Path = 'ml/training/train_detector.py';    Desc = 'Fine-tune the YOLO detector on real/synthetic defect imagery.' }
    @{ Path = 'ml/training/train_anomaly.py';     Desc = 'Fit PatchCore on normal-only imagery.' }
    @{ Path = 'ml/training/train_fault_classifier.py'; Desc = 'Train the Bi-LSTM geometry fault classifier.' }
    @{ Path = 'ml/training/train_sequence_vae.py'; Desc = 'Train the sequence VAE on normal geometry windows.' }
    @{ Path = 'ml/inference/__init__.py';         Desc = 'Inference package marker.' }
    @{ Path = 'ml/inference/pipeline.py';         Desc = 'End-to-end: segment -> models -> calibrate -> fuse -> SegmentDecision.' }
    @{ Path = 'ml/inference/exporters.py';        Desc = 'Export models to ONNX/TFLite for edge deployment.' }
    @{ Path = 'ml/evaluation/__init__.py';        Desc = 'Evaluation package marker.' }
    @{ Path = 'ml/evaluation/metrics.py';         Desc = 'PR/ROC, FPR, and calibration-curve metrics.' }
    @{ Path = 'ml/evaluation/reports.py';         Desc = 'Render evaluation reports for judges and validation.' }
    @{ Path = 'ml/utils/__init__.py';             Desc = 'Utils package marker.' }
    @{ Path = 'ml/utils/logging.py';              Desc = 'ML logging helpers.' }
    @{ Path = 'ml/utils/seeding.py';              Desc = 'Deterministic seeding for reproducible runs.' }
    @{ Path = 'ml/utils/io.py';                   Desc = 'Artifact and config read/write helpers.' }
    @{ Path = 'ml/configs/data.yaml';             Desc = 'Dataset paths, splits, and augmentation settings.' }
    @{ Path = 'ml/configs/detector.yaml';         Desc = 'YOLO detector hyperparameters and class list.' }
    @{ Path = 'ml/configs/anomaly.yaml';          Desc = 'PatchCore settings and normal-data source.' }
    @{ Path = 'ml/configs/fault_classifier.yaml'; Desc = 'Bi-LSTM window size, features, and hyperparameters.' }
    @{ Path = 'ml/configs/sequence_vae.yaml';     Desc = 'Sequence VAE architecture and training settings.' }
    @{ Path = 'ml/configs/calibration.yaml';      Desc = 'Calibration method and target FPR budget.' }
    @{ Path = 'ml/configs/fusion.yaml';           Desc = 'Fusion thresholds and persistence window.' }
    @{ Path = 'ml/configs/chainage.yaml';         Desc = 'Chainage bin size and sensor-to-distance mapping.' }
    @{ Path = 'ml/scripts/download_data.sh';      Desc = 'Fetch public datasets (RSDDs, NEU, fastener sets).' }
    @{ Path = 'ml/scripts/make_synthetic.py';     Desc = 'Generate synthetic training/validation data.' }
    @{ Path = 'ml/scripts/train_all.py';          Desc = 'Train all models in sequence from configs.' }
    @{ Path = 'ml/scripts/calibrate.py';          Desc = 'Fit calibration for all models and persist to artifacts/calibration.' }
    @{ Path = 'ml/scripts/evaluate.py';           Desc = 'Run evaluation and emit reports.' }
    @{ Path = 'ml/scripts/export_edge.py';        Desc = 'Export calibrated models for the edge device.' }
    @{ Path = 'ml/tests/test_en13848.py';         Desc = 'Unit tests for physics feature math.' }
    @{ Path = 'ml/tests/test_chainage.py';        Desc = 'Unit tests for distance resampling and alignment.' }
    @{ Path = 'ml/tests/test_calibration.py';     Desc = 'Unit tests for calibration routines.' }
    @{ Path = 'ml/tests/test_fusion.py';          Desc = 'Unit tests for rule fusion and persistence.' }

    # ---- packages/ : shared JS/TS contracts ----------------------------------
    @{ Path = 'packages/shared/package.json';     Desc = 'Shared TypeScript package consumed by app and any Node tooling.' }
    @{ Path = 'packages/shared/tsconfig.json';    Desc = 'TypeScript build config for the shared package.' }
    @{ Path = 'packages/shared/src/index.ts';     Desc = 'Barrel export for shared types and constants.' }
    @{ Path = 'packages/shared/src/types.ts';     Desc = 'Canonical DTO types: telemetry, defects, sessions, decisions.' }

    # ---- infra/ : deployment -------------------------------------------------
    @{ Path = 'infra/docker/web.Dockerfile';      Desc = 'Production container for the Next.js web app.' }
    @{ Path = 'infra/docker/backend.Dockerfile';  Desc = 'Production container for the FastAPI backend.' }
    @{ Path = 'infra/docker/ml.Dockerfile';       Desc = 'Container for ML training/inference jobs.' }
    @{ Path = 'infra/aws/s3-policy.json';         Desc = 'Least-privilege S3 bucket policy for media uploads.' }
    @{ Path = 'infra/aws/iot-policy.json';        Desc = 'IoT/device auth policy for edge telemetry ingestion.' }

    # ---- scripts/ : repo automation ------------------------------------------
    @{ Path = 'scripts/setup.ps1';                Desc = 'One-shot local setup: install JS deps, create venvs, pull env templates.' }
    @{ Path = 'scripts/dev.ps1';                  Desc = 'Start the full local dev stack (db, backend, web) with hot reload.' }
    @{ Path = 'scripts/seed.py';                  Desc = 'Seed the database with sample sessions, telemetry, and defects.' }

    # ---- docs/ ----------------------------------------------------------------
    @{ Path = 'docs/architecture.md';             Desc = 'System architecture: app -> backend -> DB + S3, and the edge/ML data flow.' }
    @{ Path = 'docs/ml-design.md';                Desc = 'ML design: two streams, calibration, rule fusion, and dataset mapping.' }
    @{ Path = 'docs/api.md';                      Desc = 'Backend API reference: endpoints, payloads, and auth.' }
    @{ Path = 'docs/hardware-bom.md';             Desc = 'Sensor BOM and bring-up notes (camera, IMUs, GNSS, odometry).' }

    # ---- data/ + artifacts/ (gitignored content, keep dirs) ------------------
    @{ Path = 'data/raw/.gitkeep';                Desc = 'Raw ingested datasets placeholder.' }
    @{ Path = 'data/processed/.gitkeep';          Desc = 'Processed/training-ready datasets placeholder.' }
    @{ Path = 'data/external/.gitkeep';           Desc = 'Third-party datasets placeholder (RSDDs, NEU).' }
    @{ Path = 'artifacts/checkpoints/.gitkeep';   Desc = 'Model checkpoints placeholder.' }
    @{ Path = 'artifacts/calibration/.gitkeep';   Desc = 'Fitted calibration parameters placeholder.' }
    @{ Path = 'artifacts/exports/.gitkeep';       Desc = 'Edge exports (ONNX/TFLite) placeholder.' }
)

# ---- Create root + all files ------------------------------------------------
if (-not (Test-Path $Root)) {
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
}

$created = 0
$skipped = 0

foreach ($f in $files) {
    $full = Join-Path $Root $f.Path
    $dir  = Split-Path $full -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    if ((Test-Path $full) -and -not $Force) {
        $skipped++
        continue
    }

    $fileName = Split-Path $full -Leaf
    $content  = New-StubContent -FileName $fileName -Desc $f.Desc
    Set-Content -Path $full -Value $content -Encoding UTF8
    $created++
    Write-Host "  + $($f.Path)"
}

Write-Host ""
Write-Host "TrackChain scaffold complete."
Write-Host "  Root:    $Root"
Write-Host "  Created: $created files"
Write-Host "  Skipped: $skipped existing files (use -Force to overwrite)"
