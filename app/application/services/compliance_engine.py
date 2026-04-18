"""Compliance engine — validates regulatory compliance across countries and sites."""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import AppConfig
from app.core.exceptions import ComplianceValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

_COMPLIANCE_RULES: Dict[str, List[str]] = {
    "US": ["FDA_IND_required", "IRB_approval_required"],
    "DE": ["EMA_CTA_required", "ethics_committee_approval", "GDPR_data_protection"],
    "IN": ["CDSCO_approval_required", "ethics_committee_approval"],
    "BR": ["ANVISA_approval_required", "CEP_CONEP_approval"],
    "AU": ["TGA_CTN_required", "HREC_approval_required"],
}


class ComplianceEngine:
    """Validates regulatory compliance for qualifying countries and sites.

    Args:
        config: Application configuration.
    """

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    async def validate(
        self,
        countries: List[Dict[str, Any]],
        country_scores: Dict[str, float],
        sites: List[Dict[str, Any]],
        parsed_criteria: Dict[str, Any],
    ) -> List[str]:
        """Return list of compliance flag strings. Empty = fully compliant.

        Raises:
            ComplianceValidationError: When validation logic encounters an error.
        """
        if not countries:
            raise ComplianceValidationError("No countries provided for compliance check.")

        flags: List[str] = []

        for country in countries:
            code = country.get("country_code", "")
            if code not in country_scores:
                continue

            rules = _COMPLIANCE_RULES.get(code, [])
            for rule in rules:
                if (
                    country.get("regulatory_complexity") == "high"
                    and parsed_criteria.get("duration_weeks", 52) < 24
                ):
                    flag = f"compliance:{code}:{rule}:short_duration_risk"
                    flags.append(flag)
                    logger.warning("Compliance flag — %s", flag)

        for site in sites:
            if site.get("past_performance", 1.0) < 0.7:
                flag = f"compliance:site:{site.get('site_id', '')}:low_past_performance"
                flags.append(flag)
                logger.warning("Compliance flag — %s", flag)

        logger.info("Compliance validation complete — flags=%d", len(flags))
        return flags
