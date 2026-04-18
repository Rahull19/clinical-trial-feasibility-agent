"""Analyze Trial use case — top-level orchestrator for the /analyze-trial endpoint.

This use case builds the LangGraph pipeline, invokes it, and returns
the final recommendation. All dependencies are injected.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import AppConfig
from app.core.exceptions import GraphExecutionError
from app.core.logging import get_logger
from app.domain.interfaces.llm import LLMPort
from app.domain.interfaces.rag import RAGPort
from app.infrastructure.db.session import DatabaseSession

logger = get_logger(__name__)


class AnalyzeTrialUseCase:
    """Orchestrates trial analysis: parse file → build graph → invoke → return.

    Args:
        config: Application configuration.
        db_session: Database session manager.
        rag: RAG backend for similarity search.
    """

    def __init__(
        self,
        config: AppConfig,
        db_session: DatabaseSession,
        rag: Optional[RAGPort] = None,
    ) -> None:
        self._config = config
        self._db = db_session
        self._rag = rag

    async def execute(
        self,
        protocol_data: Dict[str, Any],
        llm: Optional[LLMPort] = None,
    ) -> Dict[str, Any]:
        """Run the full analysis pipeline.

        Args:
            protocol_data: Parsed protocol dict (from file upload).
            llm: Optional LLM provider for the pipeline.

        Returns:
            Final recommendation dict.

        Raises:
            GraphExecutionError: When the pipeline fails.
        """
        from app.graph.builder import build_graph

        try:
            compiled_graph = build_graph(
                config=self._config,
                db_session=self._db,
                llm=llm,
                rag=self._rag,
                reviewer_mode="api",
            )

            initial_state: Dict[str, Any] = {"protocol_data": protocol_data}
            final_state = compiled_graph.invoke(initial_state)

            recommendation = final_state.get("final_recommendation")
            if not recommendation:
                recommendation = {
                    "warning": "Pipeline completed but no final recommendation was produced.",
                    "feasibility_score": final_state.get("feasibility_score", 0.0),
                    "country_scores": final_state.get("country_scores", {}),
                    "site_scores": final_state.get("site_scores", {}),
                    "compliance_flags": final_state.get("compliance_flags", []),
                    "missing_data_flags": final_state.get("missing_data_flags", []),
                }

            return recommendation

        except Exception as exc:
            logger.error("Graph execution failed: %s", exc, exc_info=True)
            raise GraphExecutionError(
                f"Pipeline error: {exc}",
                details={"protocol_id": protocol_data.get("protocol_id", "UNKNOWN")},
            ) from exc
