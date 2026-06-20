"""Statement Analysis API — 4 endpoints + health check."""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.statement import (
    AnalyzeRequest,
    AnalyzeResponse,
    CategorizeRequest,
    CategorizeResponse,
    FormatsResponse,
    ProcessingStatusResponse,
)
from app.services import redis_service

router = APIRouter()

# ── supported formats (static) ────────────────────────────────────────────────

_FORMATS = [
    {
        "format": "PDF",
        "extensions": [".pdf"],
        "max_size_mb": 10,
        "features": ["text_extraction", "table_detection", "multi_page"],
    },
    {
        "format": "CSV",
        "extensions": [".csv"],
        "max_size_mb": 5,
        "features": ["structured_data", "delimiter_detection", "encoding_auto_detect"],
    },
    {
        "format": "Excel",
        "extensions": [".xlsx", ".xls"],
        "max_size_mb": 5,
        "features": ["multiple_sheets", "formula_values"],
    },
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _run_processing(statement_data: Dict, processing_id: str) -> None:
    """Background thread target — catches all errors."""
    from app.services import statement_processor

    try:
        statement_processor.process_statement(statement_data, processing_id)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Background processing error: %s", exc)


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("/formats", response_model=FormatsResponse)
def get_supported_formats():
    """List all supported file formats (no auth required)."""
    from app.models.statement import FormatFeature
    return FormatsResponse(supported_formats=[FormatFeature(**f) for f in _FORMATS])


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=AnalyzeResponse)
def analyze_statement(
    request: AnalyzeRequest,
    user_id: int = Depends(get_current_user),
):
    """Trigger statement analysis. Returns immediately; processing runs async."""
    # Validate file type
    from app.services.s3_service import detect_file_type
    file_type = detect_file_type(request.file_url)
    if file_type == "unknown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_file_format",
                "message": "Unsupported file format. Supported: PDF, CSV, Excel",
                "statement_id": request.statement_id,
            },
        )

    processing_id = str(uuid.uuid4())
    started_at = datetime.now(tz=timezone.utc).isoformat()

    # Seed Redis status
    redis_service.set_status(
        request.statement_id,
        {
            "statement_id": request.statement_id,
            "processing_id": processing_id,
            "status": "processing",
            "progress_percentage": 0,
            "started_at": started_at,
            "completed_at": None,
            "processing_time_seconds": None,
            "results": None,
            "error": None,
        },
    )

    # Build data dict for processor
    statement_data = {
        "statement_id": request.statement_id,
        "file_url": request.file_url,
        "user_id": user_id,
        "bank_name": request.bank_name,
        "account_last_four": request.account_last_four,
    }

    # Kick off background thread
    thread = threading.Thread(
        target=_run_processing,
        args=(statement_data, processing_id),
        daemon=True,
    )
    thread.start()

    return AnalyzeResponse(
        processing_id=processing_id,
        statement_id=request.statement_id,
        status="processing",
        estimated_time_seconds=30,
        message="Statement analysis started",
    )


@router.get("/{statement_id}/status", response_model=ProcessingStatusResponse)
def get_processing_status(
    statement_id: str,
    user_id: int = Depends(get_current_user),
):
    """Retrieve current processing status from Redis cache."""
    cached = redis_service.get_status(statement_id)
    if cached:
        results_raw = cached.get("results")
        from app.models.statement import ProcessingResults
        results = ProcessingResults(**results_raw) if results_raw else None
        return ProcessingStatusResponse(
            statement_id=cached["statement_id"],
            processing_id=cached.get("processing_id", ""),
            status=cached["status"],
            progress_percentage=cached.get("progress_percentage", 0),
            started_at=cached.get("started_at"),
            completed_at=cached.get("completed_at"),
            processing_time_seconds=cached.get("processing_time_seconds"),
            results=results,
        )

    # Not in Redis — return queued placeholder
    return ProcessingStatusResponse(
        statement_id=statement_id,
        processing_id="",
        status="queued",
        progress_percentage=0,
        started_at=None,
        completed_at=None,
        processing_time_seconds=None,
        results=None,
    )


@router.post("/categorize", response_model=CategorizeResponse)
def categorize_transaction(
    request: CategorizeRequest,
    user_id: int = Depends(get_current_user),
):
    """Categorise a single transaction description."""
    from app.categorization import rule_categorizer, vector_categorizer
    from app.services import chroma_service

    desc = request.description.strip()
    chroma = chroma_service.get_client()

    # Try vector first
    cat_result = vector_categorizer.categorise(desc, chroma)

    # Fall back to rule-based
    if cat_result is None:
        cat_result = rule_categorizer.categorise(desc, request.amount or 0.0)

    similar = cat_result.pop("similar_transactions", [])

    return CategorizeResponse(
        category=cat_result["category"],
        subcategory=cat_result.get("subcategory"),
        confidence_score=cat_result.get("confidence_score", 0.5),
        alternative_categories=[],
        tags=cat_result.get("tags", []),
        similar_transactions=[
            {"description": s["description"], "category": cat_result["category"], "similarity_score": s["similarity_score"]}
            for s in similar[:3]
        ],
    )
