# Services package exports (tc.v1 SOTA).

from src.services.s3 import (
    S3Service,
    s3_service,
    generate_presigned_upload_url,
    generate_presigned_download_url,
)
from src.services.downsampling import (
    lttb_downsample,
    downsample_telemetry_lttb,
)
from src.services.alerts import (
    register_subscriber,
    unregister_subscriber,
    broadcast_event,
    broadcast_alert,
    dispatch_defect_alert,
)
from src.services.idempotency import (
    check_idempotency,
    record_idempotency,
)
from src.services.observability import (
    logger,
    StructuredLogger,
    RequestTraceMiddleware,
    metrics_endpoint,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    DEFECTS_CREATED,
    TELEMETRY_SAMPLES_INGESTED,
    ACTIVE_SESSIONS,
    ML_INFERENCE_LATENCY,
)
from src.services.audit import (
    AuditService,
    audit_service,
)
from src.services.webhooks import (
    WebhookService,
    webhook_service,
)
from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
    redis_breaker,
    s3_breaker,
    webhook_breaker,
)

__all__ = [
    "S3Service",
    "s3_service",
    "generate_presigned_upload_url",
    "generate_presigned_download_url",
    "lttb_downsample",
    "downsample_telemetry_lttb",
    "register_subscriber",
    "unregister_subscriber",
    "broadcast_event",
    "broadcast_alert",
    "dispatch_defect_alert",
    "check_idempotency",
    "record_idempotency",
    "logger",
    "StructuredLogger",
    "RequestTraceMiddleware",
    "metrics_endpoint",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "DEFECTS_CREATED",
    "TELEMETRY_SAMPLES_INGESTED",
    "ACTIVE_SESSIONS",
    "ML_INFERENCE_LATENCY",
    "AuditService",
    "audit_service",
    "WebhookService",
    "webhook_service",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenError",
    "redis_breaker",
    "s3_breaker",
    "webhook_breaker",
]
