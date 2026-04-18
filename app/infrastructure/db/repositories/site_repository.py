"""Async site repository — implements SiteRepositoryPort."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.domain.interfaces.repositories import SiteRepositoryPort
from app.domain.models.site import SiteEntity
from app.infrastructure.db.models import CountryORM, SiteORM, TrialSiteORM

logger = get_logger(__name__)


class SiteRepository(SiteRepositoryPort):
    """SQLAlchemy-backed async site repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, entity: SiteEntity, country_db_id: int) -> SiteEntity:
        stmt = select(SiteORM).where(SiteORM.site_id == entity.site_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return self._to_entity(existing)

        orm = SiteORM(
            site_id=entity.site_id,
            name=entity.name,
            country_id=country_db_id,
            capacity=entity.capacity,
            success_rate=entity.past_performance,
        )
        self._session.add(orm)
        await self._session.flush()
        logger.info("[SiteRepo] Created — site_id=%s, name=%s", orm.site_id, orm.name)
        return SiteEntity(
            site_id=orm.site_id,
            name=orm.name,
            country_code=entity.country_code,
            capacity=orm.capacity or 100,
            past_performance=orm.success_rate or 0.5,
            db_id=orm.id,
        )

    async def get_by_country_codes(self, codes: List[str]) -> List[SiteEntity]:
        stmt = (
            select(SiteORM)
            .join(CountryORM)
            .where(CountryORM.code.in_(codes))
            .options(joinedload(SiteORM.country))
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().unique().all()]

    async def get_by_trial_id(self, trial_id: int) -> List[SiteEntity]:
        stmt = (
            select(SiteORM)
            .join(TrialSiteORM, TrialSiteORM.site_id == SiteORM.id)
            .where(TrialSiteORM.trial_id == trial_id)
            .options(joinedload(SiteORM.country))
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().unique().all()]

    @staticmethod
    def _to_entity(orm: SiteORM) -> SiteEntity:
        return SiteEntity(
            site_id=orm.site_id,
            name=orm.name,
            country_code=orm.country.code if orm.country else "",
            capacity=orm.capacity or 100,
            past_performance=orm.success_rate or 0.5,
            db_id=orm.id,
        )
