"""Lightweight graph state — replaces the monolithic TrialState.

Broken into logical groups. LangGraph merges partial dicts returned by
each node, so every field still lives on a single flat Pydantic model,
but the grouping is documented via comments for readability.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrialState(BaseModel):
    """Minimal state container for the clinical-trial evaluation pipeline.

    LangGraph passes a copy into each node. Nodes return a *partial* dict
    of only the fields they update.
    """

    # ── Input ─────────────────────────────────────────────────────────────
    protocol_data: Dict[str, Any] = Field(default_factory=dict)

    # ── Parsed ────────────────────────────────────────────────────────────
    parsed_criteria: Dict[str, Any] = Field(default_factory=dict)

    # ── Entities ──────────────────────────────────────────────────────────
    countries: List[Dict[str, Any]] = Field(default_factory=list)
    sites: List[Dict[str, Any]] = Field(default_factory=list)
    investigators: List[Dict[str, Any]] = Field(default_factory=list)

    # ── Scores ────────────────────────────────────────────────────────────
    country_scores: Dict[str, float] = Field(default_factory=dict)
    site_scores: Dict[str, float] = Field(default_factory=dict)
    risk_scores: Dict[str, float] = Field(default_factory=dict)
    feasibility_score: float = 0.0

    # ── Flags ─────────────────────────────────────────────────────────────
    compliance_flags: List[str] = Field(default_factory=list)
    missing_data_flags: List[str] = Field(default_factory=list)

    # ── Human Review ──────────────────────────────────────────────────────
    human_feedback: Optional[str] = None
    approval_status: Optional[str] = None

    # ── Output ────────────────────────────────────────────────────────────
    final_recommendation: Optional[Dict[str, Any]] = None

    # ── Retry Counters ────────────────────────────────────────────────────
    enrichment_retry_count: int = 0
    compliance_retry_count: int = 0
    site_reselection_retry_count: int = 0
