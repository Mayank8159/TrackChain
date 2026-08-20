# FastAPI entrypoint: app factory, CORS, router mounting, startup/shutdown.

from __future__ import annotations

import base64
import time
from typing import List

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.config import get_settings
from src.core.logging import setup_logging
from src.db.session import engine, Base
from src.schemas.telemetry import (
    ProcessFrameRequest,
    ProcessFrameResponse,
    LineGeometry,
)
from src.api.routes import health, telemetry, defects, sessions, media

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
    description="TrackChain Integrated Track Monitoring & Edge AI Backend API",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health.router)
app.include_router(telemetry.router)
app.include_router(defects.router)
app.include_router(sessions.router)
app.include_router(media.router)


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
    raw = base64.b64decode(b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from provided base64 payload")
    return img


def detect_lines(img: np.ndarray) -> np.ndarray:
    """Run Canny → HoughLinesP and return detected segments."""
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
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        length = float(np.hypot(dx, dy))
        angle = float(np.degrees(np.arctan2(dy, dx)))
        result.append(
            LineGeometry(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                angle_deg=round(angle, 2),
                length=round(length, 2),
            )
        )
    return result


@app.post("/process-frame", response_model=ProcessFrameResponse, tags=["Frame Processing"])
def process_frame(req: ProcessFrameRequest):
    """Process incoming base64 video frame and extract track rail and sleeper lines."""
    t0 = time.perf_counter()

    try:
        img = decode_frame(req.frame)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid frame: {exc}")

    h, w = img.shape[:2]
    raw_lines = detect_lines(img)
    geometry = lines_to_geometry(raw_lines)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return ProcessFrameResponse(
        camera_id=req.camera_id,
        resolution=[w, h],
        line_count=len(geometry),
        lines=geometry,
        processing_ms=elapsed_ms,
        status="ok",
    )


# Lambda / Serverless Mangum handler
handler = Mangum(app)
