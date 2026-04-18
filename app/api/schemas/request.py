"""Request schemas — Pydantic models for API input validation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeTrialRequest(BaseModel):
    """Query parameters for the /analyze-trial endpoint.

    File upload is handled by FastAPI's UploadFile; this model covers
    the additional form fields.
    """
    llm_provider: Optional[str] = Field(
        default=None,
        description="LLM provider name: openai, groq, gemini, xai.",
    )


class IngestTrialRequest(BaseModel):
    """Query parameters for the /ingest-trial endpoint."""
    llm_provider: Optional[str] = Field(
        default=None,
        description="LLM provider name for extraction.",
    )
