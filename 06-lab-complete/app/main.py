"""Production AI Agent using the Day 9 legal multi-agent flow.

This final project keeps the Day 12 production requirements around the API:
config from environment, API key auth, rate limiting, budget guard, health
checks, graceful shutdown, Docker readiness, and structured logs.

The domain logic is adapted from the Day 9 Multi-Agent MCP/A2A source:
Customer Agent -> Law Agent -> optional Tax/Compliance specialists -> aggregate.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_and_record_budget
from app.legal_agents import run_legal_multi_agent
from app.rate_limiter import check_rate_limit
from app.session_store import append_message, load_history, new_session_id, ready as storage_ready
from app.session_store import storage_name


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"agent-{os.getpid()}")
_is_ready = False
_request_count = 0
_error_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(
        json.dumps(
            {
                "event": "startup",
                "app": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "instance_id": INSTANCE_ID,
                "storage": storage_name(),
            }
        )
    )
    time.sleep(0.1)
    _is_ready = True
    logger.info(json.dumps({"event": "ready", "instance_id": INSTANCE_ID}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown", "instance_id": INSTANCE_ID}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    started = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.time() - started) * 1000, 1),
                    "instance_id": INSTANCE_ID,
                }
            )
        )
        return response
    except Exception:
        _error_count += 1
        raise


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="default-user", min_length=1, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)


class AskResponse(BaseModel):
    question: str
    answer: str
    user_id: str
    session_id: str
    trace_id: str
    context_id: str
    served_by: str
    storage: str
    history_count: int
    usage: dict
    specialists: dict
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "source": "Day 9 legal multi-agent flow adapted for Day 12 deployment",
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "history": "GET /sessions/{session_id}/history (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics (requires X-API-Key)",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Agent is not ready")

    rate_info = check_rate_limit(body.user_id)
    session_id = body.session_id or new_session_id()

    append_message(session_id, "user", body.question)
    result = run_legal_multi_agent(question=body.question, context_id=session_id)
    append_message(session_id, "assistant", result.final_answer)
    history = load_history(session_id)

    input_tokens = max(1, len(body.question.split()) * 2)
    output_tokens = max(1, len(result.final_answer.split()) * 2)
    budget_info = check_and_record_budget(body.user_id, input_tokens, output_tokens)

    logger.info(
        json.dumps(
            {
                "event": "multi_agent_answer",
                "user_id": body.user_id,
                "session_id": session_id,
                "trace_id": result.trace_id,
                "needs_tax": result.needs_tax,
                "needs_compliance": result.needs_compliance,
                "client": str(request.client.host) if request.client else "unknown",
            }
        )
    )

    return AskResponse(
        question=body.question,
        answer=result.final_answer,
        user_id=body.user_id,
        session_id=session_id,
        trace_id=result.trace_id,
        context_id=result.context_id,
        served_by=INSTANCE_ID,
        storage=storage_name(),
        history_count=len(history),
        usage={
            "rate_limit": rate_info,
            "budget": budget_info,
        },
        specialists={
            "customer": result.customer_summary,
            "law": True,
            "tax": result.needs_tax,
            "compliance": result.needs_compliance,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/sessions/{session_id}/history", tags=["Agent"])
def get_session_history(session_id: str, _api_key: str = Depends(verify_api_key)):
    return {
        "session_id": session_id,
        "storage": storage_name(),
        "messages": load_history(session_id),
    }


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {
            "storage": storage_name(),
            "multi_agent": "day9-legal-flow",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Application not ready")
    if not storage_ready():
        raise HTTPException(status_code=503, detail="Storage not ready")
    return {
        "ready": True,
        "instance_id": INSTANCE_ID,
        "storage": storage_name(),
    }


@app.get("/metrics", tags=["Operations"])
def metrics(_api_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "monthly_budget_usd": settings.monthly_budget_usd,
        "storage": storage_name(),
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum, "instance_id": INSTANCE_ID}))


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info("Starting %s on %s:%s", settings.app_name, settings.host, settings.port)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
