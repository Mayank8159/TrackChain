# TrackChain System Architecture Specification (tc.v1)

```text
ML inference layer (Edge/Cloud)  ──►  Backend API & Database  ──►  Frontend Dashboard (Next.js)
```

---

## 1. System Overview

TrackChain is a safety-critical railway track intelligence platform designed to integrate high-speed optical computer vision, inertial measurement unit (IMU) dynamics, GNSS spatial tracking, and EN 13848-1 track geometry analytics.

The Phase 0 architecture locks the **canonical contract (`tc.v1`)** across:
- `packages/shared/src/types.ts` (TypeScript DTOs)
- `backend/src/schemas/` (Pydantic models)
- `backend/src/db/models.py` (SQLAlchemy ORM tables)
- `ml/core/schema.py` (ML dataclasses and enums)

---

## 2. Core Subsystems

### A. Edge Acquisition & ML Layer (`ml/`)
- **Raspberry Pi / Jetson Edge Unit**:
  - Direct frame streaming and downsampling.
  - Asynchronous sensor collection (IMU at 100–200 Hz, GNSS at 10 Hz).
  - Spatial distance resampling onto a uniform chainage grid (`0.25m` to `2.0m` partitions).
  - Dual-stream inference (Vision YOLOv8 + PatchCore; Geometry EN 13848 + Bi-LSTM + Sequence VAE).
  - Temperature scaling and False Positive Rate (FPR) calibration.
  - Persistence rule fusion emitting `SegmentDecision` and `MLSignal` records.

### B. Cloud & Backend Services (`backend/`)
- **FastAPI Core Gateway**:
  - Direct AWS S3 presigned upload/download coordination (no heavy video binaries passing through backend compute).
  - High-throughput batch ingestion for telemetry (`POST /api/v1/telemetry/batch`) and ML signals (`POST /api/v1/ml/signals/batch`).
  - Idempotent API processing via `idempotency_key` deduplication.
  - PostgreSQL / TimescaleDB hypertable persistence for time-series sensor data and relational entities.

### C. Web Visualization Dashboard (`app/`)
- **Next.js 14 App Router & SCADA UI**:
  - Real-time WebSocket/SSE live feed with automatic reconnect and simulation fallbacks.
  - Chainage-synchronized video playback with telemetry overlay curves.
  - Leaflet GIS corridor mapping with defect hotspot markers and severity symbology.
  - RDSO Comprehensive Track Index (CTI) and EN 13848-1 compliance report generation.

---

## 3. Storage Architecture: Database vs. S3

```text
┌────────────────────────────────────────────────────────┐
│                   Storage Partition                    │
├──────────────────────────┬─────────────────────────────┤
│ PostgreSQL / TimescaleDB │ AWS S3 Object Storage       │
├──────────────────────────┼─────────────────────────────┤
│ - devices                │ - video_segment (.mp4)      │
│ - sessions               │ - evidence_image (.jpg)     │
│ - track_segments         │ - thumbnail (.webp)         │
│ - telemetry_samples      │ - report_file (.pdf, .csv)  │
│ - ml_signals             │                             │
│ - defect_events          │                             │
│ - calibration_artifacts  │                             │
│ - model_registry         │                             │
│ - alerts                 │                             │
└──────────────────────────┴─────────────────────────────┘
```

---

## 4. Chainage-First Distance Synchronization

Railway maintenance operations operate strictly by distance (e.g. `Km 45+250`). TrackChain aligns asynchronous sensor timelines to distance:

$$\text{Timestamp } t \xrightarrow{\text{GNSS/Odometry}} \text{Chainage } s \xrightarrow{\text{Resampling}} \text{TrackSegment } [\text{start}_m, \text{end}_m]$$

1. Every entity contains `chainage_m` or `(chainage_start_m, chainage_end_m)`.
2. Telemetry curves, video scrubbers, map waypoints, and defect rows index against the same discrete `segment_id`.
3. Defect events link to `video_media_id` and `video_offset_seconds` for seekable visual audit trails.
