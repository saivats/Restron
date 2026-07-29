"""Minimal in-memory login rate limiter.

Not a distributed rate limiter — state lives in process memory, so it
resets on restart and does not share state across multiple worker
processes/instances. That's an acceptable tradeoff for a single-instance
Render deployment; if Restron ever runs multiple workers or instances
behind a load balancer, replace this with a shared store (e.g. Redis)
using the same interface.
"""

import threading
import time
from typing import Dict, Tuple

from fastapi import HTTPException, status

_LOCK = threading.Lock()
_ATTEMPTS: Dict[str, Tuple[int, float]] = {}  # key -> (failed_count, window_start)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60  # 15 minutes


def _key(scope: str, identifier: str, client_ip: str | None) -> str:
    return f"{scope}:{identifier.strip().lower()}:{client_ip or 'unknown'}"


def enforce_rate_limit(scope: str, identifier: str, client_ip: str | None) -> None:
    """Raise 429 if this identifier/IP has too many recent failed attempts."""
    key = _key(scope, identifier, client_ip)
    now = time.monotonic()
    with _LOCK:
        count, window_start = _ATTEMPTS.get(key, (0, now))
        if now - window_start > WINDOW_SECONDS:
            count, window_start = 0, now
        if count >= MAX_ATTEMPTS:
            retry_after = int(WINDOW_SECONDS - (now - window_start))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )


def record_failed_attempt(scope: str, identifier: str, client_ip: str | None) -> None:
    key = _key(scope, identifier, client_ip)
    now = time.monotonic()
    with _LOCK:
        count, window_start = _ATTEMPTS.get(key, (0, now))
        if now - window_start > WINDOW_SECONDS:
            count, window_start = 0, now
        _ATTEMPTS[key] = (count + 1, window_start)


def reset_attempts(scope: str, identifier: str, client_ip: str | None) -> None:
    key = _key(scope, identifier, client_ip)
    with _LOCK:
        _ATTEMPTS.pop(key, None)
