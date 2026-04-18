"""Protocol parsing service — extracts structured criteria from raw protocol data."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.config import AppConfig
from app.core.exceptions import ProtocolParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_FIELDS: List[str] = [
    "protocol_id", "title", "phase", "therapeutic_area",
    "indication", "target_enrollment",
]


class ProtocolParser:
    """Parses and validates clinical trial protocol documents.

    Args:
        config: Application configuration.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    async def parse(
        self, protocol_data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Parse raw protocol data into structured criteria + missing flags.

        Returns:
            Tuple of (parsed_criteria dict, list of missing-data flag strings).

        Raises:
            ProtocolParsingError: When the payload is fundamentally unusable.
        """
        if not protocol_data:
            raise ProtocolParsingError("Protocol data is empty or None.")

        missing_flags: List[str] = []
        for field in _REQUIRED_FIELDS:
            if field not in protocol_data or protocol_data[field] is None:
                missing_flags.append(f"missing_protocol_field:{field}")

        parsed_criteria: Dict[str, Any] = {
            "protocol_id": protocol_data.get("protocol_id", "UNKNOWN"),
            "title": protocol_data.get("title", ""),
            "phase": protocol_data.get("phase", ""),
            "therapeutic_area": protocol_data.get("therapeutic_area", ""),
            "indication": protocol_data.get("indication", ""),
            "target_enrollment": protocol_data.get("target_enrollment", 0),
            "age_range": protocol_data.get("age_range", {"min": 18, "max": 65}),
            "gender": protocol_data.get("gender", "all"),
            "exclusion_criteria": protocol_data.get("exclusion_criteria", []),
            "inclusion_criteria": protocol_data.get("inclusion_criteria", []),
            "primary_endpoint": protocol_data.get("primary_endpoint", ""),
            "duration_weeks": protocol_data.get("duration_weeks", 52),
            "geographic_scope": protocol_data.get("geographic_scope", []),
        }

        logger.info(
            "Protocol parsed — id=%s, missing_flags=%d",
            parsed_criteria["protocol_id"], len(missing_flags),
        )
        return parsed_criteria, missing_flags
