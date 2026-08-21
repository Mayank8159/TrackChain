# HMAC request signing and replay attack protection (tc.v1 SOTA).

import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from src.config import get_settings

settings = get_settings()


class RequestSigner:
    """HMAC-SHA256 request signing and replay prevention."""

    def __init__(self, secret_key: Optional[str] = None, tolerance_seconds: int = 300):
        key = secret_key or settings.REQUEST_SIGNING_SECRET
        self.secret_key = key.encode("utf-8")
        self.tolerance = tolerance_seconds  # 5 minutes

    def compute_signature(self, method: str, path: str, timestamp: str, body: bytes) -> str:
        """Compute HMAC-SHA256 signature."""
        signing_string = f"{method.upper()}\n{path}\n{timestamp}\n".encode("utf-8") + body
        return hmac.new(self.secret_key, signing_string, hashlib.sha256).hexdigest()

    def verify_signature(
        self,
        method: str,
        path: str,
        timestamp: Optional[str],
        signature: Optional[str],
        body: bytes,
    ) -> bool:
        """Verify HMAC signature and timestamp freshness."""
        if not signature or not timestamp:
            return False

        # Validate timestamp within tolerance
        try:
            req_time = int(timestamp)
            now = int(time.time())
            if abs(now - req_time) > self.tolerance:
                return False
        except (ValueError, TypeError):
            return False

        expected = self.compute_signature(method, path, timestamp, body)
        return hmac.compare_digest(signature, expected)


# Singleton
request_signer = RequestSigner()


async def verify_request_signature(request: Request):
    """FastAPI dependency for validating signed API requests."""
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    body = await request.body()

    if not request_signer.verify_signature(
        method=request.method,
        path=request.url.path,
        timestamp=timestamp,
        signature=signature,
        body=body,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired request signature",
        )
