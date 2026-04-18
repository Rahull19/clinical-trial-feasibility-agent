"""Dependency Injection container — single source of truth for all wiring.

NO direct instantiation of services anywhere else in the codebase.
All dependencies are resolved through this container.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.core.config import AppConfig, get_config
from app.core.logging import get_logger
from app.domain.interfaces.cache import CachePort
from app.domain.interfaces.llm import LLMPort
from app.domain.interfaces.rag import RAGPort
from app.infrastructure.cache.memory_cache import MemoryCache
from app.infrastructure.db.session import DatabaseSession
from app.infrastructure.rag.chroma_adapter import ChromaRAGAdapter
from app.infrastructure.rag.embedding_service import EmbeddingService

logger = get_logger(__name__)


class Container:
    """Application-wide DI container.

    Holds singletons for config, DB session, RAG, cache, and provides
    factory methods for use cases and LLM providers.
    """

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or get_config()

        # ── Singletons (lazy) ─────────────────────────────────────────────
        self._db_session: Optional[DatabaseSession] = None
        self._rag: Optional[RAGPort] = None
        self._cache: Optional[CachePort] = None
        self._embedding_service: Optional[EmbeddingService] = None

    # ── Config ────────────────────────────────────────────────────────────

    @property
    def config(self) -> AppConfig:
        return self._config

    # ── Database ──────────────────────────────────────────────────────────

    @property
    def db_session(self) -> DatabaseSession:
        if self._db_session is None:
            self._db_session = DatabaseSession(self._config)
        return self._db_session

    # ── Embedding Service ─────────────────────────────────────────────────

    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService(self._config)
        return self._embedding_service

    # ── RAG ───────────────────────────────────────────────────────────────

    @property
    def rag(self) -> RAGPort:
        if self._rag is None:
            self._rag = ChromaRAGAdapter(
                persist_directory=self._config.chroma_persist_directory,
                embedding_service=self.embedding_service,
            )
        return self._rag

    # ── Cache ─────────────────────────────────────────────────────────────

    @property
    def cache(self) -> CachePort:
        if self._cache is None:
            self._cache = MemoryCache(
                default_ttl=self._config.cache_ttl_seconds,
                max_size=self._config.cache_max_size,
            )
        return self._cache

    # ── LLM Provider Resolution ───────────────────────────────────────────

    def resolve_llm(self, provider: Optional[str] = None) -> LLMPort:
        """Resolve an LLM provider instance by name.

        Uses adapter wrappers around the existing sync LLM providers to
        conform to the async LLMPort interface.

        Raises:
            ValueError: If the provider name is not recognised.
        """
        from app.infrastructure.llm.adapter import LLMAdapter

        name = (provider or self._config.default_llm_provider).lower().strip()

        _REGISTRY = {
            "openai": lambda: self._build_llm("openai"),
            "groq": lambda: self._build_llm("groq"),
            "gemini": lambda: self._build_llm("gemini"),
            "xai": lambda: self._build_llm("xai"),
        }

        factory = _REGISTRY.get(name)
        if factory is None:
            raise ValueError(
                f"Unknown LLM provider: {name!r}. Available: {list(_REGISTRY.keys())}"
            )

        llm = factory()
        logger.info("Resolved LLM provider: %s (available=%s)", llm.provider_name, llm.is_available())
        return llm

    def _build_llm(self, name: str) -> LLMPort:
        from app.infrastructure.llm.adapter import LLMAdapter

        if name == "openai":
            from app.llm.openai_provider import OpenAIProvider
            return LLMAdapter(OpenAIProvider(api_key=self._config.openai_api_key))
        elif name == "groq":
            from app.llm.groq_provider import GroqProvider
            return LLMAdapter(GroqProvider(api_key=self._config.groq_api_key))
        elif name == "gemini":
            from app.llm.gemini_provider import GeminiProvider
            return LLMAdapter(GeminiProvider(api_key=self._config.gemini_api_key))
        elif name == "xai":
            from app.llm.xai_provider import XAIProvider
            return LLMAdapter(XAIProvider(api_key=self._config.xai_api_key))
        raise ValueError(f"Unknown LLM: {name}")

    # ── Use Case Factories ────────────────────────────────────────────────

    def analyze_trial_use_case(self):
        from app.application.use_cases.analyze_trial import AnalyzeTrialUseCase

        return AnalyzeTrialUseCase(
            config=self._config,
            db_session=self.db_session,
            rag=self.rag,
        )

    def ingest_trial_use_case(self):
        from app.application.use_cases.ingest_trial import IngestTrialUseCase

        return IngestTrialUseCase(
            config=self._config,
            db_session=self.db_session,
            rag=self.rag,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def init_db(self) -> None:
        """Create database tables (sync, used at startup)."""
        self.db_session.init_tables()

    async def shutdown(self) -> None:
        """Graceful shutdown — dispose connection pools."""
        if self._db_session:
            await self._db_session.dispose()
        logger.info("Container shutdown complete.")


# ── Module-level singleton ────────────────────────────────────────────────────
_container: Optional[Container] = None


def get_container() -> Container:
    """Return the application-wide container singleton."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def set_container(container: Container) -> None:
    """Override the container (useful for testing)."""
    global _container
    _container = container
