"""Risk value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def numeric(self) -> float:
        return {"low": 0.1, "medium": 0.4, "high": 0.7}[self.value]


@dataclass(frozen=True)
class RiskScore:
    """Risk score for a single entity (0.0 – 1.0, higher = riskier)."""

    entity_id: str
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", round(min(max(self.value, 0.0), 1.0), 4))

    @property
    def is_high(self) -> bool:
        return self.value > 0.7
