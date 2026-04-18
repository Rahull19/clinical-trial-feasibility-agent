"""Site domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SiteEntity:
    """Immutable representation of a clinical trial site."""

    site_id: str
    name: str
    country_code: str
    capacity: int = 100
    past_performance: float = 0.5
    source: str = "db"
    db_id: Optional[int] = None
