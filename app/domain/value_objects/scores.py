"""Score value objects — enforce 0.0–1.0 invariants at construction time."""

from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 4)


@dataclass(frozen=True)
class CountryScore:
    """Country feasibility score (0.0 – 1.0)."""

    country_code: str
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clamp(self.value))

    @property
    def passed(self) -> bool:
        return self.value > 0.0


@dataclass(frozen=True)
class SiteScore:
    """Site suitability score (0.0 – 1.0)."""

    site_id: str
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clamp(self.value))


@dataclass(frozen=True)
class FeasibilityScore:
    """Aggregate feasibility score with component breakdown."""

    value: float
    country_avg: float = 0.0
    site_avg: float = 0.0
    risk_component: float = 0.0
    investigator_avg: float = 0.0
    compliance_component: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clamp(self.value))

    @property
    def recommendation(self) -> str:
        if self.value >= 0.8:
            return "HIGHLY_FEASIBLE"
        if self.value >= 0.6:
            return "FEASIBLE"
        if self.value >= 0.4:
            return "CONDITIONALLY_FEASIBLE"
        return "NOT_FEASIBLE"
