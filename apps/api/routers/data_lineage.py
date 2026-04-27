"""Data lineage router for AI Act compliance (Fase 26.9).

Endpoints for data lineage, quality scores, and data catalog.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from services.data_lineage import get_data_lineage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/data", tags=["Data Governance"])


@router.get("/lineage")
def get_lineage(
    tabla: str = Query(..., description="Table name to query lineage for"),
    campo: str | None = Query(default=None, description="Optional field name"),
) -> list[dict]:
    """Get lineage records for a table field."""
    service = get_data_lineage_service()
    entries = service.get_lineage(tabla, campo)
    return [e.model_dump() for e in entries]


@router.get("/quality")
def get_quality(
    tabla: str | None = Query(default=None, description="Filter by table"),
) -> list[dict] | dict:
    """Get data quality scores.

    If `tabla` is provided, returns a single table's quality.
    Otherwise returns quality for all tracked tables.
    """
    service = get_data_lineage_service()
    if tabla:
        return service.get_data_quality(tabla)
    return service.get_all_quality_scores()


@router.get("/catalog")
def get_catalog() -> list[dict]:
    """Get the full data catalog."""
    service = get_data_lineage_service()
    return service.get_data_catalog()


@router.get("/catalog/{tabla}")
def get_catalog_entry(tabla: str) -> dict | None:
    """Get catalog entry for a specific table."""
    service = get_data_lineage_service()
    return service.get_catalog_entry(tabla)
