# FastAPI entrypoint — Lambda-safe with deferred imports and cold-start guards.
# All heavy imports (cv2, torch, ultralytics) are lazy to keep cold start < 5s.

from __future__ import annotations

import base64
import os
import time
from functools import lru_cache
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.schemas.telemetry import ProcessFrameRequest, ProcessFrameResponse, LineGeometry

# ---------------------------------------------------------------------------
# Lazy / guarded heavy imports — NEVER at top level for Lambda
# ---------------------------------------------------------------------------

_cv2: Any = None
_np: Any = None
_yolo_model: Any = None
_yolo_loaded: bool = False
_models_loaded: bool = False


def _load_cv2():
    global _cv2, _np
    if _cv2 is None:
        try:
            import cv2 as cv2_mod
            _cv2 = cv2_mod
        except ImportError:
            _cv2 = False
    if _np is None:
        try:
            import numpy as np_mod
            _np = np_mod
        except ImportError:
            _np = False


def _load_yolo():
    """Load YOLO model once per Lambda container. Subsequent invocations reuse it."""
    global _yolo_model, _yolo_loaded, _models_loaded
    if _models_loaded:
        return
    _models_loaded = True

    from pathlib import Path

    candidates = [
        Path("artifacts/checkpoints/yolov8n.pt"),
        Path("../artifacts/checkpoints/yolov8n.pt"),
        Path("yolov8n.pt"),
        Path("../yolov8n.pt"),
        Path("ml/weights/vision/yolov8n.pt"),
        Path("../ml/weights/vision/yolov8n.pt"),
    ]
    found = next((p for p in candidates if p.exists()), None)

    try:
        from ultralytics import YOLO  # type: ignore

        weight_target = str(found) if found else "yolov8n.pt"
        _yolo_model = YOLO(weight_target)
        _yolo_loaded = True
        _log(f"YOLO loaded from {weight_target}")
    except Exception as e:
        _log(f"YOLO unavailable (degraded mode): {e}")
        _yolo_loaded = False


def _log(msg: str):
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if level == "DEBUG":
        print(f"[ITMS] {msg}")
    else:
        print(f"[ITMS] {msg}")


# ---------------------------------------------------------------------------
# Settings (deferred — reads env at call time, not import time)
# ---------------------------------------------------------------------------


@lru_cache()
def _get_settings():
    from src.config import get_settings
    return get_settings()


# ---------------------------------------------------------------------------
# DB init — only run in non-Lambda (containerised / local dev)
# ---------------------------------------------------------------------------

_is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None


