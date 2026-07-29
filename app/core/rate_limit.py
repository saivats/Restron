"""Minimal in-memory login rate limiter.

Not a distributed rate limiter — state lives in process memory, so it
resets on restart and does not share state across multiple worker
processes/instances. That's an acceptable tradeoff for a single-instance
Render deployment; if Restron ever runs multiple workers or instances
behind a load balancer, replace this with a shared store (e.g. Redis)
using the same interface.
"""

import random
import threading
import time
from typing import Dict, Tuple

from fastapi import HTTPException, status

_LOCK = threading.Lock()
_ATTEMPTS: Dict[str, Tuple[int, float]] = {}  # key -> (failed_count, window_start)
_PRUNE_PROBABILITY = 0.02  # ~1 in 50 calls sweeps expired entries

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_WINDOW_SECONDS = 15 * 60  # 15 minutes

# Backwards-compatible aliases (existing call sites/imports).
MAX_ATTEMPTS = DEFAULT_MAX_ATTEMPTS
WINDOW_SECONDS = DEFAULT_WINDOW_SECONDS


def _key(scope: str, identifier: str, client_ip: str | None) -> str:
    return f"{scope}:{identifier.strip().lower()}:{client_ip or 'unknown'}"


def enforce_rate_limit(
    scope: str,
    identifier: str,
    client_ip: str | None,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> None:
    """Raise 429 if this identifier/IP has too many recent failed attempts."""
    key = _key(scope, identifier, client_ip)
    now = time.monotonic()
    with _LOCK:
        count, window_start = _ATTEMPTS.get(key, (0, now))
        if now - window_start > window_seconds:
            count, window_start = 0, now
        if count >= max_attempts:
            retry_after = int(window_seconds - (now - window_start))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )


def record_failed_attempt(
    scope: str,
    identifier: str,
    client_ip: str | None,
    *,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> None:
    key = _key(scope, identifier, client_ip)
    now = time.monotonic()
    with _LOCK:
        count, window_start = _ATTEMPTS.get(key, (0, now))
        if now - window_start > window_seconds:
            count, window_start = 0, now
        _ATTEMPTS[key] = (count + 1, window_start)
        if random.random() < _PRUNE_PROBABILITY:
            _prune_expired(now, window_seconds)


def _prune_expired(now: float, window_seconds: int) -> None:
    """Caller must hold _LOCK. Drops entries whose window has fully expired."""
    expired = [k for k, (_, window_start) in _ATTEMPTS.items() if now - window_start > window_seconds]
    for k in expired:
        _ATTEMPTS.pop(k, None)


def reset_attempts(scope: str, identifier: str, client_ip: str | None) -> None:
    key = _key(scope, identifier, client_ip)
    with _LOCK:
        _ATTEMPTS.pop(key, None)
