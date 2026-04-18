"""Report generator — produces the final feasibility recommendation report."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import AppConfig
from app.core.exceptions import ReportGenerationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates the final feasibility report / recommendation.

    Args:
        config: Application configuration.
    """

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    async def generate(
        self,
        parsed_criteria: Dict[str, Any],
        country_scores: Dict[str, float],
        site_scores: Dict[str, float],
        risk_scores: Dict[str, float],
        investigators: List[Dict[str, Any]],
        feasibility_score: float,
        compliance_flags: List[str],
        approval_status: Optional[str],
        human_feedback: Optional[str],
        sites: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a structured final recommendation report.

        Raises:
            ReportGenerationError: When report assembly fails.
        """
        if not parsed_criteria:
            raise ReportGenerationError("Cannot generate report without parsed criteria.")

        recommendation: Dict[str, Any] = {
            "protocol_id": parsed_criteria.get("protocol_id", "UNKNOWN"),
            "title": parsed_criteria.get("title", ""),
            "feasibility_score": feasibility_score,
            "recommendation": self._derive_recommendation(feasibility_score),
            "approval_status": approval_status,
            "human_feedback": human_feedback,
            "summary": {
                "total_countries": len(country_scores),
                "total_sites": len(site_scores),
                "total_investigators": len(investigators),
                "compliance_issues": len(compliance_flags),
            },
            "country_details": [
                {
                    "country_code": code,
                    "feasibility_score": score,
                    "risk_score": risk_scores.get(f"country:{code}", None),
                }
                for code, score in country_scores.items()
            ],
            "site_details": [
                {
                    "site_id": site.get("site_id"),
                    "name": site.get("name"),
                    "score": site_scores.get(site.get("site_id", ""), 0.0),
                    "risk_score": risk_scores.get(f"site:{site.get('site_id', '')}", None),
                }
                for site in sites
            ],
            "investigator_details": [
                {
                    "investigator_id": inv.get("investigator_id"),
                    "name": inv.get("name"),
                    "match_score": inv.get("match_score", 0.0),
                    "site_id": inv.get("site_id"),
                }
                for inv in investigators
            ],
            "compliance_flags": compliance_flags,
        }

        logger.info(
            "Report generated — protocol=%s, recommendation=%s",
            recommendation["protocol_id"], recommendation["recommendation"],
        )
        return recommendation

    @staticmethod
    def _derive_recommendation(score: float) -> str:
        if score >= 0.8:
            return "HIGHLY_FEASIBLE"
        if score >= 0.6:
            return "FEASIBLE"
        if score >= 0.4:
            return "CONDITIONALLY_FEASIBLE"
        return "NOT_FEASIBLE"
