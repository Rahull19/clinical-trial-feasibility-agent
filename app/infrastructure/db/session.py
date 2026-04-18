"""Async database session management.

Provides an async SQLAlchemy engine, session factory, and context manager.
Also retains a sync engine for table creation on startup.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import AppConfig
from app.core.logging import get_logger
from app.infrastructure.db.models import Base

logger = get_logger(__name__)


class DatabaseSession:
    """Manages async and sync SQLAlchemy engines and session factories.

    Args:
        config: Application configuration with database URLs and pool settings.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

        # Async engine (for all runtime queries)
        self._async_engine = create_async_engine(
            config.database_url,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Sync engine (only for DDL / table creation on startup)
        self._sync_engine = create_engine(
            config.database_url_sync,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
        self._sync_session_factory = sessionmaker(
            bind=self._sync_engine,
            expire_on_commit=False,
        )

        logger.info(
            "[DB] Engines created — async=%s, sync=%s",
            config.database_url.split("@")[-1],
            config.database_url_sync.split("@")[-1],
        )

    def init_tables(self) -> None:
        """Create all tables synchronously (used at startup)."""
        Base.metadata.create_all(bind=self._sync_engine)
        logger.info("[DB] Tables created / verified")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional async database session.

        Automatically commits on success, rolls back on exception,
        and closes the session in all cases.
        """
        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        """Close all connection pools (for graceful shutdown)."""
        await self._async_engine.dispose()
        self._sync_engine.dispose()
        logger.info("[DB] Connection pools disposed")
