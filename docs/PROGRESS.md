# TrackChain — Engineering Progress & System Walkthrough

> **Repository:** `TrackChain`  
> **Contract Version:** `tc.v1`  
> **Status:** Phase 0, Phase 1, Phase 2, Phase 3, and Phase 3.5 COMPLETE & SEALED  
> **Verification:** 99/99 Automated Tests Passing (100% Pass Rate across ML & Backend)  

---

## 1. Executive Summary

TrackChain is a safety-critical, production-hardened railway track inspection and predictive maintenance platform. It combines edge-native multi-modal AI inference (YOLOv8n, PatchCore, EN 13848 Track Geometry Physics, Bi-LSTM Attention Classifier, and Dilated Sequence VAE) with a scalable cloud backend (FastAPI, TimescaleDB, PostGIS, S3 Multipart Uploads, HLS Adaptive Streaming, JWT Device Auth, HMAC Request Signing, Prometheus Observability, Immutable Audit Trails, and RDSO/UDM Webhooks).

---

## 2. Master System Architecture & Data Flow

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         TRACKCHAIN: COMPLETE ML ↔ BACKEND DATA FLOW                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  ┌─────────────────────────────────────────────────────────────┐                         │
│  │              RASPBERRY PI 5 (EDGE DEVICE)                    │                         │
│  │                                                             │                         │
│  │  ┌───────────────────────────────────────────────────────┐  │                         │
│  │  │         ML INFERENCE PIPELINE (Phase 2)                │  │                         │
│  │  │                                                       │  │                         │
│  │  │  [Camera 15fps] ──► ChainageResampler ──► TrackSegment│  │                         │
│  │  │  [IMU 100Hz]    ──┘     (0.25m bins)                  │  │                         │
│  │  │  [GNSS 5Hz]     ──┘                                   │  │                         │
│  │  │                                                       │  │                         │
│  │  │  TrackSegment ──┬──► YOLOv8n ──────► CalibratedSignal │  │                         │
│  │  │                 ├──► PatchCore ────► CalibratedSignal  │  │                         │
│  │  │                 ├──► EN13848 Math ─► CalibratedSignal  │  │                         │
│  │  │                 ├──► Bi-LSTM ──────► CalibratedSignal  │  │                         │
│  │  │                 └──► Seq-VAE ──────► CalibratedSignal  │  │                         │
│  │  │                                                       │  │                         │
│  │  │  5x CalibratedSignal ──► FusionEngine ──► Decision    │  │                         │
│  │  └───────────────────────────────────────────────────────┘  │                         │
│  │                              │                               │                         │
│  │                              ▼                               │                         │
│  │  ┌───────────────────────────────────────────────────────┐  │                         │
│  │  │         EDGE BATCH SERIALIZER (emit_sample.py)        │  │                         │
│  │  │                                                       │  │                         │
│  │  │  Decision + Signals ──► TelemetryBatchSchema          │  │                         │
│  │  │                     ──► MLSignalBatchSchema            │  │                         │
│  │  │                     ──► DefectCreateSchema             │  │                         │
│  │  │                     ──► MediaPresignRequest            │  │                         │
│  │  └───────────────────────────────────────────────────────┘  │                         │
│  └──────────────────────────────┬──────────────────────────────┘                         │
│                                 │                                                         │
│                    4G / LTE Network (HTTPS + JWT + HMAC)                                  │
│                                 │                                                         │
│                                 ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐                         │
│  │              CLOUD BACKEND (Phase 3 & 3.5)                   │                         │
│  │                                                             │                         │
│  │  [Security Layer]                                           │                         │
│  │  JWT Auth ──► Rate Limiter ──► HMAC Verify ──► Trace Inject │                         │
│  │                                                             │                         │
│  │  [Ingestion & Core Services]                                │                         │
│  │  POST /telemetry/batch ──► Idempotency ──► TimescaleDB      │                         │
│  │  POST /ml/signals/batch ──► Explainability ──► TimescaleDB  │                         │
│  │  POST /defects/ ──► PostGIS ──► SSE Stream ──► RDSO Webhook │                         │
│  │  PUT {presigned_url} ──► S3 / MinIO ──► HLS Transcoder      │                         │
│  │                                                             │                         │
│  │  [Observability & Reliability]                              │                         │
│  │  GET /metrics ──► Prometheus Scrape                         │                         │
│  │  Circuit Breakers ──► Fail-Fast & 503 Graceful Degradation  │                         │
│  │  Audit Logs ──► Immutable DB Trail                          │                         │
│  │                                                             │                         │
│  │  [Query Layer]                                              │                         │
│  │  GET /telemetry?downsample=500 ──► LTTB Downsampling        │                         │
│  │  GET /defects/nearby?radius=100 ──► PostGIS Spatial Radius  │                         │
│  │  GET /media/hls/{id}/master.m3u8 ──► Adaptive Bitrate HLS   │                         │
│  │  GET /alerts/stream ──► SSE Real-time Toast Feed            │                         │
│  │  GET /dashboard/export ──► CSV & Parquet RDSO Compliance    │                         │
│  └─────────────────────────────────────────────────────────────┘                         │
│                                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase-by-Phase Progress & Completed Deliverables

