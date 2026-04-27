"""AI audit log router for AI Act compliance (Fase 24.2).

Endpoints to query the AI audit log for regulatory compliance.
"""

from fastapi import APIRouter, Query

from schemas import BaseModel, Field
from services.ai_audit import get_audit_store

router = APIRouter(prefix="/v1/ai", tags=["ai_audit_log"])


class AIAuditEntryResponse(BaseModel):
    """Response model for a single AI audit log entry."""

    request_id: str = Field(description="Correlation with original request")
    timestamp: str = Field(description="When the event occurred (ISO 8601)")
    componente: str = Field(description="AI component")
    accion: str = Field(description="Action performed")
    configuracion: dict = Field(default_factory=dict, description="Configuration parameters used")
    resultado_resumen: str = Field(default="", description="Summary of result")
    latencia_ms: float | None = Field(default=None, description="Execution time in ms")
    error: str | None = Field(default=None, description="Error if any")
    user_id: str | None = Field(default=None, description="Authenticated user ID")
    ip_address: str | None = Field(default=None, description="Origin IP")


class AIAuditLogResponse(BaseModel):
    """Response model for AI audit log query."""

    total: int = Field(description="Total entries matching the query")
    desde: str | None = Field(default=None, description="Start date filter applied")
    hasta: str | None = Field(default=None, description="End date filter applied")
    componente: str | None = Field(default=None, description="Component filter applied")
    entries: list[AIAuditEntryResponse] = Field(default_factory=list, description="Audit log entries")


class AIAuditLogByRequestResponse(BaseModel):
    """Response model for audit log by request ID."""

    request_id: str = Field(description="The request ID queried")
    total: int = Field(description="Total entries for this request")
    entries: list[AIAuditEntryResponse] = Field(default_factory=list, description="Audit entries for the request")


@router.get(
    "/audit-log",
    response_model=AIAuditLogResponse,
    summary="AI audit log query",
    description="Retrieve AI audit log entries with optional date and component filters.",
)
async def get_ai_audit_log(
    desde: str | None = Query(None, description="Start date (ISO 8601, e.g. 2026-01-01T00:00:00Z)"),
    hasta: str | None = Query(None, description="End date (ISO 8601, e.g. 2026-12-31T23:59:59Z)"),
    componente: str | None = Query(None, description="Filter by component: semantic_search, hybrid_search, consulta, embedding"),
):
    """Query AI audit log with optional filters."""
    store = get_audit_store()
    entries = store.get_entries(
        desde=desde,
        hasta=hasta,
        componente=componente,
    )

    return {
        "total": len(entries),
        "desde": desde,
        "hasta": hasta,
        "componente": componente,
        "entries": [
            AIAuditEntryResponse(
                request_id=e.request_id,
                timestamp=e.timestamp,
                componente=e.componente,
                accion=e.accion,
                configuracion=e.configuracion,
                resultado_resumen=e.resultado_resumen,
                latencia_ms=e.latencia_ms,
                error=e.error,
                user_id=e.user_id,
                ip_address=e.ip_address,
            )
            for e in entries
        ],
    }


@router.get(
    "/audit-log/{request_id}",
    response_model=AIAuditLogByRequestResponse,
    summary="AI audit log by request",
    description="Retrieve all audit entries for a specific request ID.",
)
async def get_ai_audit_log_by_request(request_id: str):
    """Get all audit entries for a specific request."""
    store = get_audit_store()
    entries = store.get_by_request_id(request_id)

    return {
        "request_id": request_id,
        "total": len(entries),
        "entries": [
            AIAuditEntryResponse(
                request_id=e.request_id,
                timestamp=e.timestamp,
                componente=e.componente,
                accion=e.accion,
                configuracion=e.configuracion,
                resultado_resumen=e.resultado_resumen,
                latencia_ms=e.latencia_ms,
                error=e.error,
                user_id=e.user_id,
                ip_address=e.ip_address,
            )
            for e in entries
        ],
    }
