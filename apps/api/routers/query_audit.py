"""Query audit log router for Fase 30.2 — Persistencia durable."""

from fastapi import APIRouter, Query

from schemas import BaseModel, Field
from services.query_audit import get_query_audit_service

router = APIRouter(prefix="/v1/ai", tags=["query_audit"])


class QueryAuditEntryResponse(BaseModel):
    """Response model for a single query audit log entry."""

    entry_id: str = Field(description="Unique entry identifier")
    request_id: str = Field(description="Correlation with original request")
    user_id: str | None = Field(default=None, description="Authenticated user ID")
    path: str = Field(description="API path that was queried")
    query_text: str = Field(description="The query text sent")
    retrieved_chunks: list[dict] = Field(default_factory=list, description="Chunks retrieved")
    response_summary: str = Field(default="", description="Summary of the response")
    model_version: str | None = Field(default=None, description="Model version used")
    config_version: str | None = Field(default=None, description="Config version used")
    created_at: str = Field(description="When the query was recorded (ISO 8601)")


class QueryAuditLogResponse(BaseModel):
    """Response model for query audit log query."""

    total: int = Field(description="Total entries matching the query")
    path: str | None = Field(default=None, description="Path filter applied")
    entries: list[QueryAuditEntryResponse] = Field(default_factory=list, description="Audit log entries")


class QueryAuditByRequestResponse(BaseModel):
    """Response model for query audit by request ID."""

    request_id: str = Field(description="The request ID queried")
    total: int = Field(description="Total entries for this request")
    entries: list[QueryAuditEntryResponse] = Field(default_factory=list, description="Audit entries for the request")


@router.get(
    "/query-audit",
    response_model=QueryAuditLogResponse,
    summary="Query audit log",
    description="Retrieve query audit log entries with optional path filter.",
)
async def get_query_audit_log(
    path: str | None = Query(None, description="Filter by API path (e.g. /v1/consulta)"),
):
    """Query query audit log with optional path filter."""
    store = get_query_audit_service()
    entries = store.get_entries(path=path)

    return {
        "total": len(entries),
        "path": path,
        "entries": [
            QueryAuditEntryResponse(
                entry_id=e.entry_id,
                request_id=e.request_id,
                user_id=e.user_id,
                path=e.path,
                query_text=e.query_text,
                retrieved_chunks=e.retrieved_chunks,
                response_summary=e.response_summary,
                model_version=e.model_version,
                config_version=e.config_version,
                created_at=e.created_at,
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
                response_summary=e.response_summary,
                model_version=e.model_version,
                config_version=e.config_version,
                created_at=e.created_at,
            )
            for e in entries
        ],
    }
