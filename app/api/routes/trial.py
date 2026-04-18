"""Thin route for clinical trial analysis — delegates to AnalyzeTrialUseCase."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.exceptions import (
    ClinicalTrialAgentError,
    FileParsingError,
    GraphExecutionError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

router = APIRouter()


@router.post("/analyze-trial")
async def analyze_trial(
    file: UploadFile = File(...),
    llm_provider: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    """Analyze a clinical trial protocol and return feasibility recommendation."""
    set_correlation_id()
    filename = file.filename or "unknown"
    logger.info("POST /analyze-trial — file=%s, provider=%s", filename, llm_provider)

    # Lazy import from container to avoid circular deps at module level
    from app.core.container import get_container

    container = get_container()

    # ── 1. Resolve LLM ───────────────────────────────────────────────────
    try:
        llm = container.resolve_llm(llm_provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ── 2. Parse file ────────────────────────────────────────────────────
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise FileParsingError("Uploaded file is empty.", details={"filename": filename})

        from app.parsing import ParserFactory

        parser_factory = ParserFactory(llm=llm)
        protocol_data = parser_factory.parse_file(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=file.content_type,
        )
        logger.info("Parsed file — filename=%s, protocol_id=%s", filename, protocol_data.get("protocol_id", "UNKNOWN"))

    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileParsingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # ── 3. Delegate to use case ──────────────────────────────────────────
    try:
        use_case = container.analyze_trial_use_case()
        recommendation = await use_case.execute(protocol_data=protocol_data, llm=llm)
    except GraphExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc

    return {
        "status": "success",
        "llm_provider": llm.provider_name if llm else "none",
        "filename": filename,
        "recommendation": recommendation,
    }
