# TrackChain REST & WebSocket API Specification (tc.v1)

Base URL: `/api/v1`  
Schema Version: `tc.v1`  
Date Format: ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)

---

## 1. Device & Session Endpoints

### `POST /api/v1/sessions/start`
Starts a new track monitoring inspection session.
- **Request Body**: `SessionStartRequest`
```json
{
  "device_id": "RPI-ITMS-001",
  "name": "NDLS-AGC Mainline High-Speed Inspection Run",
  "track_id": "IR-NR-01",
  "track_section": "New Delhi to Mathura Junction (Km 0.0 to 140.0)",
  "track_direction": "down",
  "start_chainage_m": 0.0,
  "operator_name": "Inspector A. Sharma",
  "weather": "Clear"
}
```
- **Response**: `201 Created` (`SessionResponse`)

### `PATCH /api/v1/sessions/{session_id}/finish`
Concludes an inspection run.
- **Request Body**: `SessionFinishRequest`
```json
{
  "end_chainage_m": 140000.0,
  "status": "completed",
  "defects_count": 5
}
```

### `GET /api/v1/sessions`
Lists monitoring sessions with pagination and status filters.

### `GET /api/v1/sessions/{session_id}`
Returns complete session summary, coverage, and health metrics.

---

## 2. Telemetry Ingestion & Query Endpoints

### `POST /api/v1/telemetry/batch`
Batch ingestion of aggregated 1 Hz IMU/GNSS/Geometry records from the edge unit.
- **Headers**: `Idempotency-Key: <uuid>`
- **Request Body**: `TelemetryBatchIngestRequest`
```json
{
  "schema_version": "tc.v1",
  "idempotency_key": "7b8d4f90-1c23-4e89-b78f-a9b0c1d2e3f4",
  "timestamp": "2026-08-21T01:30:00Z",
  "session_id": "ses-delhi-agra-001",
  "device_id": "RPI-ITMS-001",
  "samples": [
    {
      "chainage_m": 12450.0,
      "speed_mps": 30.5,
      "speed_kmh": 110.0,
      "vertical_rms": 0.85,
      "lateral_rms": 0.42,
      "vibration_rms": 0.94,
      "track_gauge_mm": 1436.5,
      "cant_mm": 12.0,
      "twist_mm_per_m": 1.2,
      "latitude": 28.6139,
      "longitude": 77.2090
    }
  ]
}
```

### `GET /api/v1/sessions/{session_id}/telemetry`
Fetches downsampled telemetry curves for frontend graph rendering.
- **Query Params**: `chainage_start_m`, `chainage_end_m`, `downsample_factor`

---

## 3. S3 Media Upload & Presigning Endpoints

### `POST /api/v1/media/presign-upload`
Generates an authenticated S3 presigned PUT URL for direct edge-to-S3 uploads.
- **Request Body**: `PresignUploadRequest`
```json
{
  "session_id": "ses-delhi-agra-001",
  "device_id": "RPI-ITMS-001",
  "media_type": "video_segment",
  "filename": "segment_km12_km14.mp4",
  "content_type": "video/mp4",
  "chainage_start_m": 12000.0,
  "chainage_end_m": 14000.0
}
```
- **Response**: `200 OK` (`PresignUploadResponse`)

### `POST /api/v1/media/complete`
Confirms successful upload to S3 and registers the asset in the database.

### `GET /api/v1/media/{media_id}/presign-download`
Generates a time-limited S3 presigned GET URL for video playback or evidence viewing.

---

## 4. ML Signal & Defect Endpoints

### `POST /api/v1/ml/signals/batch`
Uploads raw and calibrated model detections per segment.
- **Request Body**: `MLSignalBatchRequest`

### `POST /api/v1/defects`
Registers an operational defect event flagged by ML fusion.
- **Request Body**: `DefectEventCreate`
```json
{
  "session_id": "ses-delhi-agra-001",
  "chainage_m": 12450.0,
  "defect_class": "missing_fastener",
  "defect_family": "visual_component",
  "severity": "critical",
  "decision": "INSPECT_KNOWN",
  "confidence": 0.94,
  "source_model": "yolo_v8_detector",
  "stream_source": "vision",
  "evidence_image_id": "med-evid-001",
  "video_media_id": "med-vid-001",
  "video_offset_seconds": 24.5
}
```

### `GET /api/v1/defects`
Filterable defect registry.
- **Query Params**: `session_id`, `severity`, `defect_class`, `status`, `chainage_min`, `chainage_max`

### `PATCH /api/v1/defects/{defect_id}/status`
Acknowledge or resolve a defect during maintenance workflows.

---

## 5. Dashboard Summary Endpoints

### `GET /api/v1/dashboard/summary`
Returns high-level statistics for the live SCADA control room dashboard.
- **Response**: `DashboardSummaryResponse`
```json
{
  "total_defects": 14,
  "critical_defects": 3,
  "distance_covered_km": 258.0,
  "avg_speed_kmh": 105.4,
  "open_alerts": 2,
  "defect_counts_by_class": {
    "missing_fastener": 6,
    "crack": 3,
    "twist_exceedance": 3,
    "gauge_widening": 2
  },
  "severity_distribution": {
    "critical": 3,
    "high": 4,
    "medium": 5,
    "low": 2
  }
}
```
