from __future__ import annotations

import base64
import time
from typing import List

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ITMS Frame Processor",
    version="0.1.0",
    description="Integrated Track Monitoring System — frame analysis backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ProcessFrameRequest(BaseModel):
    frame: str = Field(..., description="Base64-encoded JPEG / PNG frame")
    camera_id: str = Field(default="cam-00", description="Source camera identifier")


class LineGeometry(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    angle_deg: float = Field(..., description="Angle of the line in degrees")
    length: float


class ProcessFrameResponse(BaseModel):
    camera_id: str
    resolution: List[int] = Field(..., description="[width, height] of processed frame")
    line_count: int
    lines: List[LineGeometry]
    processing_ms: float
    status: str = "ok"


# ---------------------------------------------------------------------------
# Computer-vision helpers
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
                x1=float(x1), y1=float(y1),
                x2=float(x2), y2=float(y2),
                angle_deg=round(angle, 2),
                length=round(length, 2),
            )
        )
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok", "service": "itms-backend"}


@app.post("/process-frame", response_model=ProcessFrameResponse)
def process_frame(req: ProcessFrameRequest):
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
    )


# ---------------------------------------------------------------------------
# Lambda / Mangum adapter
# ---------------------------------------------------------------------------

handler = Mangum(app)