def _init_db_if_needed():
    if _is_lambda:
        return  # Skip DB DDL on Lambda cold start — use Alembic migrations instead.
    try:
        from src.db.session import Base, engine
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        _log(f"DB init skipped: {exc}")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = _get_settings()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        from src.services.artifacts import load_artifacts
        app.state.ml = load_artifacts()
        from src.services.pipeline import start_worker
        app.state.worker = await start_worker(app.state.ml)
        
        import asyncio
        from src.services.alerts import set_main_event_loop
        set_main_event_loop(asyncio.get_running_loop())
        
        yield
        
        # Shutdown
        if hasattr(app.state, "worker"):
            app.state.worker.cancel()

    _application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="TrackChain Integrated Track Monitoring & Edge AI Backend API",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = first executed) ---

    _application.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "https://trackchain.vercel.app").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Observability middleware (lazy import) ---
    try:
        from src.services.observability import RequestTraceMiddleware, metrics_endpoint
        _application.add_middleware(RequestTraceMiddleware)

        @_application.get("/metrics", tags=["Observability"])
        async def metrics():
            return await metrics_endpoint()
    except ImportError:
        _log("Observability middleware unavailable")

    # --- Circuit breaker handler (lazy import) ---
    try:
        from src.services.circuit_breaker import CircuitBreakerOpenError

        @_application.exception_handler(CircuitBreakerOpenError)
        async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenError):
            return JSONResponse(
                status_code=503,
                content={"error": "service_degraded", "message": exc.message, "retry_after": exc.retry_after},
                headers={"Retry-After": str(exc.retry_after)},
            )
    except ImportError:
        pass

    # --- Security headers ---
    @_application.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # --- Rate limiter (in-memory, works per-container in Lambda) ---
    _rate_limit_store: dict[str, list[float]] = {}

    @_application.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path in ("/health", "/api/health", "/api/v1/health", "/metrics", "/warmup"):
            return await call_next(request)

        device_key = (
            request.headers.get("X-Device-ID")
            or request.headers.get("Authorization")
            or (request.client.host if request.client else "anonymous")
        )
        now = time.time()
        timestamps = [t for t in _rate_limit_store.get(device_key, []) if now - t < 60.0]

        settings_local = _get_settings()
        limit = settings_local.RATE_LIMIT_REQUESTS_PER_MINUTE
        if len(timestamps) >= limit:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "retry_after": 60},
                headers={"Retry-After": "60"},
            )
        timestamps.append(now)
        _rate_limit_store[device_key] = timestamps
        return await call_next(request)

    # --- Routers ---
    from src.api.routes import (
        health, telemetry, defects, sessions, media,
        devices, dashboard, ml, alerts, ingest
    )
    from src.gateway import node_ws, live_ws

    _application.include_router(health.router)
    _application.include_router(node_ws.router)
    _application.include_router(live_ws.router)

    api_router = APIRouter()
    api_router.include_router(telemetry.router)
    api_router.include_router(defects.router)
    api_router.include_router(sessions.router)
    api_router.include_router(media.router)
    api_router.include_router(devices.router)
    api_router.include_router(dashboard.router)
    api_router.include_router(ml.router)
    api_router.include_router(alerts.router)
    api_router.include_router(ingest.router)

    _application.include_router(api_router, prefix="/api")
    _application.include_router(api_router, prefix="/api/v1")

    # --- Warmup endpoint ---
    @_application.get("/warmup", tags=["Health"])
    @_application.get("/api/v1/warmup", tags=["Health"])
    def warmup_handler():
        return {"status": "warm", "timestamp": time.time(), "service": "trackchain-backend"}

    # --- Process-frame endpoint ---
    @_application.post("/process-frame", tags=["Frame Processing"], response_model=ProcessFrameResponse)
    async def process_frame(req: ProcessFrameRequest):
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _process_frame_logic, req, LineGeometry, ProcessFrameResponse)

    return _application


# ---------------------------------------------------------------------------
# Frame processing (self-contained, no top-level heavy deps)
# ---------------------------------------------------------------------------

CANNY_LOW = 50
CANNY_HIGH = 150
HOUGH_RHO = 1
HOUGH_THETA_OPTIONAL: float = 3.141592653589793 / 180  # pi/180
HOUGH_THRESHOLD = 80
HOUGH_MIN_LINE_LENGTH = 30
HOUGH_MAX_LINE_GAP = 10


def _decode_frame(b64: str) -> Any:
    _load_cv2()
    if not _cv2:
        raise RuntimeError("OpenCV not available")
    raw = base64.b64decode(b64)
    arr = _np.frombuffer(raw, dtype=_np.uint8)
    img = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from provided base64 payload")
    return img


def _detect_lines(img: Any) -> Any:
    _load_cv2()
    if not _cv2:
        return _np.array([])
    gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
    blurred = _cv2.GaussianBlur(gray, (5, 5), 0)
    edges = _cv2.Canny(blurred, CANNY_LOW, CANNY_HIGH)
    lines = _cv2.HoughLinesP(
        edges, HOUGH_RHO, HOUGH_THETA_OPTIONAL, HOUGH_THRESHOLD,
        minLineLength=HOUGH_MIN_LINE_LENGTH, maxLineGap=HOUGH_MAX_LINE_GAP,
    )
    return lines if lines is not None else _np.array([])


def _lines_to_geometry(raw_lines: Any, LineGeometry: Any) -> List[Any]:
    _load_cv2()
    result = []
    if raw_lines is None or len(raw_lines) == 0:
        return result
    for line in raw_lines:
        pts = _np.asarray(line).reshape(-1)
        if len(pts) < 4:
            continue
        x1, y1, x2, y2 = float(pts[0]), float(pts[1]), float(pts[2]), float(pts[3])
        dx, dy = x2 - x1, y2 - y1
        length = float(_np.hypot(dx, dy))
        angle = float(_np.degrees(_np.arctan2(dy, dx)))
        result.append(LineGeometry(
            x1=round(x1, 2), y1=round(y1, 2),
            x2=round(x2, 2), y2=round(y2, 2),
            angle_deg=round(angle, 2), length=round(length, 2),
        ))
    return result


