"""Source manifest and freshness endpoints."""

from __future__ import annotations

from db import db_session
from fastapi import APIRouter
from middleware.metrics import record_source_freshness_metrics
from services.source_manifest import get_freshness_ledger, get_source_manifest

router = APIRouter(prefix="/v1/sources", tags=["source-manifest"])


@router.get("/manifest")
def source_manifest():
    # In 4.3 these HTTP surfaces stay source-level; row-level quality data lives
    # behind persistence-oriented MCP access instead of this router response.
    with db_session() as db:
        sources = get_source_manifest(db)
    return {"total": len(sources), "sources": sources}


@router.get("/freshness")
def source_freshness():
    with db_session() as db:
        sources = get_freshness_ledger(db)
    record_source_freshness_metrics(sources)
    return {"total": len(sources), "sources": sources}
