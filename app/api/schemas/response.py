"""Response schemas — Pydantic models for API output serialization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class CountryDetail(BaseModel):
    country_code: str
    feasibility_score: float
    risk_score: Optional[float] = None


class SiteDetail(BaseModel):
    site_id: Optional[str] = None
    name: Optional[str] = None
    score: float = 0.0
    risk_score: Optional[float] = None


class InvestigatorDetail(BaseModel):
    investigator_id: Optional[str] = None
    name: Optional[str] = None
    match_score: float = 0.0
    site_id: Optional[str] = None


class RecommendationSummary(BaseModel):
    total_countries: int = 0
    total_sites: int = 0
    total_investigators: int = 0
    compliance_issues: int = 0


class Recommendation(BaseModel):
    protocol_id: str = "UNKNOWN"
    title: str = ""
    feasibility_score: float = 0.0
    recommendation: str = "NOT_FEASIBLE"
    approval_status: Optional[str] = None
    human_feedback: Optional[str] = None
    summary: Optional[RecommendationSummary] = None
    country_details: List[CountryDetail] = Field(default_factory=list)
    site_details: List[SiteDetail] = Field(default_factory=list)
    investigator_details: List[InvestigatorDetail] = Field(default_factory=list)
    compliance_flags: List[str] = Field(default_factory=list)
    warning: Optional[str] = None


class AnalyzeTrialResponse(BaseModel):
    status: str = "success"
    llm_provider: str = ""
    filename: str = ""
    recommendation: Recommendation = Field(default_factory=Recommendation)


class IngestionData(BaseModel):
    protocol_id: str
    status: str = "ingested"
    title: str = ""
    therapeutic_area: str = ""
    phase: str = ""
    countries_stored: int = 0
    sites_stored: int = 0
    investigators_stored: int = 0
    rag_documents_indexed: int = 0


class IngestTrialResponse(BaseModel):
    status: str = "success"
    data: IngestionData
