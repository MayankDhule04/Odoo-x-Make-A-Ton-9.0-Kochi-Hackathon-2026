"""Simple in-memory rate limiter for login and password reset endpoints.

Uses a sliding-window counter per IP address. The window and limit are small enough
that the dict stays tiny. A restart clears all counters, which is fine for a hackathon.
"""

import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

# (window_seconds, max_requests_in_window)
_LOGIN_LIMIT = (60, 10)  # 10 login attempts per minute per IP
_RESET_LIMIT = (300, 5)  # 5 reset requests per 5 minutes per IP

_buckets: dict[str, list[float]] = defaultdict(list)


def _check(key: str, window: int, limit: int) -> None:
    now = time.monotonic()
    timestamps = _buckets[key]
    # Purge entries outside the window.
    _buckets[key] = [t for t in timestamps if now - t < window]
    if len(_buckets[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    _buckets[key].append(now)


def _login_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    _check(f"login:{ip}", *_LOGIN_LIMIT)


def _reset_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    _check(f"reset:{ip}", *_RESET_LIMIT)


LoginRateLimit = Annotated[None, Depends(_login_rate_limit)]
ResetRateLimit = Annotated[None, Depends(_reset_rate_limit)]
