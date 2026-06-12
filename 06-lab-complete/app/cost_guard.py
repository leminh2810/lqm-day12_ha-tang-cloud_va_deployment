"""Monthly budget guard for LLM-style usage."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException

from app.config import settings


PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006

try:
    import redis

    _redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    if _redis:
        _redis.ping()
except Exception:
    _redis = None


_memory_spend: dict[str, float] = defaultdict(float)


def _month_key() -> str:
    return time.strftime("%Y-%m")


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS
        + output_tokens / 1000 * PRICE_PER_1K_OUTPUT_TOKENS
    )


def check_and_record_budget(user_id: str, input_tokens: int, output_tokens: int) -> dict:
    cost = estimate_cost(input_tokens, output_tokens)
    budget = settings.monthly_budget_usd

    if _redis:
        key = f"budget:{user_id}:{_month_key()}"
        current = float(_redis.get(key) or 0.0)
        if current + cost > budget:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "used_usd": round(current, 6),
                    "budget_usd": budget,
                },
            )
        total = float(_redis.incrbyfloat(key, cost))
        _redis.expire(key, 32 * 24 * 3600)
    else:
        key = f"{user_id}:{_month_key()}"
        current = _memory_spend[key]
        if current + cost > budget:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "used_usd": round(current, 6),
                    "budget_usd": budget,
                },
            )
        _memory_spend[key] += cost
        total = _memory_spend[key]

    return {
        "cost_usd": round(cost, 6),
        "spent_usd": round(total, 6),
        "budget_usd": budget,
        "remaining_usd": round(max(0.0, budget - total), 6),
    }
