"""
Circuit breaker pattern for graceful degradation and cascading failure prevention (tc.v1 SOTA).
Protects external network integrations (Redis, S3, Webhooks, Push Notifications).
"""

import asyncio
import time
from enum import Enum
from functools import wraps
from typing import Callable, Any, Type, Tuple, Optional


class CircuitState(Enum):
    CLOSED = "closed"          # Normal operation: all calls execute
    OPEN = "open"              # Failing: fast fail without invoking upstream
    HALF_OPEN = "half_open"    # Probing: trial request allowed to verify health


class CircuitBreakerOpenError(Exception):
    """Raised immediately when an operation is attempted while the circuit breaker is OPEN."""

    def __init__(self, message: str = "Circuit breaker is OPEN. Upstream service temporarily unavailable.", retry_after: int = 30):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class CircuitBreaker:
    """
    Production-grade circuit breaker for async and sync external calls.
    
    States & Transitions:
    - CLOSED: Successful executions keep the circuit closed. Consecutive failures >= failure_threshold switch state to OPEN.
    - OPEN: Calls immediately raise CircuitBreakerOpenError. Once recovery_timeout expires, state becomes HALF_OPEN.
    - HALF_OPEN: Next request is executed. If successful -> CLOSED. If it fails -> OPEN (reset timer).
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    def _check_state(self):
        """Check and update circuit breaker state based on time window."""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                retry_in = max(1, int(self.recovery_timeout - elapsed))
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Retry in {retry_in}s.",
                    retry_after=retry_in,
                )

    def _on_success(self):
        """Reset failure counts and close the circuit on successful execution."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Increment failure counts and open the circuit if threshold is reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def __call__(self, func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                self._check_state()
                try:
                    result = await func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception:
                    self._on_failure()
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                self._check_state()
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception:
                    self._on_failure()
                    raise
            return sync_wrapper


# Standard pre-configured circuit breakers for subsystems
redis_breaker = CircuitBreaker(name="redis", failure_threshold=3, recovery_timeout=20.0)
s3_breaker = CircuitBreaker(name="s3", failure_threshold=3, recovery_timeout=30.0)
webhook_breaker = CircuitBreaker(name="webhook", failure_threshold=5, recovery_timeout=45.0)
