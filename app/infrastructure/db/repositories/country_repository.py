"""Async country repository — implements CountryRepositoryPort."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.interfaces.repositories import CountryRepositoryPort
from app.domain.models.country import CountryEntity
from app.infrastructure.db.models import CountryORM

logger = get_logger(__name__)


class CountryRepository(CountryRepositoryPort):
    """SQLAlchemy-backed async country repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, entity: CountryEntity) -> CountryEntity:
        existing = await self.get_by_code(entity.code)
        if existing:
            return existing

        orm = CountryORM(
            code=entity.code,
            name=entity.name,
            regulatory_complexity=entity.regulatory_complexity,
            avg_startup_weeks=entity.avg_startup_weeks,
            patient_pool=entity.patient_pool,
        )
        self._session.add(orm)
        await self._session.flush()
        logger.info("[CountryRepo] Created — code=%s, name=%s", orm.code, orm.name)
        return self._to_entity(orm)

    async def get_by_code(self, code: str) -> Optional[CountryEntity]:
        stmt = select(CountryORM).where(CountryORM.code == code)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def get_by_codes(self, codes: List[str]) -> List[CountryEntity]:
        stmt = select(CountryORM).where(CountryORM.code.in_(codes))
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def list_all(self) -> List[CountryEntity]:
        stmt = select(CountryORM)
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    @staticmethod
    def _to_entity(orm: CountryORM) -> CountryEntity:
        return CountryEntity(
            code=orm.code,
            name=orm.name,
            regulatory_complexity=orm.regulatory_complexity or "medium",
            avg_startup_weeks=orm.avg_startup_weeks or 14,
            patient_pool=orm.patient_pool or 50_000,
            db_id=orm.id,
        )
