"""Ingest Trial use case — top-level orchestrator for the /ingest-trial endpoint.

Coordinates: file parsing → metadata extraction → PostgreSQL storage → RAG indexing.
All dependencies are injected.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import AppConfig
from app.core.exceptions import FileParsingError
from app.core.logging import get_logger
from app.application.services.enrichment_engine import MetadataNormaliser
from app.domain.interfaces.llm import LLMPort
from app.domain.interfaces.rag import RAGPort
from app.domain.models.trial import TrialEntity
from app.infrastructure.db.session import DatabaseSession

logger = get_logger(__name__)


class IngestTrialUseCase:
    """Orchestrates historical trial data ingestion.

    Args:
        config: Application configuration.
        db_session: Database session manager.
        rag: RAG backend for vector indexing.
    """

    def __init__(
        self,
        config: AppConfig,
        db_session: DatabaseSession,
        rag: RAGPort,
    ) -> None:
        self._config = config
        self._db = db_session
        self._rag = rag
        self._normaliser = MetadataNormaliser()

    async def execute(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        llm: Optional[LLMPort] = None,
    ) -> Dict[str, Any]:
        """Run the ingestion pipeline.

        Args:
            file_bytes: Raw file content.
            filename: Original filename.
            mime_type: Optional MIME type hint.
            llm: Optional LLM provider for extraction.

        Returns:
            Summary dict with protocol_id, status, and counts.

        Raises:
            FileParsingError: If parsing fails.
            ValueError: If trial already exists.
        """
        logger.info("[IngestTrialUseCase] Starting — filename=%s", filename)

        # ── 1. Parse file (uses existing parsing infrastructure) ──────────
        from app.parsing.parser_factory import ParserFactory

        parser_factory = ParserFactory(llm=llm)
        protocol_data = parser_factory.parse_file(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
        )

        protocol_id = protocol_data.get("protocol_id", "UNKNOWN")
        raw_text = protocol_data.get("raw_text", "")

        if protocol_id == "UNKNOWN":
            raise FileParsingError(
                "Could not extract protocol_id from the document.",
                details={"filename": filename},
            )

        # ── 2. Store in PostgreSQL ────────────────────────────────────────
        db_result = await self._store_in_database(protocol_data, raw_text)

        # ── 3. Index in vector DB ─────────────────────────────────────────
        rag_count = await self._index_in_rag(protocol_data, raw_text)

        summary = {
            "protocol_id": protocol_id,
            "status": "ingested",
            "title": protocol_data.get("title", ""),
            "therapeutic_area": protocol_data.get("therapeutic_area", ""),
            "phase": protocol_data.get("phase", ""),
            "countries_stored": db_result.get("countries_count", 0),
            "sites_stored": db_result.get("sites_count", 0),
            "investigators_stored": db_result.get("investigators_count", 0),
            "rag_documents_indexed": rag_count,
        }

        logger.info(
            "[IngestTrialUseCase] Complete — protocol_id=%s, countries=%d, sites=%d, investigators=%d, rag=%d",
            protocol_id, summary["countries_stored"], summary["sites_stored"],
            summary["investigators_stored"], rag_count,
        )
        return summary

    async def _store_in_database(
        self,
        protocol_data: Dict[str, Any],
        raw_text: str,
    ) -> Dict[str, Any]:
        from app.infrastructure.db.repositories.trial_repository import TrialRepository
        from app.infrastructure.db.repositories.country_repository import CountryRepository
        from app.infrastructure.db.repositories.site_repository import SiteRepository
        from app.infrastructure.db.repositories.investigator_repository import InvestigatorRepository
        from app.domain.models.country import CountryEntity
        from app.domain.models.site import SiteEntity
        from app.domain.models.investigator import InvestigatorEntity

        async with self._db.session() as session:
            trial_repo = TrialRepository(session)
            country_repo = CountryRepository(session)
            site_repo = SiteRepository(session)
            inv_repo = InvestigatorRepository(session)

            protocol_id = protocol_data.get("protocol_id", "UNKNOWN")
            if await trial_repo.exists(protocol_id):
                raise ValueError(f"Trial {protocol_id} already exists in the database.")

            trial_entity = TrialEntity(
                protocol_id=protocol_id,
                title=protocol_data.get("title", ""),
                therapeutic_area=protocol_data.get("therapeutic_area", ""),
                phase=protocol_data.get("phase", ""),
                indication=protocol_data.get("indication", ""),
                target_enrollment=protocol_data.get("target_enrollment", 0),
                raw_text=raw_text,
            )
            trial = await trial_repo.create(trial_entity)

            # Countries
            normalised_countries = self._normaliser.normalise_countries(
                protocol_data.get("geographic_scope", [])
            )
            country_id_map: Dict[str, int] = {}
            for c_entity in normalised_countries:
                stored = await country_repo.get_or_create(c_entity)
                if stored.db_id:
                    country_id_map[c_entity.code] = stored.db_id

            # Sites
            sites_raw = protocol_data.get("sites", [])
            site_id_map: Dict[str, int] = {}
            for s_data in sites_raw:
                country_code = s_data.get("country_code", "")
                country_db_id = country_id_map.get(country_code)
                if not country_db_id:
                    continue
                s_entity = SiteEntity(
                    site_id=s_data.get("site_id", ""),
                    name=s_data.get("name", "Unknown Site"),
                    country_code=country_code,
                    capacity=s_data.get("capacity", 100),
                    past_performance=s_data.get("success_rate", 0.5),
                )
                stored_site = await site_repo.get_or_create(s_entity, country_db_id)
                if stored_site.db_id:
                    site_id_map[s_entity.site_id] = stored_site.db_id

            # Investigators
            investigators_raw = protocol_data.get("investigators", [])
            inv_count = 0
            for inv_data in investigators_raw:
                site_id_str = inv_data.get("site_id", "")
                site_db_id = site_id_map.get(site_id_str)
                if not site_db_id:
                    continue
                inv_entity = InvestigatorEntity(
                    investigator_id=inv_data.get("investigator_id", ""),
                    name=inv_data.get("name", "Unknown"),
                    site_id=site_id_str,
                    experience_years=inv_data.get("past_trials", 0),
                )
                await inv_repo.get_or_create(inv_entity, site_db_id)
                inv_count += 1

            return {
                "trial_id": trial.db_id,
                "countries_count": len(normalised_countries),
                "sites_count": len(sites_raw),
                "investigators_count": inv_count,
            }

    async def _index_in_rag(
        self,
        protocol_data: Dict[str, Any],
        raw_text: str,
    ) -> int:
        if not raw_text or not raw_text.strip():
            logger.warning("[IngestTrialUseCase] No text to index in RAG")
            return 0

        doc = {
            "id": protocol_data.get("protocol_id", "UNKNOWN"),
            "text": raw_text,
            "metadata": {
                "protocol_id": protocol_data.get("protocol_id", ""),
                "therapeutic_area": protocol_data.get("therapeutic_area", ""),
                "phase": protocol_data.get("phase", ""),
                "indication": protocol_data.get("indication", ""),
            },
        }
        return await self._rag.add_documents([doc], collection="trials")
