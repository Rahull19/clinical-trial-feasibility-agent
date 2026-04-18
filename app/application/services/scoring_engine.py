"""Scoring engines — country, site, and aggregate feasibility scoring.

All magic numbers are injected via AppConfig. No hardcoded thresholds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.config import AppConfig
from app.core.exceptions import (
    CountryFeasibilityError,
    FeasibilityScoringError,
    NoValidCountriesError,
    NoValidSitesError,
    SiteSelectionError,
)
from app.core.logging import get_logger
from app.domain.value_objects.risk import RiskLevel

logger = get_logger(__name__)

_REGULATORY_MAP: Dict[str, float] = {"low": 0.9, "medium": 0.6, "high": 0.3}


class CountryScorer:
    """Scores countries based on patient pool, regulatory, startup, and TA match."""

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    async def evaluate(
        self,
        countries: List[Dict[str, Any]],
        parsed_criteria: Dict[str, Any],
        threshold: float,
    ) -> Dict[str, float]:
        if not countries:
            raise CountryFeasibilityError("No countries provided for evaluation.")

        scores: Dict[str, float] = {}
        for country in countries:
            try:
                pool_norm = min(
                    country.get("patient_pool", 0) / self._cfg.max_patient_pool, 1.0
                )
                reg_score = _REGULATORY_MAP.get(
                    country.get("regulatory_complexity", "high"), 0.3
                )
                startup_norm = max(
                    1.0 - country.get("avg_startup_weeks", self._cfg.max_startup_weeks) / self._cfg.max_startup_weeks,
                    0.0,
                )
                ta_match = 1.0 if country.get("therapeutic_area_match") else 0.5

                composite = (
                    self._cfg.weight_patient_pool * pool_norm
                    + self._cfg.weight_regulatory * reg_score
                    + self._cfg.weight_startup * startup_norm
                    + self._cfg.weight_ta_match * ta_match
                )
                composite = round(composite, 4)

                code = country["country_code"]
                if composite >= threshold:
                    scores[code] = composite
                    logger.info("Country %s — score=%.4f (PASS)", code, composite)
                else:
                    logger.info("Country %s — score=%.4f (FILTERED)", code, composite)
            except KeyError as exc:
                logger.warning("Skipping country with missing key: %s", exc)

        if not scores:
            raise NoValidCountriesError(
                "All countries scored below the threshold.",
                details={"threshold": threshold},
            )
        return scores


class SiteScorer:
    """Scores sites based on performance, capacity, and enrollment fit."""

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    def score_site(self, site: Dict[str, Any], target_enrollment: int) -> float:
        capacity_norm = min(
            site.get("capacity", 100) / self._cfg.max_site_capacity, 1.0
        )
        perf = site.get("past_performance", 0.5)
        enrollment_fit = min(
            site.get("capacity", 100) / max(target_enrollment, 1), 1.0
        )
        return round(
            self._cfg.weight_site_performance * perf
            + self._cfg.weight_site_capacity * capacity_norm
            + self._cfg.weight_site_enrollment * enrollment_fit,
            4,
        )


class FeasibilityScorer:
    """Computes the aggregate feasibility score."""

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    async def compute(
        self,
        country_scores: Dict[str, float],
        site_scores: Dict[str, float],
        risk_scores: Dict[str, float],
        investigators: List[Dict[str, Any]],
        compliance_flags: List[str],
    ) -> float:
        if not country_scores and not site_scores:
            raise FeasibilityScoringError(
                "Cannot compute feasibility without country or site scores."
            )

        avg_country = _safe_mean(list(country_scores.values()))
        avg_site = _safe_mean(list(site_scores.values()))
        avg_risk = _safe_mean(list(risk_scores.values())) if risk_scores else 0.5
        risk_component = 1.0 - avg_risk

        inv_scores = [inv.get("match_score", 0.5) for inv in investigators]
        avg_inv = _safe_mean(inv_scores) if inv_scores else 0.5

        compliance_component = max(
            1.0 - self._cfg.compliance_penalty_per_flag * len(compliance_flags), 0.0
        )

        feasibility = (
            self._cfg.weight_country * avg_country
            + self._cfg.weight_site * avg_site
            + self._cfg.weight_risk * risk_component
            + self._cfg.weight_investigator * avg_inv
            + self._cfg.weight_compliance * compliance_component
        )
        feasibility = round(min(max(feasibility, 0.0), 1.0), 4)

        logger.info(
            "Feasibility score = %.4f  (country=%.3f, site=%.3f, risk_comp=%.3f, inv=%.3f, compl=%.3f)",
            feasibility, avg_country, avg_site, risk_component, avg_inv, compliance_component,
        )
        return feasibility


def _safe_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0
