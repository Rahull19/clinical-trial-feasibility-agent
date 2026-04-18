"""FastAPI entry point (v2) — Clean Architecture with DI container.

Run with:
    uvicorn app.main:app --reload
    python -m app.main
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI

from app.api.routes.trial import router as trial_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.schemas.response import HealthResponse
from app.core.container import get_container
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager — startup/shutdown via DI container."""
    container = get_container()
    setup_logging(container.config.log_level)

    # ── Startup ───────────────────────────────────────────────────────────
    try:
        container.init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as exc:
        logger.warning("DB init skipped (DB may not be available): %s", exc)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    await container.shutdown()
    logger.info("Application shutting down.")


# ── FastAPI Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="Clinical Trial Feasibility & Site Selection Agent",
    description="Production-grade LangGraph-powered backend — Clean Architecture.",
    version="4.0.0",
    lifespan=lifespan,
)

app.include_router(trial_router, tags=["Trial Analysis"])
app.include_router(ingestion_router, tags=["Data Ingestion"])


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="4.0.0")


# ── CLI Runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    container = get_container()
    logger.info(
        "Starting FastAPI server on %s:%d",
        container.config.host,
        container.config.port,
    )
    uvicorn.run(
        "app.main:app",
        host=container.config.host,
        port=container.config.port,
        reload=True,
    )
