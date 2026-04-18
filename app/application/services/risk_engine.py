"""Risk engine — computes risk scores for countries and sites.

All risk weights and regulatory mappings come from AppConfig.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import AppConfig
from app.core.exceptions import RiskScoringError
from app.core.logging import get_logger

logger = get_logger(__name__)

_REGULATORY_RISK: Dict[str, float] = {
    "low": 0.1,
    "medium": 0.4,
    "high": 0.7,
}


class RiskEngine:
    """Computes risk scores across countries and sites.

    Args:
        config: Application configuration with risk weights.
    """

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    async def compute(
        self,
        countries: List[Dict[str, Any]],
        sites: List[Dict[str, Any]],
        country_scores: Dict[str, float],
        site_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute per-entity risk scores (0.0–1.0, higher = riskier).

        Raises:
            RiskScoringError: When no entities are provided.
        """
        if not countries and not sites:
            raise RiskScoringError("No entities provided for risk scoring.")

        risk_scores: Dict[str, float] = {}

        for country in countries:
            code = country.get("country_code", "")
            if code not in country_scores:
                continue
            reg_risk = _REGULATORY_RISK.get(
                country.get("regulatory_complexity", "high"), 0.5
            )
            feasibility_inverse = 1.0 - country_scores.get(code, 0.5)
            risk = round(
                self._cfg.weight_risk_regulatory * reg_risk
                + self._cfg.weight_risk_feasibility * feasibility_inverse,
                4,
            )
            risk_scores[f"country:{code}"] = risk
            logger.info("Risk for country %s = %.4f", code, risk)

        for site in sites:
            sid = site.get("site_id", "")
            perf = site.get("past_performance", 0.5)
            site_risk = round(1.0 - perf, 4)
            risk_scores[f"site:{sid}"] = site_risk
            logger.info("Risk for site %s = %.4f", sid, site_risk)

        return risk_scores
