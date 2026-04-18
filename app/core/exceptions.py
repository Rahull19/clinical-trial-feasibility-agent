"""Domain-specific exception hierarchy.

Every exception carries a ``details`` dict for structured error context.
Exceptions are organised by domain boundary so callers can catch at the
right granularity.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ClinicalTrialAgentError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.details: Dict[str, Any] = details or {}


# ── Protocol / Parsing ────────────────────────────────────────────────────────

class ProtocolParsingError(ClinicalTrialAgentError):
    """Raised when protocol data cannot be parsed or is malformed."""


class FileParsingError(ClinicalTrialAgentError):
    """Raised when an uploaded file cannot be parsed."""


class UnsupportedFileTypeError(ClinicalTrialAgentError):
    """Raised when an uploaded file type is not supported."""


# ── Enrichment ────────────────────────────────────────────────────────────────

class DataEnrichmentError(ClinicalTrialAgentError):
    """Raised when data enrichment fails or returns incomplete data."""


# ── Country ───────────────────────────────────────────────────────────────────

class CountryFeasibilityError(ClinicalTrialAgentError):
    """Raised when country feasibility evaluation encounters an error."""


class NoValidCountriesError(ClinicalTrialAgentError):
    """Raised when no countries pass the feasibility threshold."""


# ── Site ──────────────────────────────────────────────────────────────────────

class SiteSelectionError(ClinicalTrialAgentError):
    """Raised when site selection logic fails."""


class NoValidSitesError(ClinicalTrialAgentError):
    """Raised when no sites pass the selection criteria."""


# ── Investigator ──────────────────────────────────────────────────────────────

class InvestigatorMatchingError(ClinicalTrialAgentError):
    """Raised when investigator matching encounters an error."""


# ── Risk / Scoring ────────────────────────────────────────────────────────────

class RiskScoringError(ClinicalTrialAgentError):
    """Raised when risk scoring computation fails."""


class FeasibilityScoringError(ClinicalTrialAgentError):
    """Raised when overall feasibility scoring fails."""


# ── Compliance ────────────────────────────────────────────────────────────────

class ComplianceValidationError(ClinicalTrialAgentError):
    """Raised when compliance validation encounters an error."""


# ── Report ────────────────────────────────────────────────────────────────────

class ReportGenerationError(ClinicalTrialAgentError):
    """Raised when report generation encounters an error."""


# ── Human Review ──────────────────────────────────────────────────────────────

class HumanReviewError(ClinicalTrialAgentError):
    """Raised when human review interaction fails."""


# ── Infrastructure ────────────────────────────────────────────────────────────

class LLMProviderError(ClinicalTrialAgentError):
    """Raised when an LLM provider is unavailable or returns an error."""


class GraphExecutionError(ClinicalTrialAgentError):
    """Raised when the LangGraph execution pipeline encounters an error."""


class RepositoryError(ClinicalTrialAgentError):
    """Raised when a database repository operation fails."""


class RAGError(ClinicalTrialAgentError):
    """Raised when a RAG operation fails."""


class CacheError(ClinicalTrialAgentError):
    """Raised when a cache operation fails."""
