"""Async investigator repository — implements InvestigatorRepositoryPort."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.domain.interfaces.repositories import InvestigatorRepositoryPort
from app.domain.models.investigator import InvestigatorEntity
from app.infrastructure.db.models import InvestigatorORM, SiteORM, TrialInvestigatorORM

logger = get_logger(__name__)


class InvestigatorRepository(InvestigatorRepositoryPort):
    """SQLAlchemy-backed async investigator repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, entity: InvestigatorEntity, site_db_id: int) -> InvestigatorEntity:
        stmt = select(InvestigatorORM).where(
            InvestigatorORM.investigator_id == entity.investigator_id
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return self._to_entity(existing, entity.site_id)

        orm = InvestigatorORM(
            investigator_id=entity.investigator_id,
            name=entity.name,
            site_id=site_db_id,
            specialization=entity.specialization or None,
            past_trials=entity.experience_years,
            success_rate=0.0,
        )
        self._session.add(orm)
        await self._session.flush()
        logger.info("[InvestigatorRepo] Created — id=%s, name=%s", orm.investigator_id, orm.name)
        return InvestigatorEntity(
            investigator_id=orm.investigator_id,
            name=orm.name,
            site_id=entity.site_id,
            experience_years=orm.past_trials or 0,
            db_id=orm.id,
        )

    async def get_by_site_id(self, site_id: str) -> List[InvestigatorEntity]:
        stmt = (
            select(InvestigatorORM)
            .join(SiteORM)
            .where(SiteORM.site_id == site_id)
            .options(joinedload(InvestigatorORM.site))
        )
        result = await self._session.execute(stmt)
        return [
            self._to_entity(orm, site_id)
            for orm in result.scalars().unique().all()
        ]

    async def get_by_trial_id(self, trial_id: int) -> List[InvestigatorEntity]:
        stmt = (
            select(InvestigatorORM)
            .join(TrialInvestigatorORM, TrialInvestigatorORM.investigator_id == InvestigatorORM.id)
            .where(TrialInvestigatorORM.trial_id == trial_id)
            .options(joinedload(InvestigatorORM.site))
        )
        result = await self._session.execute(stmt)
        return [
            self._to_entity(orm, orm.site.site_id if orm.site else "")
            for orm in result.scalars().unique().all()
        ]

    @staticmethod
    def _to_entity(orm: InvestigatorORM, site_id: str) -> InvestigatorEntity:
        return InvestigatorEntity(
            investigator_id=orm.investigator_id,
            name=orm.name,
            site_id=site_id,
            experience_years=orm.past_trials or 0,
            specialization=orm.specialization or "",
            db_id=orm.id,
        )
