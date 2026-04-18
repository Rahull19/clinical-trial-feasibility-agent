"""Thin route for trial ingestion — delegates to IngestTrialUseCase."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.exceptions import FileParsingError, UnsupportedFileTypeError
from app.core.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

router = APIRouter()


@router.post("/ingest-trial")
async def ingest_trial(
    file: UploadFile = File(...),
    llm_provider: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    """Ingest a historical trial document into the system."""
    set_correlation_id()
    filename = file.filename or "unknown"
    logger.info("POST /ingest-trial — file=%s, provider=%s", filename, llm_provider)

    from app.core.container import get_container

    container = get_container()

    # ── 1. Resolve LLM ───────────────────────────────────────────────────
    try:
        llm = container.resolve_llm(llm_provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ── 2. Read file ─────────────────────────────────────────────────────
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {exc}") from exc

    # ── 3. Delegate to use case ──────────────────────────────────────────
    try:
        use_case = container.ingest_trial_use_case()
        result = await use_case.execute(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=file.content_type,
            llm=llm,
        )
        return {"status": "success", "data": result}

    except ValueError as exc:
        logger.warning("Duplicate trial ingestion: %s", exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileParsingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc
