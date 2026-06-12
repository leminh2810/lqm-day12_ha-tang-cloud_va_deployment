"""Redis-backed rate limiter with in-memory fallback."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings


try:
    import redis

    _redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    if _redis:
        _redis.ping()
except Exception:
    _redis = None


_windows: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(user_id: str) -> dict:
    limit = settings.rate_limit_per_minute
    window_seconds = 60
    now = time.time()

    if _redis:
        key = f"rate:{user_id}:{int(now // window_seconds)}"
        current = _redis.incr(key)
        if current == 1:
            _redis.expire(key, window_seconds + 5)
        remaining = max(0, limit - current)
        if current > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} requests/minute",
                headers={"Retry-After": "60"},
            )
        return {"limit": limit, "remaining": remaining}

    window = _windows[user_id]
    while window and window[0] < now - window_seconds:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests/minute",
            headers={"Retry-After": "60"},
        )
    window.append(now)
    return {"limit": limit, "remaining": limit - len(window)}
