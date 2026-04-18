"""RAG port interface — contract for vector-store backends.

The domain and application layers programme against this interface.
Concrete implementations (Chroma, Milvus) live in infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class RAGPort(ABC):
    """Abstract RAG interface for document retrieval."""

    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "default",
    ) -> int:
        """Ingest documents into the vector store.

        Args:
            documents: List of dicts with at least a ``text`` key.
            collection: Target collection / index name.

        Returns:
            Number of documents successfully ingested.
        """

    @abstractmethod
    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        collection: str = "default",
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve the most relevant documents for a query.

        Args:
            query_text: The natural-language query.
            top_k: Maximum number of results.
            collection: Collection / index to search.
            where: Optional metadata filter.

        Returns:
            List of result dicts with ``text``, ``score``, and ``metadata``.
        """

    @abstractmethod
    async def delete_collection(self, collection: str) -> bool:
        """Delete an entire collection."""
