# ITMS Backend — Frame Processor

Python FastAPI service for railway track frame analysis. Runs as an AWS Lambda behind API Gateway via Mangum.

## Endpoints

| Method | Path             | Description                        |
|--------|------------------|------------------------------------|
| GET    | `/health`        | Health check                       |
| POST   | `/process-frame` | Accepts base64 frame, returns geometry telemetry |

## POST /process-frame

**Request**

```json
{
  "camera_id": "cam-00",
  "frame": "<base64-encoded JPEG/PNG>"
}
```

**Response**

```json
{
  "camera_id": "cam-00",
  "resolution": [640, 480],
  "line_count": 4,
  "lines": [
    {
      "x1": 50.0,
      "y1": 150.0,
      "x2": 590.0,
      "y2": 150.0,
      "angle_deg": 0.0,
      "length": 540.0
    }
  ],
  "processing_ms": 12.34,
  "status": "ok"
}
```

## Local Development

```bash
# Install deps
pip install -r requirements.txt

# Run dev server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Docs at http://127.0.0.1:8000/docs

## Docker / SAM Local

```bash
# Build
sam build

# Invoke locally
sam local invoke ProcessFrameFunction --event event.json

# Or run as container
docker build -t itms-backend .
docker run -p 8080:8080 itms-backend
```

## Smoke Test

```bash
python test_local.py --url http://127.0.0.1:8000/process-frame
```
