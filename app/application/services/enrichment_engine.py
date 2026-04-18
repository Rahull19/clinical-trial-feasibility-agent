"""Enrichment engine — split from the old monolithic EnrichmentService.

Responsibilities:
  - DataFetcher: queries DB for country data
  - RAGAugmenter: finds similar trials via RAG
  - MetadataNormaliser: normalises country names to codes
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.config import AppConfig
from app.core.exceptions import DataEnrichmentError
from app.core.logging import get_logger
from app.domain.interfaces.cache import CachePort
from app.domain.interfaces.rag import RAGPort
from app.domain.interfaces.repositories import CountryRepositoryPort
from app.domain.models.country import CountryEntity
from app.infrastructure.db.session import DatabaseSession

logger = get_logger(__name__)

# Mapping of common country names/codes to standardised records.
_COUNTRY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "USA": {"code": "US", "name": "United States", "regulatory_complexity": "medium", "avg_startup_weeks": 12, "patient_pool": 120_000},
    "US": {"code": "US", "name": "United States", "regulatory_complexity": "medium", "avg_startup_weeks": 12, "patient_pool": 120_000},
    "United States": {"code": "US", "name": "United States", "regulatory_complexity": "medium", "avg_startup_weeks": 12, "patient_pool": 120_000},
    "Germany": {"code": "DE", "name": "Germany", "regulatory_complexity": "high", "avg_startup_weeks": 16, "patient_pool": 45_000},
    "DE": {"code": "DE", "name": "Germany", "regulatory_complexity": "high", "avg_startup_weeks": 16, "patient_pool": 45_000},
    "India": {"code": "IN", "name": "India", "regulatory_complexity": "medium", "avg_startup_weeks": 10, "patient_pool": 200_000},
    "IN": {"code": "IN", "name": "India", "regulatory_complexity": "medium", "avg_startup_weeks": 10, "patient_pool": 200_000},
    "Japan": {"code": "JP", "name": "Japan", "regulatory_complexity": "high", "avg_startup_weeks": 20, "patient_pool": 60_000},
    "JP": {"code": "JP", "name": "Japan", "regulatory_complexity": "high", "avg_startup_weeks": 20, "patient_pool": 60_000},
    "Brazil": {"code": "BR", "name": "Brazil", "regulatory_complexity": "high", "avg_startup_weeks": 18, "patient_pool": 80_000},
    "BR": {"code": "BR", "name": "Brazil", "regulatory_complexity": "high", "avg_startup_weeks": 18, "patient_pool": 80_000},
    "Australia": {"code": "AU", "name": "Australia", "regulatory_complexity": "medium", "avg_startup_weeks": 14, "patient_pool": 30_000},
    "AU": {"code": "AU", "name": "Australia", "regulatory_complexity": "medium", "avg_startup_weeks": 14, "patient_pool": 30_000},
    "UK": {"code": "UK", "name": "United Kingdom", "regulatory_complexity": "medium", "avg_startup_weeks": 14, "patient_pool": 50_000},
    "United Kingdom": {"code": "UK", "name": "United Kingdom", "regulatory_complexity": "medium", "avg_startup_weeks": 14, "patient_pool": 50_000},
    "China": {"code": "CN", "name": "China", "regulatory_complexity": "high", "avg_startup_weeks": 22, "patient_pool": 300_000},
    "CN": {"code": "CN", "name": "China", "regulatory_complexity": "high", "avg_startup_weeks": 22, "patient_pool": 300_000},
    "Canada": {"code": "CA", "name": "Canada", "regulatory_complexity": "medium", "avg_startup_weeks": 12, "patient_pool": 35_000},
    "CA": {"code": "CA", "name": "Canada", "regulatory_complexity": "medium", "avg_startup_weeks": 12, "patient_pool": 35_000},
    "France": {"code": "FR", "name": "France", "regulatory_complexity": "high", "avg_startup_weeks": 16, "patient_pool": 55_000},
    "FR": {"code": "FR", "name": "France", "regulatory_complexity": "high", "avg_startup_weeks": 16, "patient_pool": 55_000},
}


class MetadataNormaliser:
    """Normalises country names/codes to standard CountryEntity records."""

    def normalise_countries(self, geographic_scope: List[str]) -> List[CountryEntity]:
        seen: set = set()
        entities: List[CountryEntity] = []
        for name in geographic_scope:
            defaults = _COUNTRY_DEFAULTS.get(name)
            if defaults and defaults["code"] not in seen:
                entities.append(CountryEntity(**defaults))
                seen.add(defaults["code"])
            elif name not in seen:
                code = name[:2].upper()
                entities.append(CountryEntity(code=code, name=name))
                seen.add(code)
        return entities


class DataFetcher:
    """Fetches country data from PostgreSQL."""

    def __init__(self, db_session: DatabaseSession) -> None:
        self._db = db_session

    async def fetch_countries(
        self, codes: List[str],
    ) -> List[CountryEntity]:
        from app.infrastructure.db.repositories.country_repository import CountryRepository

        async with self._db.session() as session:
            repo = CountryRepository(session)
            if codes:
                return await repo.get_by_codes(codes)
            return await repo.list_all()


class RAGAugmenter:
    """Finds insights from similar historical trials via RAG."""

    def __init__(self, rag: RAGPort) -> None:
        self._rag = rag

    async def find_similar_trials(
        self, therapeutic_area: str, indication: str,
    ) -> List[Dict[str, Any]]:
        query = f"{therapeutic_area} {indication} trial feasibility"
        results = await self._rag.query(query, top_k=5, collection="trials")
        if results:
            logger.info(
                "RAG augmentation — found %d similar trials for '%s'",
                len(results), query[:60],
            )
        return results


class EnrichmentEngine:
    """Orchestrates enrichment using DataFetcher, RAGAugmenter, and MetadataNormaliser.

    Args:
        db_session: Database session manager.
        rag: Optional RAG backend.
        cache: Optional cache backend.
        config: Application configuration.
    """

    def __init__(
        self,
        db_session: DatabaseSession,
        rag: Optional[RAGPort] = None,
        cache: Optional[CachePort] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self._normaliser = MetadataNormaliser()
        self._fetcher = DataFetcher(db_session)
        self._augmenter = RAGAugmenter(rag) if rag else None
        self._cache = cache

    async def enrich(
        self, parsed_criteria: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Enrich parsed criteria with country data and RAG insights.

        Returns:
            Tuple of (enriched country list as dicts, remaining flags).

        Raises:
            DataEnrichmentError: When enrichment fails irrecoverably.
        """
        if not parsed_criteria:
            raise DataEnrichmentError("Cannot enrich from empty criteria.")

        therapeutic_area: str = parsed_criteria.get("therapeutic_area", "")
        indication: str = parsed_criteria.get("indication", "")
        geographic_scope: List[str] = parsed_criteria.get("geographic_scope", [])

        logger.info(
            "Enrichment input — therapeutic_area=%s, geographic_scope=%s",
            therapeutic_area, geographic_scope,
        )

        # Normalise country names to codes
        normalised = self._normaliser.normalise_countries(geographic_scope)
        codes = [c.code for c in normalised]

        # Try DB first
        countries = await self._try_db(codes, therapeutic_area)

        # Fallback to normalised defaults
        if not countries:
            countries = self._build_defaults(normalised, therapeutic_area)

        # RAG augmentation
        if self._augmenter and therapeutic_area:
            try:
                await self._augmenter.find_similar_trials(therapeutic_area, indication)
            except Exception as e:
                logger.warning("RAG augmentation failed: %s", e)

        remaining_flags: List[str] = []
        if not indication:
            remaining_flags.append("missing_enrichment_field:indication")

        logger.info(
            "Enrichment complete — countries=%d, remaining_flags=%d",
            len(countries), len(remaining_flags),
        )
        return countries, remaining_flags

    async def _try_db(
        self, codes: List[str], therapeutic_area: str,
    ) -> List[Dict[str, Any]]:
        try:
            db_countries = await self._fetcher.fetch_countries(codes)
            if db_countries:
                result = [
                    {
                        "country_code": c.code,
                        "name": c.name,
                        "patient_pool": c.patient_pool,
                        "regulatory_complexity": c.regulatory_complexity,
                        "avg_startup_weeks": c.avg_startup_weeks,
                        "therapeutic_area_match": therapeutic_area,
                    }
                    for c in db_countries
                ]
                logger.info("Enrichment from DB — found %d countries", len(result))
                return result
        except Exception as e:
            logger.warning("DB enrichment failed, falling back to defaults: %s", e)
        return []

    @staticmethod
    def _build_defaults(
        normalised: List[CountryEntity], therapeutic_area: str,
    ) -> List[Dict[str, Any]]:
        countries = [
            {
                "country_code": c.code,
                "name": c.name,
                "patient_pool": c.patient_pool,
                "regulatory_complexity": c.regulatory_complexity,
                "avg_startup_weeks": c.avg_startup_weeks,
                "therapeutic_area_match": therapeutic_area,
            }
            for c in normalised
        ]
        if not countries:
            countries.append({
                "country_code": "US",
                "name": "United States",
                "patient_pool": 120_000,
                "regulatory_complexity": "medium",
                "avg_startup_weeks": 12,
                "therapeutic_area_match": therapeutic_area,
            })
        logger.info("Enrichment from defaults — %d countries", len(countries))
        return countries
