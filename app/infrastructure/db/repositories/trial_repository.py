"""Async trial repository — implements TrialRepositoryPort."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.interfaces.repositories import TrialRepositoryPort
from app.domain.models.trial import TrialEntity
from app.infrastructure.db.models import TrialORM

logger = get_logger(__name__)


class TrialRepository(TrialRepositoryPort):
    """SQLAlchemy-backed async trial repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entity: TrialEntity) -> TrialEntity:
        orm = TrialORM(
            protocol_id=entity.protocol_id,
            title=entity.title,
            therapeutic_area=entity.therapeutic_area or None,
            phase=entity.phase or None,
            indication=entity.indication or None,
            target_enrollment=entity.target_enrollment or None,
            raw_text=entity.raw_text or None,
        )
        self._session.add(orm)
        await self._session.flush()
        logger.info("[TrialRepo] Created — protocol_id=%s, id=%d", orm.protocol_id, orm.id)
        return self._to_entity(orm)

    async def get_by_protocol_id(self, protocol_id: str) -> Optional[TrialEntity]:
        stmt = select(TrialORM).where(TrialORM.protocol_id == protocol_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def exists(self, protocol_id: str) -> bool:
        stmt = select(TrialORM.id).where(TrialORM.protocol_id == protocol_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[TrialEntity]:
        stmt = select(TrialORM).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def search_by_therapeutic_area(self, area: str) -> List[TrialEntity]:
        stmt = select(TrialORM).where(TrialORM.therapeutic_area.ilike(f"%{area}%"))
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    @staticmethod
    def _to_entity(orm: TrialORM) -> TrialEntity:
        return TrialEntity(
            protocol_id=orm.protocol_id,
            title=orm.title,
            phase=orm.phase or "",
            therapeutic_area=orm.therapeutic_area or "",
            indication=orm.indication or "",
            target_enrollment=orm.target_enrollment or 0,
            raw_text=orm.raw_text or "",
            db_id=orm.id,
        )
