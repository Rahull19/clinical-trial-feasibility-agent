"""Investigator matcher — multi-tier investigator fetching and scoring.

Strategy:
  1. Query PostgreSQL for investigators at the target sites
  2. Use RAG to find investigators from similar historical trials
  3. Fall back to hardcoded pool
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import AppConfig
from app.core.exceptions import InvestigatorMatchingError
from app.core.logging import get_logger
from app.domain.interfaces.rag import RAGPort
from app.infrastructure.db.session import DatabaseSession

logger = get_logger(__name__)

_FALLBACK_INVESTIGATORS: Dict[str, List[Dict[str, Any]]] = {
    "US-001": [{"investigator_id": "INV-US-001", "name": "Dr. Sarah Chen", "experience_years": 15, "publications": 42, "site_id": "US-001"}],
    "US-002": [{"investigator_id": "INV-US-002", "name": "Dr. Michael Ross", "experience_years": 12, "publications": 28, "site_id": "US-002"}],
    "DE-001": [{"investigator_id": "INV-DE-001", "name": "Dr. Hans Mueller", "experience_years": 20, "publications": 55, "site_id": "DE-001"}],
    "IN-001": [{"investigator_id": "INV-IN-001", "name": "Dr. Priya Sharma", "experience_years": 10, "publications": 18, "site_id": "IN-001"}],
    "IN-002": [{"investigator_id": "INV-IN-002", "name": "Dr. Arjun Patel", "experience_years": 8, "publications": 12, "site_id": "IN-002"}],
    "BR-001": [{"investigator_id": "INV-BR-001", "name": "Dr. Ana Silva", "experience_years": 14, "publications": 30, "site_id": "BR-001"}],
    "JP-001": [{"investigator_id": "INV-JP-001", "name": "Dr. Kenji Tanaka", "experience_years": 16, "publications": 38, "site_id": "JP-001"}],
    "AU-001": [{"investigator_id": "INV-AU-001", "name": "Dr. James Wright", "experience_years": 18, "publications": 48, "site_id": "AU-001"}],
}


class InvestigatorFetcher:
    """Fetches investigators from DB and RAG with tiered fallback."""

    def __init__(
        self,
        db_session: DatabaseSession,
        rag: Optional[RAGPort] = None,
    ) -> None:
        self._db = db_session
        self._rag = rag

    async def fetch(
        self,
        site_id: str,
        therapeutic_area: str = "",
        indication: str = "",
    ) -> List[Dict[str, Any]]:
        investigators = await self._fetch_from_db(site_id)
        if investigators:
            return investigators

        if self._rag and therapeutic_area:
            investigators = await self._fetch_from_rag(site_id, therapeutic_area, indication)
            if investigators:
                return investigators

        return _FALLBACK_INVESTIGATORS.get(site_id, [])

    async def _fetch_from_db(self, site_id: str) -> List[Dict[str, Any]]:
        try:
            from app.infrastructure.db.repositories.investigator_repository import InvestigatorRepository

            async with self._db.session() as session:
                repo = InvestigatorRepository(session)
                db_investigators = await repo.get_by_site_id(site_id)
                if db_investigators:
                    result = [
                        {
                            "investigator_id": inv.investigator_id,
                            "name": inv.name,
                            "experience_years": inv.experience_years,
                            "publications": inv.publications,
                            "site_id": site_id,
                        }
                        for inv in db_investigators
                    ]
                    logger.info("Investigators from DB — %d for site %s", len(result), site_id)
                    return result
        except Exception as e:
            logger.warning("DB investigator query failed: %s", e)
        return []

    async def _fetch_from_rag(
        self,
        site_id: str,
        therapeutic_area: str,
        indication: str,
    ) -> List[Dict[str, Any]]:
        try:
            from app.infrastructure.db.repositories.trial_repository import TrialRepository
            from app.infrastructure.db.repositories.investigator_repository import InvestigatorRepository

            query = f"{therapeutic_area} {indication} principal investigator"
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
                inv_repo = InvestigatorRepository(session)
                investigators: List[Dict[str, Any]] = []
                for protocol_id in similar_protocol_ids:
                    trial = await trial_repo.get_by_protocol_id(protocol_id)
                    if trial and trial.db_id:
                        trial_invs = await inv_repo.get_by_trial_id(trial.db_id)
                        for inv in trial_invs:
                            investigators.append({
                                "investigator_id": inv.investigator_id,
                                "name": inv.name,
                                "experience_years": inv.experience_years,
                                "publications": inv.publications,
                                "site_id": site_id,
                                "source": "rag_similar_trial",
                            })
                if investigators:
                    logger.info("Investigators from RAG — %d for site %s", len(investigators), site_id)
                    return investigators
        except Exception as e:
            logger.warning("RAG investigator lookup failed: %s", e)
        return []


class InvestigatorScorer:
    """Computes relevance score for an investigator (0.0–1.0)."""

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

    def score(self, investigator: Dict[str, Any]) -> float:
        exp_norm = min(
            investigator.get("experience_years", 0) / self._cfg.max_investigator_experience_years, 1.0
        )
        pub_norm = min(
            investigator.get("publications", 0) / self._cfg.max_investigator_publications, 1.0
        )
        return round(
            self._cfg.weight_inv_experience * exp_norm
            + self._cfg.weight_inv_publications * pub_norm,
            4,
        )


class InvestigatorMatcher:
    """Matches principal investigators to selected sites.

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
        self._fetcher = InvestigatorFetcher(db_session, rag)
        self._scorer = InvestigatorScorer(self._cfg)

    async def match(
        self,
        sites: List[Dict[str, Any]],
        parsed_criteria: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Match investigators to the selected sites.

        Raises:
            InvestigatorMatchingError: When no sites are provided.
        """
        if not sites:
            raise InvestigatorMatchingError("No sites provided for investigator matching.")

        therapeutic_area = parsed_criteria.get("therapeutic_area", "")
        indication = parsed_criteria.get("indication", "")
        matched: List[Dict[str, Any]] = []

        for site in sites:
            site_id: str = site.get("site_id", "")
            candidates = await self._fetcher.fetch(
                site_id=site_id,
                therapeutic_area=therapeutic_area,
                indication=indication,
            )
            if not candidates:
                logger.warning("No investigators found for site %s", site_id)
                continue

            for inv in candidates:
                inv_record = {
                    **inv,
                    "match_score": self._scorer.score(inv),
                }
                matched.append(inv_record)
                logger.info(
                    "Investigator %s matched to site %s — score=%.2f",
                    inv["investigator_id"], site_id, inv_record["match_score"],
                )

        if not matched:
            logger.warning("No investigators matched for any selected site.")

        return matched
