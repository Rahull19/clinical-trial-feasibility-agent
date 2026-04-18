"""Centralized application configuration.

All magic numbers, thresholds, retry limits, and external service settings
are defined here. Values are loaded from environment variables (prefixed
with ``CTA_``) or a ``.env`` file via Pydantic BaseSettings.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Single source of truth for every tuneable parameter."""

    # ── LLM Provider API Keys ────────────────────────────────────────────
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None

    # ── Default LLM Provider ─────────────────────────────────────────────
    default_llm_provider: str = "openai"

    # ── Scoring Thresholds ───────────────────────────────────────────────
    country_score_threshold: float = 0.5
    site_score_threshold: float = 0.4
    risk_score_threshold: float = 0.7
    feasibility_score_threshold: float = 0.6

    # ── Scoring Weights (must sum to 1.0 per group) ──────────────────────
    weight_country: float = 0.25
    weight_site: float = 0.25
    weight_risk: float = 0.20
    weight_investigator: float = 0.15
    weight_compliance: float = 0.15

    # ── Country Scoring Weights ──────────────────────────────────────────
    weight_patient_pool: float = 0.35
    weight_regulatory: float = 0.25
    weight_startup: float = 0.20
    weight_ta_match: float = 0.20

    # ── Site Scoring Weights ─────────────────────────────────────────────
    weight_site_performance: float = 0.40
    weight_site_capacity: float = 0.35
    weight_site_enrollment: float = 0.25

    # ── Investigator Scoring Weights ─────────────────────────────────────
    weight_inv_experience: float = 0.60
    weight_inv_publications: float = 0.40

    # ── Normalisation Caps ───────────────────────────────────────────────
    max_patient_pool: int = 250_000
    max_startup_weeks: int = 24
    max_site_capacity: int = 250
    max_investigator_experience_years: int = 25
    max_investigator_publications: int = 60
    compliance_penalty_per_flag: float = 0.15

    # ── Retry Limits ─────────────────────────────────────────────────────
    max_enrichment_retries: int = 2
    max_compliance_retries: int = 1
    max_site_reselection_retries: int = 1

    # ── Risk Weights ─────────────────────────────────────────────────────
    weight_risk_regulatory: float = 0.50
    weight_risk_feasibility: float = 0.50

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Human-in-the-Loop ────────────────────────────────────────────────
    hitl_enabled: bool = True

    # ── PostgreSQL ───────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/clinical_trials"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/clinical_trials"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # ── RAG / Vector DB ──────────────────────────────────────────────────
    rag_provider: str = "chroma"
    chroma_persist_directory: str = "./chroma_data"
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # ── Embedding ────────────────────────────────────────────────────────
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ── Cache ────────────────────────────────────────────────────────────
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1000

    # ── Server ───────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Document Parsing ─────────────────────────────────────────────────
    max_document_chars: int = 8000

    model_config = {
        "env_prefix": "CTA_",
        "env_file": ".env",
        "extra": "ignore",
    }


def get_config() -> AppConfig:
    """Factory that returns a singleton-ish config (cacheable)."""
    return AppConfig()
