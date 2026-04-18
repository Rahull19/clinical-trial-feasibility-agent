"""Site selector — multi-tier site fetching and scoring.

Strategy:
  1. Query PostgreSQL for sites in target countries
  2. Use RAG to find sites from similar historical trials
  3. Fall back to hardcoded catalogue
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.config import AppConfig
from app.core.exceptions import NoValidSitesError, SiteSelectionError
from app.core.logging import get_logger
from app.application.services.scoring_engine import SiteScorer
from app.domain.interfaces.rag import RAGPort
from app.infrastructure.db.session import DatabaseSession

logger = get_logger(__name__)

_FALLBACK_SITES: Dict[str, List[Dict[str, Any]]] = {
    "US": [
        {"site_id": "US-001", "name": "Mayo Clinic", "capacity": 150, "past_performance": 0.92, "country_code": "US"},
        {"site_id": "US-002", "name": "Johns Hopkins", "capacity": 120, "past_performance": 0.88, "country_code": "US"},
    ],
    "DE": [
        {"site_id": "DE-001", "name": "Charité Berlin", "capacity": 80, "past_performance": 0.85, "country_code": "DE"},
    ],
    "IN": [
        {"site_id": "IN-001", "name": "AIIMS Delhi", "capacity": 200, "past_performance": 0.80, "country_code": "IN"},
        {"site_id": "IN-002", "name": "CMC Vellore", "capacity": 100, "past_performance": 0.78, "country_code": "IN"},
    ],
    "BR": [
        {"site_id": "BR-001", "name": "Hospital Sírio-Libanês", "capacity": 90, "past_performance": 0.75, "country_code": "BR"},
    ],
    "JP": [
        {"site_id": "JP-001", "name": "University of Tokyo Hospital", "capacity": 100, "past_performance": 0.87, "country_code": "JP"},
    ],
    "AU": [
        {"site_id": "AU-001", "name": "Royal Melbourne Hospital", "capacity": 60, "past_performance": 0.90, "country_code": "AU"},
    ],
}


class SiteFetcher:
    """Fetches sites from DB and RAG with tiered fallback."""

    def __init__(
        self,
        db_session: DatabaseSession,
        rag: Optional[RAGPort] = None,
    ) -> None:
        self._db = db_session
        self._rag = rag

    async def fetch(
        self,
        country_codes: List[str],
        therapeutic_area: str = "",
        indication: str = "",
    ) -> List[Dict[str, Any]]:
        sites = await self._fetch_from_db(country_codes)
        if sites:
            return sites

        if self._rag and therapeutic_area:
            sites = await self._fetch_from_rag(country_codes, therapeutic_area, indication)
            if sites:
                return sites

        return self._fetch_from_fallback(country_codes)

    async def _fetch_from_db(self, country_codes: List[str]) -> List[Dict[str, Any]]:
        try:
            from app.infrastructure.db.repositories.site_repository import SiteRepository

            async with self._db.session() as session:
                repo = SiteRepository(session)
                db_sites = await repo.get_by_country_codes(country_codes)
                if db_sites:
                    sites = [
                        {
                            "site_id": s.site_id,
                            "name": s.name,
                            "capacity": s.capacity,
                            "past_performance": s.past_performance,
                            "country_code": s.country_code,
                        }
                        for s in db_sites
                    ]
                    logger.info("Sites from DB — %d sites for %s", len(sites), country_codes)
                    return sites
        except Exception as e:
            logger.warning("DB site query failed: %s", e)
        return []

    async def _fetch_from_rag(
        self,
        country_codes: List[str],
        therapeutic_area: str,
        indication: str,
    ) -> List[Dict[str, Any]]:
        try:
            from app.infrastructure.db.repositories.trial_repository import TrialRepository
            from app.infrastructure.db.repositories.site_repository import SiteRepository

            query = f"{therapeutic_area} {indication} clinical trial sites"
            results = await self._rag.query(query, top_k=5, collection="trials")
            if not results:
                return []

            similar_protocol_ids = [
                r.get("metadata", {}).get("protocol_id")
                for r in results
                if r.get("metadata", {}).get("protocol_id")
            ]
            if not similar_protocol_ids:
                return []

            async with self._db.session() as session:
                trial_repo = TrialRepository(session)
                site_repo = SiteRepository(session)
                sites: List[Dict[str, Any]] = []
                for protocol_id in similar_protocol_ids:
                    trial = await trial_repo.get_by_protocol_id(protocol_id)
                    if trial and trial.db_id:
                        trial_sites = await site_repo.get_by_trial_id(trial.db_id)
                        for s in trial_sites:
                            if s.country_code in country_codes:
                                sites.append({
                                    "site_id": s.site_id,
                                    "name": s.name,
                                    "capacity": s.capacity,
                                    "past_performance": s.past_performance,
                                    "country_code": s.country_code,
                                    "source": "rag_similar_trial",
                                })
                if sites:
                    logger.info("Sites from RAG (similar trials) — %d sites for %s", len(sites), country_codes)
                    return sites
        except Exception as e:
            logger.warning("RAG site lookup failed: %s", e)
        return []

    @staticmethod
    def _fetch_from_fallback(country_codes: List[str]) -> List[Dict[str, Any]]:
        sites: List[Dict[str, Any]] = []
        for code in country_codes:
            sites.extend(_FALLBACK_SITES.get(code, []))
        logger.info("Sites from fallback — %d sites for %s", len(sites), country_codes)
        return sites


class SiteSelector:
    """Selects and scores candidate clinical sites.

    Args:
        db_session: Database session manager.
        rag: Optional RAG backend.
        config: Application configuration.
    """

    def __init__(
        self,
        db_session: DatabaseSession,
        rag: Optional[RAGPort] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self._cfg = config or AppConfig()
        self._fetcher = SiteFetcher(db_session, rag)
        self._scorer = SiteScorer(self._cfg)

    async def select(
        self,
        country_scores: Dict[str, float],
        parsed_criteria: Dict[str, Any],
        threshold: float,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """Select and score sites for countries that passed feasibility.

        Raises:
            SiteSelectionError: On processing errors.
            NoValidSitesError: When no sites pass the threshold.
        """
        if not country_scores:
            raise SiteSelectionError("No qualifying countries — cannot select sites.")

        all_sites = await self._fetcher.fetch(
            country_codes=list(country_scores.keys()),
            therapeutic_area=parsed_criteria.get("therapeutic_area", ""),
            indication=parsed_criteria.get("indication", ""),
        )

        target_enrollment: int = parsed_criteria.get("target_enrollment", 100)
        selected_sites: List[Dict[str, Any]] = []
        site_scores: Dict[str, float] = {}

        for site in all_sites:
            code = site.get("country_code", "")
            if code not in country_scores:
                continue

            score = self._scorer.score_site(site, target_enrollment)
            if score >= threshold:
                selected_sites.append(site)
                site_scores[site["site_id"]] = score
                logger.info("Site %s (%s) — score=%.4f (PASS)", site["site_id"], site["name"], score)
            else:
                logger.info("Site %s (%s) — score=%.4f (FILTERED)", site["site_id"], site["name"], score)

        if not selected_sites:
            raise NoValidSitesError(
                "No sites passed the selection threshold.",
                details={"threshold": threshold},
            )

        return selected_sites, site_scores
