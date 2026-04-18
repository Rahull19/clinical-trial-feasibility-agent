"""ChromaDB adapter — async implementation of RAGPort.

Wraps the synchronous ChromaDB client with ``asyncio.to_thread`` so that
all vector-store operations are non-blocking.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.logging import get_logger
from app.domain.interfaces.rag import RAGPort
from app.infrastructure.rag.embedding_service import EmbeddingService

logger = get_logger(__name__)


class ChromaRAGAdapter(RAGPort):
    """Async ChromaDB-backed RAG for clinical trial document retrieval.

    Args:
        persist_directory: Path for ChromaDB persistent storage.
        embedding_service: Embedding service for vectorisation.
    """

    def __init__(
        self,
        persist_directory: str,
        embedding_service: EmbeddingService,
    ) -> None:
        self._persist_directory = persist_directory
        self._embedding_service = embedding_service
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("[ChromaRAG] Initialised — dir=%s", persist_directory)

    def _get_collection(self, collection: str) -> chromadb.Collection:
        return self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "default",
    ) -> int:
        if not documents:
            return 0

        col = self._get_collection(collection)
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        embeddings: List[List[float]] = []

        for doc in documents:
            text = doc.get("text", "")
            if not text.strip():
                continue

            doc_id = doc.get("id", str(uuid.uuid4()))
            metadata = doc.get("metadata", {})
            clean_meta = {
                k: v for k, v in metadata.items()
                if isinstance(v, (str, int, float, bool))
            }

            embedding = await self._embedding_service.embed_text(text)

            ids.append(doc_id)
            texts.append(text)
            metadatas.append(clean_meta)
            embeddings.append(embedding)

        if not ids:
            return 0

        await asyncio.to_thread(
            col.upsert,
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        logger.info("[ChromaRAG] add_documents — count=%d, collection=%s", len(ids), collection)
        return len(ids)

    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        collection: str = "default",
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        col = self._get_collection(collection)

        count = col.count()
        if count == 0:
            logger.info("[ChromaRAG] query — collection=%s is empty", collection)
            return []

        query_embedding = await self._embedding_service.embed_text(query_text)

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, count),
        }
        if where:
            query_kwargs["where"] = where

        results = await asyncio.to_thread(col.query, **query_kwargs)

        output: List[Dict[str, Any]] = []
        if results and results.get("documents"):
            documents = results["documents"][0]
            distances = results.get("distances", [[]])[0]
            metadatas_list = results.get("metadatas", [[]])[0]

            for i, doc_text in enumerate(documents):
                score = 1.0 - distances[i] if i < len(distances) else 0.0
                meta = metadatas_list[i] if i < len(metadatas_list) else {}
                output.append({
                    "text": doc_text,
                    "score": round(score, 4),
                    "metadata": meta,
                })

        logger.info(
            "[ChromaRAG] query — results=%d, collection=%s, query=%s",
            len(output), collection, query_text[:60],
        )
        return output

    async def delete_collection(self, collection: str) -> bool:
        try:
            await asyncio.to_thread(self._client.delete_collection, collection)
            logger.info("[ChromaRAG] Deleted collection — %s", collection)
            return True
        except Exception as e:
            logger.warning("[ChromaRAG] delete_collection failed — %s", e)
            return False
