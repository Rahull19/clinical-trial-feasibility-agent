"""Trial domain entity — pure business object with no ORM dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class TrialEntity:
    """Immutable representation of a clinical trial."""

    protocol_id: str
    title: str
    phase: str = ""
    therapeutic_area: str = ""
    indication: str = ""
    target_enrollment: int = 0
    duration_weeks: int = 52
    age_range_min: int = 18
    age_range_max: int = 65
    gender: str = "all"
    geographic_scope: List[str] = field(default_factory=list)
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    primary_endpoint: str = ""
    raw_text: str = ""
    db_id: Optional[int] = None
