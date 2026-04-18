"""Embedding service for generating vector representations of text.

Supports multiple providers (OpenAI, sentence-transformers) with a
unified interface. Runs synchronous embedding calls in a thread-pool
so callers can ``await`` without blocking the event loop.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from app.core.config import AppConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Generates text embeddings using configurable providers.

    Args:
        config: Application config for provider/model selection.
    """

    def __init__(self, config: AppConfig) -> None:
        self._provider = config.embedding_provider
        self._model = config.embedding_model
        self._api_key = config.openai_api_key
        self._dimension = config.embedding_dimension
        self._max_chars = config.max_document_chars
        self._client = None
        self._local_model = None

        logger.info(
            "[EmbeddingService] Init — provider=%s, model=%s",
            self._provider,
            self._model,
        )

    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single text string (async-safe)."""
        if not text or not text.strip():
            return [0.0] * self._dimension
        return await asyncio.to_thread(self._embed_sync, text)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed_text(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed_sync(self, text: str) -> List[float]:
        """Synchronous embedding dispatch (runs in thread-pool)."""
        if self._provider == "openai":
            return self._embed_openai(text)
        elif self._provider in ("sentence-transformers", "sentence_transformers", "local"):
            return self._embed_local(text)
        else:
            logger.warning("[EmbeddingService] Unknown provider=%s, using zeros", self._provider)
            return [0.0] * self._dimension

    def _embed_openai(self, text: str) -> List[float]:
        try:
            if self._client is None:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)

            response = self._client.embeddings.create(
                input=text[:self._max_chars],
                model=self._model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("[EmbeddingService] OpenAI embedding failed: %s", e)
            return [0.0] * self._dimension

    def _embed_local(self, text: str) -> List[float]:
        try:
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self._model)
                self._dimension = self._local_model.get_sentence_embedding_dimension()

            embedding = self._local_model.encode(text[:self._max_chars], convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error("[EmbeddingService] Local embedding failed: %s", e)
            return [0.0] * self._dimension
