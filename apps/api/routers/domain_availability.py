"""Domain availability endpoints for API and MCP consumers."""

from __future__ import annotations

from db import db_session
from fastapi import APIRouter, HTTPException, Query

from services.domain_availability import (
    EMPTY_STATUSES,
    get_domain_availability,
    list_domain_availability as list_availability,
    summarize_availability,
)

router = APIRouter(prefix="/v1/domain-availability", tags=["domain-availability"])


@router.get("", operation_id="list_domain_availability")
def list_domain_availability(
    only_empty: bool = Query(False, description="Return only tables that are not safe to answer from directly."),
    status: str | None = Query(None, description="Filter by populated/workflow_empty/allowed_empty/configured_but_unavailable."),
    domain: str | None = Query(None, description="Case-insensitive domain substring."),
):
    if status is not None and status not in {*EMPTY_STATUSES, "populated"}:
        raise HTTPException(status_code=422, detail=f"Unsupported availability status: {status}")
    with db_session() as db:
        records = list_availability(db, only_empty=only_empty, status=status, domain=domain)
    return {
        "summary": summarize_availability(records),
        "items": records,
        "total": len(records),
    }


@router.get("/{table}", operation_id="get_domain_availability")
def get_table_domain_availability(table: str):
    with db_session() as db:
        record = get_domain_availability(db, table)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Table not registered in Ralph registry: {table}")
    return record
