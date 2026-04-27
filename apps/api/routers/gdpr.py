"""GDPR router for AI Act compliance (Fase 26.10).

Endpoints for ARCO data subject requests and DPIA summary.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from services.gdpr import ARCOType, get_gdpr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/gdpr", tags=["GDPR"])


@router.post("/solicitud")
def create_arco_request(
    tipo: str,
    datos_afectados: str,
    solicitante: str,
) -> dict:
    """Create a new ARCO (data subject) request."""
    service = get_gdpr_service()
    request = service.create_arco_request(
        tipo=tipo,
        datos_afectados=datos_afectados,
        solicitante=solicitante,
    )
    return request.model_dump()


@router.get("/solicitudes/{request_id}")
def get_arco_request(request_id: str) -> dict | None:
    """Get the status of an ARCO request."""
    service = get_gdpr_service()
    request = service.get_request(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"Request not found: {request_id}")
    return request.model_dump()


@router.get("/solicitudes")
def list_arco_requests(
    estado: str | None = Query(default=None, description="Filter by status"),
) -> list[dict]:
    """List ARCO requests, optionally filtered by status."""
    service = get_gdpr_service()
    requests = service.get_all_requests(estado=estado)
    return [r.model_dump() for r in requests]


@router.post("/solicitudes/{request_id}/fulfill")
def fulfill_arco_request(
    request_id: str,
    estado: str = "completada",
    respuesta: str = "",
) -> dict:
    """Fulfill an ARCO request."""
    service = get_gdpr_service()
    request = service.fulfill_arco_request(
        request_id=request_id,
        estado=estado,
        respuesta=respuesta,
    )
    if request is None:
        raise HTTPException(status_code=404, detail=f"Request not found: {request_id}")
    return request.model_dump()


@router.get("/dpia")
def get_dpia_summary() -> dict:
    """Get Data Protection Impact Assessment summary (without sensitive details)."""
    service = get_gdpr_service()
    return service.get_dpia_summary()


@router.get("/solicitudes/pending")
def get_pending_requests() -> list[dict]:
    """Get all pending ARCO requests."""
    service = get_gdpr_service()
    requests = service.get_pending_requests()
    return [r.model_dump() for r in requests]


@router.get("/solicitudes/stats")
def get_request_stats() -> dict:
    """Get ARCO request statistics by type."""
    service = get_gdpr_service()
    return {
        "total": service.total_requests,
        "by_type": service.get_request_count_by_type(),
    }
