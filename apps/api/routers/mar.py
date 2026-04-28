"""MAR (Market Abuse Regulation) data model endpoints.

Fase 31.8 — Expansion regulatoria.

Endpoints:
    GET  /v1/mar/insider-transactions        — list insider transactions (PPI)
    GET  /v1/mar/insider-transactions/{id}   — get insider transaction by ID
    GET  /v1/mar/suspicious-reports          — list suspicious transaction reports
    GET  /v1/mar/suspicious-reports/{id}     — get suspicious report by ID
    GET  /v1/mar/manipulation-indicators     — list manipulation indicators
    GET  /v1/mar/manipulation-indicators/{id} — get manipulation indicator by ID
    GET  /v1/mar/insider-communications      — list insider communications
    GET  /v1/mar/insider-communications/{id} — get insider communication by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    MarInsiderCommunicationDetail,
    MarInsiderCommunicationListResponse,
    MarInsiderTransactionDetail,
    MarInsiderTransactionListResponse,
    MarMarketManipulationIndicatorDetail,
    MarMarketManipulationIndicatorListResponse,
    MarSuspiciousTransactionReportDetail,
    MarSuspiciousTransactionReportListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/mar", tags=["mar"])


# ===========================================================================
# Insider Transactions (PPI)
# ===========================================================================


@router.get(
    "/insider-transactions",
    response_model=MarInsiderTransactionListResponse,
    operation_id="list_mar_insider_transactions",
)
async def list_mar_insider_transactions(
    status: str | None = Query(None, description="Filtrar por estado: reported, under_review, flagged"),
    search: str | None = Query(None, description="Buscar por ppi_name"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mt.status = :status")
        params["status"] = status
    if search:
        filters.append("LOWER(mt.ppi_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, ppi_name, instrument, transaction_type, value_eur, status
                FROM mar_insider_transaction mt
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM mar_insider_transaction mt
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/insider-transactions/{item_id}",
    response_model=MarInsiderTransactionDetail,
    operation_id="get_mar_insider_transaction",
)
async def get_mar_insider_transaction(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, ppi_name, ppi_role, instrument, transaction_type,
                       quantity, value_eur, price, date_time, country, status, created_at
                FROM mar_insider_transaction mt
                WHERE mt.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Suspicious Transaction Reports
# ===========================================================================


@router.get(
    "/suspicious-reports",
    response_model=MarSuspiciousTransactionReportListResponse,
    operation_id="list_mar_suspicious_reports",
)
async def list_mar_suspicious_reports(
    status: str | None = Query(None, description="Filtrar por estado"),
    submitted_to_cnmv: bool | None = Query(None, description="Filtrar por reporte a CNMV"),
    search: str | None = Query(None, description="Buscar por instrument"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("ms.status = :status")
        params["status"] = status
    if submitted_to_cnmv is not None:
        filters.append("ms.submitted_to_cnmv = :submitted_to_cnmv")
        params["submitted_to_cnmv"] = submitted_to_cnmv
    if search:
        filters.append("LOWER(ms.instrument) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, instrument, severity, submitted_to_cnmv, cnmv_reference, status
                FROM mar_suspicious_transaction_report ms
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM mar_suspicious_transaction_report ms
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/suspicious-reports/{item_id}",
    response_model=MarSuspiciousTransactionReportDetail,
    operation_id="get_mar_suspicious_report",
)
async def get_mar_suspicious_report(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, instrument, pattern_description,
                       detection_method, severity, submitted_to_cnmv,
                       cnmv_reference, status, created_at
                FROM mar_suspicious_transaction_report ms
                WHERE ms.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Market Manipulation Indicators
# ===========================================================================


@router.get(
    "/manipulation-indicators",
    response_model=MarMarketManipulationIndicatorListResponse,
    operation_id="list_mar_manipulation_indicators",
)
async def list_mar_manipulation_indicators(
    status: str | None = Query(None, description="Filtrar por estado"),
    pattern_type: str | None = Query(None, description="Filtrar por tipo de patron"),
    search: str | None = Query(None, description="Buscar por instrument"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mm.status = :status")
        params["status"] = status
    if pattern_type:
        filters.append("mm.pattern_type = :pattern_type")
        params["pattern_type"] = pattern_type
    if search:
        filters.append("LOWER(mm.instrument) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, pattern_type, instrument, confidence_score, status
                FROM mar_market_manipulation_indicator mm
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM mar_market_manipulation_indicator mm
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/manipulation-indicators/{item_id}",
    response_model=MarMarketManipulationIndicatorDetail,
    operation_id="get_mar_manipulation_indicator",
)
async def get_mar_manipulation_indicator(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, pattern_type, instrument, time_window,
                       volume_anomaly_pct, price_anomaly_pct,
                       confidence_score, status, created_at
                FROM mar_market_manipulation_indicator mm
                WHERE mm.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Insider Communications
# ===========================================================================


@router.get(
    "/insider-communications",
    response_model=MarInsiderCommunicationListResponse,
    operation_id="list_mar_insider_communications",
)
async def list_mar_insider_communications(
    search: str | None = Query(None, description="Buscar por sender_id o receiver_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if search:
        filters.append(
            "(ms.sender_id = :search::integer OR ms.receiver_id = :search2::integer)"
        )
        params["search"] = search
        params["search2"] = search

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, sender_id, receiver_id, content_summary, channel, timestamp
                FROM mar_insider_communication ms
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM mar_insider_communication ms
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/insider-communications/{item_id}",
    response_model=MarInsiderCommunicationDetail,
    operation_id="get_mar_insider_communication",
)
async def get_mar_insider_communication(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, sender_id, receiver_id, channel, timestamp,
                       content_summary, inside_info_reference, created_at
                FROM mar_insider_communication ms
                WHERE ms.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)
