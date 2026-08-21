# TrackChain REST, WebSocket & Observability API Specification (tc.v1)

Base URL: `/api/v1` (also aliased under `/api`)  
Schema Version: `tc.v1`  
Date Format: ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)

---

## 1. Security & Edge Device Management

### `POST /api/v1/devices/register`
Registers a new edge inspection trolley/locomotive unit and issues a secure API key.
- **Request Body**: `DeviceRegisterRequest`
```json
{
  "device_id": "RPI-5-ITMS-001",
  "name": "Track Inspection Cart Unit 1",
  "hardware_version": "Raspberry Pi 5 (8GB)",
  "firmware_version": "v1.4.2",
  "camera_model": "Sony IMX477 1080p60",
  "imu_model": "Bosch BNO085 100Hz",
  "gnss_model": "u-blox NEO-M9N RTK"
}
```
- **Response**: `200 OK` (`DeviceRegisterResponse` containing `api_key`)

### `POST /api/v1/devices/token`
Exchanges a valid device API key for a short-lived scoped JWT access token and refresh token.
- **Request Body**: `DeviceTokenRequest`
```json
{
  "device_id": "RPI-5-ITMS-001",
  "api_key": "tc_live_..."
}
```
- **Response**: `200 OK` (`DeviceTokenResponse` containing `access_token`, `refresh_token`, `expires_in_seconds`)

### `POST /api/v1/devices/refresh`
Rotates an expired JWT access token using a valid refresh token.

### `POST /api/v1/devices/revoke`
Revokes an edge device to block future token issuance and API access.

---

## 2. Session Management

### `POST /api/v1/sessions`
Starts a new track monitoring inspection session.
- **Headers**: `Authorization: Bearer <jwt>`
- **Request Body**: `SessionCreate`
```json
{
  "id": "ses-delhi-agra-001",
  "name": "Northern Railway Track Inspection Run",
  "track_id": "IR-NR-MAIN01",
  "track_section": "Delhi-Mathura Km 102.0 to 108.0",
  "track_direction": "down",
  "start_chainage_m": 102000.0,
  "operator_name": "Senior Section Engineer (P-Way)",
  "device_id": "RPI-5-ITMS-001"
}
```
- **Response**: `200 OK` (`SessionResponse`)

### `PATCH /api/v1/sessions/{session_id}`
Updates or finishes an inspection run (end chainage, status, defect count).

### `GET /api/v1/sessions`
Lists monitoring sessions with pagination, track ID, and status filters.

### `GET /api/v1/sessions/{session_id}`
Returns complete session metadata, status, coverage, and defect metrics.

---

## 3. Telemetry Ingestion & Query Endpoints

### `POST /api/v1/telemetry/batch`
High-throughput batch ingestion of IMU/GNSS/geometry records with idempotency and HMAC request signing.
- **Headers**:
  - `Authorization: Bearer <jwt>`
  - `X-Signature: <hmac_sha256>`
  - `X-Timestamp: <epoch_seconds>`
  - `X-Idempotency-Key: <unique_key>`
- **Request Body**: `TelemetryBatchIngest`
```json
{
  "schema_version": "tc.v1",
  "idempotency_key": "idemp-tel-104928",
  "session_id": "ses-delhi-agra-001",
  "device_id": "RPI-5-ITMS-001",
  "samples": [
    {
      "chainage_m": 102400.0,
      "speed_mps": 30.5,
      "speed_kmh": 109.8,
      "vibration_rms": 0.85,
      "track_gauge_mm": 1676.2,
      "cant_mm": 12.0,
      "twist_mm_per_m": 0.8,
      "latitude": 28.5350,
      "longitude": 77.2840
    }
  ]
}
```

### `GET /api/v1/telemetry`
Retrieves telemetry samples with optional **LTTB Peak-Preserving Downsampling** (`?downsample=500`).
- **Query Params**: `session_id`, `downsample`, `limit`

---

## 4. ML Signal & Defect Endpoints

### `POST /api/v1/ml/signals/batch`
Batch ingestion of multi-modal model detections for model explainability.

### `POST /api/v1/defects`
Registers an AI-detected or fused defect event.
- **Request Body**: `DefectCreate`
```json
{
  "session_id": "ses-delhi-agra-001",
  "device_id": "RPI-5-ITMS-001",
  "chainage_m": 102450.0,
  "defect_class": "missing_fastener",
  "defect_family": "visual_component",
  "severity": "critical",
  "decision": "INSPECT_KNOWN",
  "confidence": 0.94,
  "source_model": "yolo_v8_detector",
  "stream_source": "vision",
  "description": "Missing fastening clip at KM 102+450",
  "latitude": 28.5340,
  "longitude": 77.2850,
  "supporting_signals": [
    {
      "model_name": "yolo_v8_detector",
      "model_version": "v1.0.0",
      "signal_type": "bounding_box",
      "raw_score": 0.94,
      "calibrated_score": 0.94,
      "threshold": 0.5,
      "fired": true,
      "label": "missing_fastener",
      "bbox": [120.0, 240.0, 180.0, 310.0]
    }
  ]
}
```

### `GET /api/v1/defects`
Lists defects with severity, class, status, and session filters.

### `GET /api/v1/defects/nearby`
PostGIS / Haversine spatial radius query finding defects near given latitude/longitude.
- **Query Params**: `lat`, `lon`, `radius_meters` (default 500m)

### `GET /api/v1/defects/geojson`
Returns standard GeoJSON `FeatureCollection` for direct rendering in Mapbox/Leaflet GIS maps.

---

## 5. Media & HLS Video Streaming

### `POST /api/v1/media/presign-upload`
Generates AWS S3 / MinIO presigned PUT URLs for direct edge asset uploads.

### `POST /api/v1/media/multipart/initiate`
Initiates an AWS S3 multipart upload for large video files.

### `POST /api/v1/media/multipart/presign-part`
Generates presigned URLs for individual 5MB+ video parts.

### `POST /api/v1/media/multipart/complete`
Completes multipart upload and triggers background HLS adaptive bitrate transcoding.

### `GET /api/v1/media/stream/{media_id}`
HTTP 206 Partial Content video streaming supporting range seeking.

### `GET /api/v1/media/hls/{media_id}/master.m3u8`
Adaptive bitrate HLS master playlist for variable bandwidth SCADA players (`1080p`, `720p`, `480p`, `360p`).

---

## 6. Real-Time Alerting & SCADA Exports

### `GET /api/v1/alerts/stream`
Server-Sent Events (SSE) stream broadcasting real-time defect alerts directly to connected dashboards.

### `GET /api/v1/dashboard/summary`
Live SCADA KPI summary (total defects, critical count, open alerts, severity breakdown).

### `GET /api/v1/dashboard/export/csv`
Streams CSV defect records for RDSO and track maintenance teams.

### `GET /api/v1/dashboard/export/parquet`
Generates high-performance Apache Parquet binary file for large-scale data lake analytics.

---

## 7. Observability, Metrics & Health

### `GET /metrics`
Prometheus OpenMetrics endpoint scraping request counts, latency histograms, defect counters, and ML latency.

### `GET /health` & `GET /health/ready`
Liveness and readiness probes verifying database and storage connectivity.

### `GET /warmup`
Lightweight ping endpoint to prevent serverless Lambda cold starts.
