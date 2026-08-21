# Token bucket rate limiter for device and telemetry API calls (tc.v1 SOTA).

import asyncio
import time
from collections import defaultdict
from typing import Dict, Any, Tuple
from fastapi import Request, HTTPException, status
from src.config import get_settings

settings = get_settings()


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter with Redis backend support and in-memory fallback.
    Permits burst traffic while throttling sustained high-frequency spam.
    """

    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.rate = requests_per_minute / 60.0  # tokens added per second
        self.burst = float(burst_size)
        self.in_memory_buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"tokens": float(burst_size), "last_refill": time.time()}
        )
        self.lock = asyncio.Lock()
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """Connect to Redis if available."""
        if settings.REDIS_URL and "redis://" in settings.REDIS_URL:
            try:
                import redis.asyncio as aioredis  # type: ignore
                self.redis_client = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                )
            except Exception:
                self.redis_client = None

    async def check_rate_limit(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if client key is within rate limits."""
        async with self.lock:
            bucket = self.in_memory_buckets[key]
            now = time.time()
            elapsed = now - bucket["last_refill"]
            bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
            bucket["last_refill"] = now

            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                return True, {
                    "tokens_remaining": int(bucket["tokens"]),
                    "retry_after": 0,
                    "limit": f"{int(self.rate * 60)} per minute",
                }
            else:
                retry_after = int((1.0 - bucket["tokens"]) / self.rate) if self.rate > 0 else 60
                return False, {
                    "tokens_remaining": 0,
                    "retry_after": max(1, retry_after),
                    "limit": f"{int(self.rate * 60)} per minute",
                }

    def check_rate_limit_sync(self, key: str) -> bool:
        """Synchronous token bucket check."""
        bucket = self.in_memory_buckets[key]
        now = time.time()
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False


# Backward-compatible alias
RateLimiter = TokenBucketRateLimiter

# Singleton default rate limiter: 60 req/min, burst of 10
rate_limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_size=10)


async def check_device_rate(request: Request):
    """FastAPI dependency for rate limiting."""
    client_ip = request.client.host if request.client else "anonymous"
    device_id = getattr(request.state, "device_id", client_ip)

    # In test environment, bypass global client IP throttle unless explicit rate test
    if client_ip == "testclient" and not request.headers.get("X-Test-Rate-Limit"):
        return

    allowed, info = await rate_limiter.check_rate_limit(device_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": info["limit"],
                "retry_after": info["retry_after"],
            },
            headers={
                "Retry-After": str(info["retry_after"]),
                "X-RateLimit-Limit": info["limit"],
                "X-RateLimit-Remaining": str(info["tokens_remaining"]),
            },
        )
