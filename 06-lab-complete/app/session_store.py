"""Conversation history storage with Redis fallback."""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict

from app.config import settings


try:
    import redis

    _redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    if _redis:
        _redis.ping()
except Exception:
    _redis = None


_memory_sessions: dict[str, list[dict]] = defaultdict(list)


def storage_name() -> str:
    return "redis" if _redis else "in-memory"


def new_session_id() -> str:
    return str(uuid.uuid4())


def load_history(session_id: str) -> list[dict]:
    if _redis:
        raw_items = _redis.lrange(f"history:{session_id}", 0, -1)
        return [json.loads(item) for item in raw_items]
    return list(_memory_sessions.get(session_id, []))


def append_message(session_id: str, role: str, content: str) -> list[dict]:
    message = {
        "role": role,
        "content": content,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if _redis:
        key = f"history:{session_id}"
        _redis.rpush(key, json.dumps(message))
        _redis.ltrim(key, -settings.max_history_messages, -1)
        _redis.expire(key, settings.session_ttl_seconds)
        return load_history(session_id)

    history = _memory_sessions[session_id]
    history.append(message)
    if len(history) > settings.max_history_messages:
        del history[:-settings.max_history_messages]
    return list(history)


def ready() -> bool:
    if not _redis:
        return True
    try:
        return bool(_redis.ping())
    except Exception:
        return False