def _process_frame_logic(req: Any, LineGeometry: Any, ProcessFrameResponse: Any) -> Any:
    t0 = time.perf_counter()

    try:
        img = _decode_frame(req.frame)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid frame: {exc}")

    h, w = img.shape[:2]
    raw_lines = _detect_lines(img)
    geometry = _lines_to_geometry(raw_lines, LineGeometry)

    rails = [l for l in geometry if abs(l.angle_deg) < 35 or abs(l.angle_deg) > 145]
    sleepers = [l for l in geometry if 35 <= abs(l.angle_deg) <= 145]

    # YOLO Inference (lazy, fallback to ONNX if ultralytics unavailable or ONNX_MODE=true)
    yolo_boxes: List[dict] = []
    
    if os.getenv("ONNX_MODE", "").lower() == "true":
        # Pure ONNX execution (Torch-free cloud mode)
        try:
            from src.services.onnx_inference import infer_yolo, load_onnx_model, _loaded as _onnx_loaded
            if not _onnx_loaded:
                load_onnx_model()
            yolo_boxes = infer_yolo(img, conf_thresh=0.25)
            global _yolo_loaded
            _yolo_loaded = _onnx_loaded
        except Exception as e:
            _log(f"ONNX inference failed: {e}")
    else:
        # Standard Ultralytics execution
        _load_yolo()
        if _yolo_loaded and _yolo_model is not None:
            try:
                results = _yolo_model.predict(source=img, conf=0.25, verbose=False)
                if results and len(results) > 0 and results[0].boxes is not None:
                    for box in results[0].boxes:
                        cls_idx = int(box.cls[0].item() if hasattr(box.cls[0], "item") else box.cls[0])
                        name = results[0].names.get(cls_idx, str(cls_idx))
                        conf = float(box.conf[0].item() if hasattr(box.conf[0], "item") else box.conf[0])
                        xyxy = box.xyxy[0].tolist()
                        yolo_boxes.append({
                            "class": name, "confidence": round(conf, 4),
                            "xmin": round(float(xyxy[0]), 2), "ymin": round(float(xyxy[1]), 2),
                            "xmax": round(float(xyxy[2]), 2), "ymax": round(float(xyxy[3]), 2),
                        })
            except Exception as e:
                _log(f"YOLO inference failed: {e}")

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Calculate honest vision degradation status and confidence score
    hough_lines_count = len(rails) + len(sleepers)
    yolo_boxes_count = len(yolo_boxes)

    # Check for glare, excessive noise, or sensor overexposure
    is_glare_or_noise = False
    if len(geometry) > 40:
        is_glare_or_noise = True
    elif _cv2 and _np:
        try:
            gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
            mean_val = float(_np.mean(gray))
            if mean_val > 210 or (mean_val > 130 and len(geometry) > 25):
                is_glare_or_noise = True
        except Exception:
            pass

    vision_status = "OK"
    if is_glare_or_noise:
        vision_status = "DEGRADED"
        vision_confidence_score = 0.15
    elif len(rails) < 2 and hough_lines_count < 2:
        vision_status = "DEGRADED"
        vision_confidence_score = 0.0
    elif hough_lines_count < 4 and len(rails) < 2:
        vision_status = "LOW_CONFIDENCE"
        vision_confidence_score = round(min(1.0, (hough_lines_count * 0.1) + (yolo_boxes_count * 0.2)), 2)
    else:
        vision_confidence_score = round(min(1.0, (hough_lines_count * 0.1) + (yolo_boxes_count * 0.2)), 2)

    return ProcessFrameResponse(
        camera_id=req.camera_id,
        resolution=(w, h),
        line_count=len(geometry),
        lines=geometry,
        rails=rails,
        sleepers=sleepers,
        processing_ms=elapsed_ms,
        inference_ms=elapsed_ms,
        yolo_weights_loaded=_yolo_loaded,
        yolo_boxes=yolo_boxes,
        status="ok",
        vision_status=vision_status,
        vision_confidence_score=vision_confidence_score,
    )


# ---------------------------------------------------------------------------
# Create app + Lambda Mangum adapter
# ---------------------------------------------------------------------------

app = create_app()
_init_db_if_needed()

# Mangum handler — ALWAYS defined, never None
from mangum import Mangum  # type: ignore  # guaranteed in requirements
handler = Mangum(app, api_gateway_base_path=os.getenv("API_GATEWAY_BASE_PATH", ""))
