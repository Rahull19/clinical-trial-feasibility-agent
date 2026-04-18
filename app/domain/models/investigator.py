"""Investigator domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InvestigatorEntity:
    """Immutable representation of a principal investigator."""

    investigator_id: str
    name: str
    site_id: str
    experience_years: int = 0
    publications: int = 0
    specialization: str = ""
    source: str = "db"
    db_id: Optional[int] = None
