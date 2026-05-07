"""Source manifest and freshness endpoints."""

from __future__ import annotations

from db import db_session
from fastapi import APIRouter
from middleware.metrics import record_source_freshness_metrics
from services.source_manifest import (
    check_and_create_freshness_alerts,
    get_freshness_alerts,
    get_freshness_ledger,
    get_source_manifest,
)

router = APIRouter(prefix="/v1/sources", tags=["source-manifest"])


@router.get("/manifest")
def source_manifest():
    with db_session() as db:
        sources = get_source_manifest(db)
    return {"total": len(sources), "sources": sources}


@router.get("/freshness")
def source_freshness():
    with db_session() as db:
        sources = get_freshness_ledger(db)
    record_source_freshness_metrics(sources)
    return {"total": len(sources), "sources": sources}


@router.get("/freshness-alerts")
def source_freshness_alerts():
    with db_session() as db:
        sources = get_source_manifest(db)
        record_source_freshness_metrics(sources)
        check_and_create_freshness_alerts(db)
        alerts = get_freshness_alerts(db)
    return {
        "total": len(alerts),
        "critical": sum(1 for a in alerts if a["alert_level"] == "critical"),
        "warning": sum(1 for a in alerts if a["alert_level"] == "warning"),
        "alerts": alerts,
    }
