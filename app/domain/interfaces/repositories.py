"""Repository port interfaces — contracts that infrastructure must implement.

These are pure abstract classes with NO framework imports. The domain layer
never knows about SQLAlchemy, PostgreSQL, or any other persistence technology.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.models.country import CountryEntity
from app.domain.models.investigator import InvestigatorEntity
from app.domain.models.site import SiteEntity
from app.domain.models.trial import TrialEntity


class TrialRepositoryPort(ABC):
    """Abstract contract for trial persistence."""

    @abstractmethod
    async def create(self, entity: TrialEntity) -> TrialEntity:
        """Persist a new trial and return the entity with its DB id."""

    @abstractmethod
    async def get_by_protocol_id(self, protocol_id: str) -> Optional[TrialEntity]:
        """Fetch a trial by its protocol_id."""

    @abstractmethod
    async def exists(self, protocol_id: str) -> bool:
        """Return True if a trial with this protocol_id exists."""

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[TrialEntity]:
        """Paginated listing of all trials."""

    @abstractmethod
    async def search_by_therapeutic_area(self, area: str) -> List[TrialEntity]:
        """Find trials matching a therapeutic area."""


class CountryRepositoryPort(ABC):
    """Abstract contract for country persistence."""

    @abstractmethod
    async def get_or_create(self, entity: CountryEntity) -> CountryEntity:
        """Return existing country or create a new one."""

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[CountryEntity]:
        """Fetch a country by its ISO code."""

    @abstractmethod
    async def get_by_codes(self, codes: List[str]) -> List[CountryEntity]:
        """Fetch multiple countries by their codes."""

    @abstractmethod
    async def list_all(self) -> List[CountryEntity]:
        """Return all countries."""


class SiteRepositoryPort(ABC):
    """Abstract contract for site persistence."""

    @abstractmethod
    async def get_or_create(self, entity: SiteEntity, country_db_id: int) -> SiteEntity:
        """Return existing site or create a new one."""

    @abstractmethod
    async def get_by_country_codes(self, codes: List[str]) -> List[SiteEntity]:
        """Fetch sites in the given countries."""

    @abstractmethod
    async def get_by_trial_id(self, trial_id: int) -> List[SiteEntity]:
        """Fetch sites associated with a trial."""


class InvestigatorRepositoryPort(ABC):
    """Abstract contract for investigator persistence."""

    @abstractmethod
    async def get_or_create(self, entity: InvestigatorEntity, site_db_id: int) -> InvestigatorEntity:
        """Return existing investigator or create a new one."""

    @abstractmethod
    async def get_by_site_id(self, site_id: str) -> List[InvestigatorEntity]:
        """Fetch investigators at a given site (by string site_id)."""

    @abstractmethod
    async def get_by_trial_id(self, trial_id: int) -> List[InvestigatorEntity]:
        """Fetch investigators associated with a trial."""
