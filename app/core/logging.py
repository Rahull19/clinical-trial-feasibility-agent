"""Structured logging with correlation-ID support.

Every log record carries ``correlation_id`` so that a single API request
can be traced end-to-end across services, DB calls, and RAG queries.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

# ── Correlation ID ────────────────────────────────────────────────────────────
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set (or generate) the correlation ID for the current async context."""
    value = cid or uuid.uuid4().hex[:12]
    _correlation_id.set(value)
    return value


def get_correlation_id() -> str:
    """Return the current correlation ID (empty string if unset)."""
    return _correlation_id.get()


# ── Custom Formatter ──────────────────────────────────────────────────────────

class CorrelationFormatter(logging.Formatter):
    """Injects ``correlation_id`` into every log record."""

    def format(self, record: logging.LogRecord) -> str:
        record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
        return super().format(record)


# ── Logger Factory ────────────────────────────────────────────────────────────

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger once (idempotent)."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CorrelationFormatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a named logger (auto-configures on first call)."""
    setup_logging()
    return logging.getLogger(name or "clinical_trial_agent")
