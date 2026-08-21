"""
Observability stack: Prometheus metrics, structured JSON logging, and request tracing (tc.v1 SOTA).
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings

settings = get_settings()

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter(
    "trackchain_http_requests_total",
    "Total HTTP requests handled by TrackChain backend",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "trackchain_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

DEFECTS_CREATED = Counter(
    "trackchain_defects_created_total",
    "Total track defect anomalies identified and recorded",
    ["defect_class", "severity", "source_model"],
)

TELEMETRY_SAMPLES_INGESTED = Counter(
    "trackchain_telemetry_samples_total",
    "Total high-frequency track geometry telemetry samples ingested",
)

ACTIVE_SESSIONS = Gauge(
    "trackchain_active_sessions",
    "Number of active monitoring sessions currently in progress",
)

ML_INFERENCE_LATENCY = Histogram(
    "trackchain_ml_inference_seconds",
    "ML model inference and fusion latency in seconds",
    ["model_name"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# --- Request Tracing ---
request_id_var: ContextVar[str] = ContextVar("request_id", default="system")


def get_current_request_id() -> str:
    """Retrieve active request ID from context."""
    return request_id_var.get()


# --- Structured Logger ---
class StructuredLogger:
    """JSON-formatted structured logger for cloud and container log aggregation."""

    def __init__(self, name: str = "trackchain"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        self.name = name

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        extra_dict = extra.copy() if extra else {}
        extra_dict["request_id"] = request_id_var.get()
        extra_dict["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        extra_dict["level"] = level.upper()
        extra_dict["logger"] = self.name
        extra_dict["message"] = message

        log_fn = getattr(self.logger, level.lower(), self.logger.info)
        try:
            log_fn(json.dumps(extra_dict))
        except Exception:
            log_fn(f"[{level.upper()}] {message} | {extra_dict}")

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log("info", message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        self._log("error", message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log("warning", message, extra)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log("debug", message, extra)


logger = StructuredLogger("trackchain")


# --- Request Tracing & Metrics Middleware ---
class RequestTraceMiddleware(BaseHTTPMiddleware):
    """Middleware that injects X-Request-ID, calculates latency, and records Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        token = request_id_var.set(request_id)
        start_time = time.time()

        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time
            endpoint = request.url.path

            # Increment metrics (skip metrics scraping endpoint itself to prevent metric bloat)
            if endpoint != "/metrics":
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=endpoint,
                    status_code=response.status_code,
                ).inc()

                REQUEST_LATENCY.labels(
                    method=request.method,
                    endpoint=endpoint,
                ).observe(duration)

            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": endpoint,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration = time.time() - start_time
            endpoint = request.url.path

            if endpoint != "/metrics":
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=endpoint,
                    status_code=500,
                ).inc()

                REQUEST_LATENCY.labels(
                    method=request.method,
                    endpoint=endpoint,
                ).observe(duration)

            logger.error(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": endpoint,
                    "error": str(exc),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,
            )
            raise
        finally:
            request_id_var.reset(token)


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint returning OpenMetrics / Prometheus plaintext data."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
