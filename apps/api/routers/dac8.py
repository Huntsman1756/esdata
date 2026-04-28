"""DAC8 / DAC9 crypto-asset information exchange endpoints.

Fase 31 — Expansion regulatoria.

Endpoints:
    GET  /v1/dac8/reporting-entities              — list reporting entities
    GET  /v1/dac8/reporting-entities/{id}         — get entity by ID
    GET  /v1/dac8/crypto-reports                  — list DAC crypto reports
    GET  /v1/dac8/crypto-reports/{id}             — get report by ID
    GET  /v1/dac8/wallet-holders                  — list wallet holders
    GET  /v1/dac8/wallet-holders/{id}             — get holder by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    DacCryptoReportDetail,
    DacCryptoReportListResponse,
    DacReportingEntityDetail,
    DacReportingEntityListResponse,
    DacWalletHolderDetail,
    DacWalletHolderListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/dac8", tags=["dac8"])


# ===========================================================================
# DAC Reporting Entities
# ===========================================================================


@router.get(
    "/reporting-entities",
    response_model=DacReportingEntityListResponse,
    operation_id="list_dac_reporting_entities",
)
async def list_dac_reporting_entities(
    member_state: str | None = Query(None, description="Filtrar por estado miembro"),
    entity_type: str | None = Query(None, description="Filtrar por tipo: crypto-asset service provider, exchange, custodian"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive, suspended"),
    dac8_registered: bool | None = Query(None, description="Filtrar por registro DAC8"),
    dac9_registered: bool | None = Query(None, description="Filtrar por registro DAC9"),
    search: str | None = Query(None, description="Buscar por NIF"),
):
    filters = ["1=1"]
    params: dict = {}

    if member_state:
        filters.append("de.member_state = :member_state")
        params["member_state"] = member_state
    if entity_type:
        filters.append("de.entity_type = :entity_type")
        params["entity_type"] = entity_type
    if status:
        filters.append("de.status = :status")
        params["status"] = status
    if dac8_registered is not None:
        filters.append("de.dac8_registered = :dac8_registered")
        params["dac8_registered"] = dac8_registered
    if dac9_registered is not None:
        filters.append("de.dac9_registered = :dac9_registered")
        params["dac9_registered"] = dac9_registered
    if search:
        filters.append("LOWER(de.tin) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, tin, entity_type, member_state,
                       dac8_registered, dac9_registered, status
                FROM dac_reporting_entity de
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        entities = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM dac_reporting_entity de
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"entities": entities, "total": count}


@router.get(
    "/reporting-entities/{item_id}",
    response_model=DacReportingEntityDetail,
    operation_id="get_dac_reporting_entity",
)
async def get_dac_reporting_entity(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, tin, entity_type, member_state,
                       dac8_registered, dac9_registered, status, created_at
                FROM dac_reporting_entity de
                WHERE de.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Entidad de reporte DAC8/DAC9 no encontrada"},
            )
        return dict(row)


# ===========================================================================
# DAC Crypto Reports
# ===========================================================================


@router.get(
    "/crypto-reports",
    response_model=DacCryptoReportListResponse,
    operation_id="list_dac_crypto_reports",
)
async def list_dac_crypto_reports(
    entity_id: int | None = Query(None, description="Filtrar por ID de entidad reportante"),
    reporting_period: str | None = Query(None, description="Filtrar por periodo de reporte (YYYY-MM)"),
    status: str | None = Query(None, description="Filtrar por estado: draft, submitted, amended, rejected"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("cr.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if reporting_period:
        filters.append("cr.reporting_period = :reporting_period")
        params["reporting_period"] = reporting_period
    if status:
        filters.append("cr.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, reporting_period, status,
                       crypto_transactions_count, wallet_holders_count
                FROM dac_crypto_report cr
                WHERE {" AND ".join(filters)}
                ORDER BY cr.id DESC
                """
            ),
            params,
        ).mappings()
        reports = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM dac_crypto_report cr
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"reports": reports, "total": count}


@router.get(
    "/crypto-reports/{item_id}",
    response_model=DacCryptoReportDetail,
    operation_id="get_dac_crypto_report",
)
async def get_dac_crypto_report(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, reporting_period, submitted_at,
                       status, crypto_transactions_count, wallet_holders_count, created_at
                FROM dac_crypto_report cr
                WHERE cr.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Reporte DAC8/DAC9 no encontrado"},
            )
        return dict(row)


# ===========================================================================
# DAC Wallet Holders
# ===========================================================================


@router.get(
    "/wallet-holders",
    response_model=DacWalletHolderListResponse,
    operation_id="list_dac_wallet_holders",
)
async def list_dac_wallet_holders(
    report_id: int | None = Query(None, description="Filtrar por ID de reporte"),
    holder_member_state: str | None = Query(None, description="Filtrar por estado miembro del titular"),
    holder_type: str | None = Query(None, description="Filtrar por tipo: individual, entity"),
    verification_status: str | None = Query(None, description="Filtrar por estado de verificacion"),
    search: str | None = Query(None, description="Buscar por direccion de wallet o NIF"),
):
    filters = ["1=1"]
    params: dict = {}

    if report_id is not None:
        filters.append("wh.report_id = :report_id")
        params["report_id"] = report_id
    if holder_member_state:
        filters.append("wh.holder_member_state = :holder_member_state")
        params["holder_member_state"] = holder_member_state
    if holder_type:
        filters.append("wh.holder_type = :holder_type")
        params["holder_type"] = holder_type
    if verification_status:
        filters.append("wh.verification_status = :verification_status")
        params["verification_status"] = verification_status
    if search:
        filters.append(
            "(LOWER(wh.wallet_address) LIKE LOWER(:search) OR LOWER(wh.holder_tin) LIKE LOWER(:search))"
        )
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, report_id, wallet_address, holder_tin,
                       holder_member_state, holder_type, total_value_eur,
                       verification_status
                FROM dac_wallet_holder wh
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        holders = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM dac_wallet_holder wh
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"holders": holders, "total": count}


@router.get(
    "/wallet-holders/{item_id}",
    response_model=DacWalletHolderDetail,
    operation_id="get_dac_wallet_holder",
)
async def get_dac_wallet_holder(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, report_id, wallet_address, holder_tin,
                       holder_member_state, holder_type, total_value_eur,
                       verification_status, created_at
                FROM dac_wallet_holder wh
                WHERE wh.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Titular de wallet DAC8/DAC9 no encontrado"},
            )
        return dict(row)