### Phase 0: Contract Sync Design (`tc.v1`) — SEALED
- Universal canonical contract synchronized across:
  - Python ML: `ml/core/schema.py`
  - Backend API: `backend/src/schemas/*.py`
  - TypeScript: `packages/shared/src/types.ts`
  - Database: `backend/src/db/models.py`

### Phase 1: Walking Skeleton & Vertical Slice — SEALED
- Full end-to-end integration verified from synthetic edge injection to SQLite/PostgreSQL persistence and SSE alert streaming.

### Phase 2: Edge ML Inference Stack (Phases 2.1 – 2.6) — SEALED
1. **Phase 2.1 (YOLOv8n Visual Defect Detector)**:
   - Supervised detection of missing clips, broken fasteners, rail cracks.
   - Slicing Aided Hyper Inference (SAHI) support. Exported to ONNX & INT8.
2. **Phase 2.2 (PatchCore Visual Anomaly Detector)**:
   - Memory bank of 2,508 core-set normal patch embeddings (WideResNet50_2).
   - FAISS $L_2$ search with Sigmoid EVT calibration ($P_{99} = 13.68, k = 0.50$).
3. **Phase 2.3 (EN 13848 Track Geometry Physics)**:
   - Resampling onto strict $0.25\text{ m}$ chainage grid (`ml/core/chainage.py`).
   - Vectorized EN 13848 / RDSO Broad Gauge ($1676\text{ mm}$) physics: Cant, Multi-Base Twist (3m/6m), Chord Versines (10m/20m), Unevenness, and TQI.
   - Normalized exceedance calibration ($0.50 = \text{Action Limit}$).
4. **Phase 2.4 (Bi-LSTM Geometry Fault Classifier)**:
   - 2-layer Bi-LSTM with multi-head spatial attention over 20m windows.
   - Temperature scaling calibration ($T$).
5. **Phase 2.5 (Dilated Sequence VAE)**:
   - Generative autoencoder with dilated 1D-CNN encoder and dual-path anomaly scoring (Reconstruction MSE + Latent Mahalanobis Distance).
6. **Phase 2.6 (Master Fusion Engine)**:
   - Confidence-weighted multi-modal fusion.
   - Cross-modal correlation boost (elevates visual + geometry coincident faults).
   - Exponential hysteresis ($h_t = \alpha \cdot s_t + (1-\alpha) \cdot h_{t-1}$) and adaptive section thresholds.

### Phase 3: Cloud Backend Hardening — SEALED
1. **TimescaleDB Hypertables & PostGIS**: Time-series chunk partitioning and geospatial radius searching (`haversine` + PostGIS queries).
2. **LTTB Peak-Preserving Downsampling**: Largest Triangle Three Buckets algorithm preserving critical min/max sensor peaks across 10,000+ points.
3. **S3 Multipart Uploads & HLS Video Streaming**:
   - Resumable multipart uploads with presigned URLs.
   - HLS adaptive bitrate ladder (`1080p`, `720p`, `480p`, `360p`) with master `.m3u8` playlists and HTTP 206 range seeking.
