"""Country domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CountryEntity:
    """Immutable representation of a country with regulatory metadata."""

    code: str
    name: str
    regulatory_complexity: str = "medium"
    avg_startup_weeks: int = 14
    patient_pool: int = 50_000
    therapeutic_area_match: str = ""
    db_id: Optional[int] = None
