"""
Webhook notification service for pushing critical defect alerts to external railway systems (RDSO, UDM, TMS).
Supports HMAC-SHA256 payload signing, timestamp verification, and exponential backoff retry (tc.v1 SOTA).
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any
import httpx
from src.config import get_settings
from src.services.observability import logger

settings = get_settings()


class WebhookService:
    """Push notifications to external Indian Railways systems (RDSO, UDM, TMS)."""

    def __init__(self):
        self.webhook_urls: Dict[str, Optional[str]] = {
            "rdso": settings.RDSO_WEBHOOK_URL,
            "udm": settings.UDM_WEBHOOK_URL,
            "tms": settings.TMS_WEBHOOK_URL,
        }
        self.webhook_secrets: Dict[str, str] = {
            "rdso": settings.RDSO_WEBHOOK_SECRET,
            "udm": settings.UDM_WEBHOOK_SECRET,
            "tms": settings.TMS_WEBHOOK_SECRET,
        }

    def sign_payload(self, payload_str: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def send_alert(
        self,
        system: str,
        event_type: str,
        payload: Dict[str, Any],
        retry_count: int = 3,
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Send webhook alert to external system with exponential backoff retry."""
        system_lower = system.lower()
        if system_lower not in self.webhook_urls:
            raise ValueError(f"Unknown webhook system: {system}. Must be one of: rdso, udm, tms.")

        url = self.webhook_urls[system_lower]
        secret = self.webhook_secrets[system_lower]

        if not url:
            logger.debug(f"Webhook URL not configured for system '{system}', skipping dispatch.")
            return {"status": "skipped", "system": system_lower, "reason": "url_not_configured"}

        # Prepare formatted JSON payload with envelope metadata
        envelope = {
            "source": "trackchain",
            "system": system_lower,
            "event_type": event_type,
            "timestamp": int(time.time()),
            "data": payload,
        }
        payload_str = json.dumps(envelope, sort_keys=True)
        signature = self.sign_payload(payload_str, secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": str(envelope["timestamp"]),
            "X-Webhook-Event": event_type,
            "User-Agent": "TrackChain-Webhook-Dispatcher/1.0",
        }

        # Retry loop with exponential backoff
        for attempt in range(1, retry_count + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, content=payload_str, headers=headers)
                    response.raise_for_status()
                    logger.info(
                        f"webhook_dispatched_successfully",
                        extra={
                            "system": system_lower,
                            "event_type": event_type,
                            "attempt": attempt,
                            "status_code": response.status_code,
                        },
                    )
                    return {
                        "status": "delivered",
                        "system": system_lower,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    }
            except Exception as exc:
                logger.warning(
                    f"webhook_dispatch_failed",
                    extra={
                        "system": system_lower,
                        "event_type": event_type,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                if attempt == retry_count:
                    logger.error(
                        f"webhook_max_retries_exhausted",
                        extra={"system": system_lower, "event_type": event_type, "attempts": retry_count},
                    )
                    return {
                        "status": "failed",
                        "system": system_lower,
                        "error": str(exc),
                        "attempts": retry_count,
                    }
                # Short backoff for resilience
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))


webhook_service = WebhookService()