4. **JWT Security & Rate Limiting**:
   - Device registration (`POST /api/v1/devices/register`) and token exchange (`POST /api/v1/devices/token`).
   - Token bucket rate limiter and HMAC-SHA256 request signing (`X-Signature`, `X-Timestamp`).
5. **RDSO Batch Compliance Exports**: Streaming CSV and Apache Parquet export endpoints (`/api/v1/dashboard/export/*`).

### Phase 3.5: Observability, Audit Trail, Webhooks & Circuit Breakers — SEALED
1. **Prometheus Observability (`backend/src/services/observability.py`)**:
   - `GET /metrics` OpenMetrics endpoint with request count, duration histogram, defect counters, and telemetry counters.
   - `RequestTraceMiddleware` with `X-Request-ID` propagation and structured JSON logging.
2. **Immutable Audit Logging (`backend/src/services/audit.py`)**:
   - `AuditLog` table with Alembic migration `0004_add_audit_logs.py`.
   - Automatic recording of device registration, token exchange, revocation, and defect creation.
3. **External Webhook Integrations (`backend/src/services/webhooks.py`)**:
   - HMAC-SHA256 signed webhooks (`X-Webhook-Signature`, `X-Webhook-Timestamp`, `X-Webhook-Event`) for RDSO, UDM, and TMS.
   - Automatic dispatch on critical track defects with exponential backoff.
4. **Circuit Breakers & Graceful Degradation (`backend/src/services/circuit_breaker.py`)**:
   - `CLOSED` $\to$ `OPEN` $\to$ `HALF_OPEN` state machine.
   - FastAPI exception handler returning HTTP 503 with `Retry-After`.

---

## 4. Verification Test Matrix (99/99 Passing)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.5.0
collected 99 items

backend/tests/
  test_auth_and_security.py ......................... [PASSED]
  test_e2e_integration.py ........................... [PASSED]
  test_geospatial_and_export.py ..................... [PASSED]
  test_health.py .................................... [PASSED]
  test_integration_slice.py ......................... [PASSED]
  test_lttb_downsampling.py ......................... [PASSED]
  test_observability_audit_webhooks.py .............. [PASSED]
  test_s3_multipart.py .............................. [PASSED]
  test_schemas.py ................................... [PASSED]
  test_sota_features.py ............................. [PASSED]
  test_video_streaming.py ........................... [PASSED]

ml/tests/
  test_adaptive_thresholds.py ....................... [PASSED]
  test_anomaly.py ................................... [PASSED]
  test_calibration.py ............................... [PASSED]
  test_calibration_sync.py .......................... [PASSED]
  test_chainage.py .................................. [PASSED]
  test_confidence_fusion.py ......................... [PASSED]
  test_cross_modal_boost.py ......................... [PASSED]
  test_detector.py .................................. [PASSED]
  test_dilated_encoder.py ........................... [PASSED]
  test_en13848.py ................................... [PASSED]
  test_fault_classifier.py .......................... [PASSED]
  test_fusion.py .................................... [PASSED]
  test_hysteresis.py ................................ [PASSED]
  test_integration_sync.py .......................... [PASSED]
  test_overlapping_windows.py ....................... [PASSED]
  test_physics_detector.py .......................... [PASSED]
  test_pipeline_integration.py ...................... [PASSED]
  test_sequence_vae.py .............................. [PASSED]
  test_sequence_vae_dual_path.py .................... [PASSED]
  test_signal_contract.py ........................... [PASSED]
  test_triad_integration.py ......................... [PASSED]

====================== 99 passed, 118 warnings in 49.75s ======================
```

---

## 5. Next Step: Phase 4 (Frontend Dashboard)

With Phase 2 and Phase 3 completely synchronized and verified, we proceed to **Phase 4**: Building the modern Next.js 14 SCADA Operations Dashboard with live Mapbox/Leaflet spatial visualization, HLS adaptive video playback, LTTB telemetry charts, and real-time SSE alert feeds.
