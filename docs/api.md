# Backend API reference: endpoints, payloads, and auth.

# TrackChain Backend API Reference

## Authentication
Requests should include the header:
```http
X-API-Key: <your-api-key>
```

## Endpoints

### 1. Health & Probes
- `GET /health`: Liveness probe.
- `GET /ready`: Readiness probe.

### 2. Telemetry Ingestion & Query
- `POST /api/telemetry`: Ingest array of time-series sensor points.
- `GET /api/telemetry?session_id=...&downsample=100`: Query downsampled telemetry series.

### 3. Defect Management
- `POST /api/defects`: Register newly detected defect event.
- `GET /api/defects?session_id=...&severity=critical`: Filter defect registry.

### 4. Inspection Sessions
- `POST /api/sessions`: Create new track inspection session.
- `GET /api/sessions`: List past runs and defect statistics.

### 5. Media & Storage
- `POST /api/media/presign-upload`: Get S3 PUT URL for edge upload.
- `POST /api/media/presign-download`: Get S3 GET URL for browser playback.

### 6. Frame Processing
- `POST /process-frame`: Real-time OpenCV Canny/Hough line analysis on base64 image.
