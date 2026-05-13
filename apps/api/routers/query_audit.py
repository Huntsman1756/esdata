"""Query audit log router for Fase 30.2 — Persistencia durable."""

from fastapi import APIRouter, Query
from schemas import QueryAuditByRequestResponse, QueryAuditEntryResponse, QueryAuditLogResponse
from services.query_audit import get_query_audit_service

router = APIRouter(prefix="/v1/ai", tags=["query_audit"])


@router.get(
    "/query-audit",
    response_model=QueryAuditLogResponse,
    summary="Query audit log",
    description="Retrieve query audit log entries with optional path filter.",
)
async def get_query_audit_log(
    path: str | None = Query(None, description="Filter by API path (e.g. /v1/consulta)"),
    limit: int = Query(100, ge=1, le=100, description="Maximum entries returned"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Query query audit log with optional path filter."""
    store = get_query_audit_service()
    total = store.count_entries(path=path)
    entries = store.get_entries(path=path, limit=limit, offset=offset)

    return {
        "total": total,
        "path": path,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(entries) < total,
        "entries": [
            QueryAuditEntryResponse(
                entry_id=e.entry_id,
                request_id=e.request_id,
                user_id=e.user_id,
                path=e.path,
                query_text=e.query_text,
                retrieved_chunks=e.retrieved_chunks,
                sources=e.sources,
                response_summary=e.response_summary,
                confidence=e.confidence,
                completeness=e.completeness,
                verified=e.verified,
                model_version=e.model_version,
                config_version=e.config_version,
                created_at=e.created_at,
                grounding_status=e.grounding_status,
                prompt_injection_detected=e.prompt_injection_detected,
                grounding_summary=e.grounding_summary,
                tool_name=e.tool_name,
            )
            for e in entries
        ],
    }


@router.get(
    "/query-audit/{request_id}",
    response_model=QueryAuditByRequestResponse,
    summary="Query audit log by request",
    description="Retrieve all query audit entries for a specific request ID.",
)
async def get_query_audit_by_request(request_id: str):
    """Get all query audit entries for a specific request."""
    store = get_query_audit_service()
    entries = store.get_by_request_id(request_id)

    return {
        "request_id": request_id,
        "total": len(entries),
        "entries": [
            QueryAuditEntryResponse(
                entry_id=e.entry_id,
                request_id=e.request_id,
                user_id=e.user_id,
                path=e.path,
                query_text=e.query_text,
                retrieved_chunks=e.retrieved_chunks,
                sources=e.sources,
                response_summary=e.response_summary,
                confidence=e.confidence,
                completeness=e.completeness,
                verified=e.verified,
                model_version=e.model_version,
                config_version=e.config_version,
                created_at=e.created_at,
                grounding_status=e.grounding_status,
                prompt_injection_detected=e.prompt_injection_detected,
                grounding_summary=e.grounding_summary,
                tool_name=e.tool_name,
            )
            for e in entries
        ],
    }
