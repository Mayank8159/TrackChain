# FastAPI entrypoint: app factory, CORS, router mounting, startup/shutdown (tc.v1 SOTA).

from __future__ import annotations

import base64
import time
from typing import List

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from mangum import Mangum
except ImportError:
    Mangum = None

import numpy as np
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.core.logging import setup_logging
from src.db.session import engine, Base
from src.services.observability import RequestTraceMiddleware, metrics_endpoint
from src.services.circuit_breaker import CircuitBreakerOpenError
from src.schemas.telemetry import (
    ProcessFrameRequest,
    ProcessFrameResponse,
    LineGeometry,
)
from src.api.routes import (
    health,
    telemetry,
    defects,
    sessions,
    media,
    devices,
    dashboard,
    ml,
    alerts,
)
from fastapi import Request
from fastapi.responses import JSONResponse

# Setup structured logging
logger = setup_logging()
settings = get_settings()

# Initialize DB tables in development
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:
    logger.warning(f"Database initialization warning: {exc}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="TrackChain Integrated Track Monitoring & Edge AI Backend API (tc.v1)",
)

# Tracing & Metrics Middleware
app.add_middleware(RequestTraceMiddleware)

# CORS Allowlist
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Device-ID", "X-Idempotency-Key", "X-Signature"],
)

# In-memory token bucket rate limiter per device / IP
_rate_limit_store: dict[str, list[float]] = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Bypass health probes and metrics from rate limits
    if request.url.path in ["/health", "/api/health", "/api/v1/health", "/metrics", "/warmup"]:
        return await call_next(request)

    device_key = (
        request.headers.get("X-Device-ID")
        or request.headers.get("Authorization")
        or request.client.host
        if request.client
        else "anonymous"
    )
    now = time.time()

    # Clean old records older than 60s
    timestamps = _rate_limit_store.get(device_key, [])
    timestamps = [t for t in timestamps if now - t < 60.0]

    limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    if len(timestamps) >= limit:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "detail": f"Device ingestion rate limit exceeded ({limit} req/min). Please back off.",
                "retry_after": 60,
            },
            headers={"Retry-After": "60"},
        )

    timestamps.append(now)
    _rate_limit_store[device_key] = timestamps

    return await call_next(request)

# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(CircuitBreakerOpenError)
async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenError):
    """Graceful degradation when external services or circuit breakers are open."""
    return JSONResponse(
        status_code=503,
        content={
            "error": "service_degraded",
            "message": exc.message,
            "retry_after": exc.retry_after,
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus OpenMetrics scraping endpoint."""
    return await metrics_endpoint()


# Mount Health probes at root
app.include_router(health.router)

# Group domain routers into unified API sub-router
api_router = APIRouter()
api_router.include_router(telemetry.router)
api_router.include_router(defects.router)
api_router.include_router(sessions.router)
api_router.include_router(media.router)
api_router.include_router(devices.router)
api_router.include_router(dashboard.router)
api_router.include_router(ml.router)
api_router.include_router(alerts.router)

# Mount API endpoints under both /api and /api/v1
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")


@app.get("/warmup", tags=["Health"])
@app.get("/api/v1/warmup", tags=["Health"])
def warmup_handler():
    """Lightweight ping endpoint to keep serverless Lambda functions warm and prevent cold starts."""
    return {"status": "warm", "timestamp": time.time(), "service": "trackchain-backend"}


# ---------------------------------------------------------------------------
# ML Model Loading & Honesty Enforcement (tc.v1 SOTA - Fix B3)
# ---------------------------------------------------------------------------
YOLO_WEIGHTS_LOADED = False
yolo_model = None

try:
    from pathlib import Path
    weights_candidates = [
        Path("artifacts/checkpoints/yolov8n.pt"),
        Path("../artifacts/checkpoints/yolov8n.pt"),
        Path("yolov8n.pt"),
        Path("ml/weights/vision/yolo_rail_v0.1.pt"),
        Path("../ml/weights/vision/yolo_rail_v0.1.pt"),
        Path("ml/weights/vision/yolov8n.pt"),
        Path("../ml/weights/vision/yolov8n.pt"),
    ]
    found_weights = next((p for p in weights_candidates if p.exists()), None)
    try:
        from ultralytics import YOLO  # type: ignore
        weight_target = str(found_weights) if found_weights else "yolov8n.pt"
        yolo_model = YOLO(weight_target)
        YOLO_WEIGHTS_LOADED = True
        logger.info(f"✅ Real YOLO neural network loaded successfully from {weight_target}")
    except Exception as e:
        logger.warning(f"Could not initialize YOLO model: {e}")
        YOLO_WEIGHTS_LOADED = False
except Exception as exc:
    logger.warning(f"ML weight loading encountered exception: {exc}")
    YOLO_WEIGHTS_LOADED = False


# ---------------------------------------------------------------------------
# Computer-vision helpers for edge frame processing
# ---------------------------------------------------------------------------

CANNY_LOW = 50
CANNY_HIGH = 150
HOUGH_RHO = 1
HOUGH_THETA = np.pi / 180
HOUGH_THRESHOLD = 80
HOUGH_MIN_LINE_LENGTH = 30
HOUGH_MAX_LINE_GAP = 10


def decode_frame(b64: str) -> np.ndarray:
    """Decode a base64 string into an OpenCV BGR image."""
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is not installed in the current environment")
    raw = base64.b64decode(b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from provided base64 payload")
    return img


def detect_lines(img: np.ndarray) -> np.ndarray:
    """Run Canny → HoughLinesP and return detected segments."""
    if cv2 is None:
        return np.array([])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, CANNY_LOW, CANNY_HIGH)
    lines = cv2.HoughLinesP(
        edges,
        HOUGH_RHO,
        HOUGH_THETA,
        HOUGH_THRESHOLD,
        minLineLength=HOUGH_MIN_LINE_LENGTH,
        maxLineGap=HOUGH_MAX_LINE_GAP,
    )
    return lines if lines is not None else np.array([])


def lines_to_geometry(lines: np.ndarray) -> List[LineGeometry]:
    """Convert raw Hough segments into structured LineGeometry objects."""
    result: List[LineGeometry] = []
    if lines is None or len(lines) == 0:
        return result
    for line in lines:
        pts = np.asarray(line).reshape(-1)
        if len(pts) < 4:
            continue
        x1, y1, x2, y2 = float(pts[0]), float(pts[1]), float(pts[2]), float(pts[3])
        dx = x2 - x1
        dy = y2 - y1
        length = float(np.hypot(dx, dy))
        angle = float(np.degrees(np.arctan2(dy, dx)))
        result.append(
            LineGeometry(
                x1=round(x1, 2),
                y1=round(y1, 2),
                x2=round(x2, 2),
                y2=round(y2, 2),
                angle_deg=round(angle, 2),
                length=round(length, 2),
            )
        )
    return result


@app.post("/process-frame", response_model=ProcessFrameResponse, tags=["Frame Processing"])
def process_frame(req: ProcessFrameRequest):
    """Process incoming base64 video frame with OpenCV Hough transform and real YOLO ML inference."""
    t0 = time.perf_counter()

    try:
        img = decode_frame(req.frame)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid frame: {exc}")

    h, w = img.shape[:2]
    raw_lines = detect_lines(img)
    geometry = lines_to_geometry(raw_lines)

    # Classify geometric lines into longitudinal rails vs transverse sleepers based on angle
    rails = [l for l in geometry if abs(l.angle_deg) < 35 or abs(l.angle_deg) > 145]
    sleepers = [l for l in geometry if 35 <= abs(l.angle_deg) <= 145]

    # Run real YOLOv8 detection
    yolo_boxes = []
    if YOLO_WEIGHTS_LOADED and yolo_model is not None:
        try:
            results = yolo_model.predict(source=img, conf=0.25, verbose=False)
            if results and len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    cls_idx = int(box.cls[0].item() if hasattr(box.cls[0], "item") else box.cls[0])
                    name = results[0].names.get(cls_idx, str(cls_idx))
                    conf = float(box.conf[0].item() if hasattr(box.conf[0], "item") else box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    yolo_boxes.append({
                        "class": name,
                        "confidence": round(conf, 4),
                        "xmin": round(float(xyxy[0]), 2),
                        "ymin": round(float(xyxy[1]), 2),
                        "xmax": round(float(xyxy[2]), 2),
                        "ymax": round(float(xyxy[3]), 2),
                    })
        except Exception as e:
            logger.warning(f"YOLO inference failed: {e}")


    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return ProcessFrameResponse(
        camera_id=req.camera_id,
        resolution=(w, h),
        line_count=len(geometry),
        lines=geometry,
        rails=rails,
        sleepers=sleepers,
        processing_ms=elapsed_ms,
        inference_ms=elapsed_ms,
        yolo_weights_loaded=YOLO_WEIGHTS_LOADED,
        yolo_boxes=yolo_boxes,
        status="ok",
    )


# Lambda / Serverless Mangum handler
handler = Mangum(app) if Mangum else None

