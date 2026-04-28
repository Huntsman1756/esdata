"""AIFMD and UCITS data model endpoints.

Fase 31.9.3 — Expansion regulatoria: AIFMD y UCITS.

Endpoints:
    GET  /v1/aifmd/funds                      -- list AIFMD funds
    GET  /v1/aifmd/funds/{id}                 -- get fund by ID
    GET  /v1/aifmd/regulatory-reports         -- list AIFMD regulatory reports
    GET  /v1/aifmd/regulatory-reports/{id}    -- get report by ID
    GET  /v1/aifmd/liquidity-management       -- list liquidity management
    GET  /v1/aifmd/liquidity-management/{id}  -- get by ID
    GET  /v1/ucits/funds                      -- list UCITS funds
    GET  /v1/ucits/funds/{id}                 -- get fund by ID
    GET  /v1/ucits/regulatory-reports         -- list UCITS regulatory reports
    GET  /v1/ucits/regulatory-reports/{id}    -- get report by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    AifmdFundDetail,
    AifmdFundListResponse,
    AifmdLiquidityManagementDetail,
    AifmdLiquidityManagementListResponse,
    AifmdRegulatoryReportDetail,
    AifmdRegulatoryReportListResponse,
    UcitsFundDetail,
    UcitsFundListResponse,
    UcitsRegulatoryReportDetail,
    UcitsRegulatoryReportListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/aifmd", tags=["aifmd"])
ucits_router = APIRouter(prefix="/v1/ucits", tags=["ucits"])


# ===========================================================================
# AIFMD Funds
# ===========================================================================


@router.get(
    "/funds",
    response_model=AifmdFundListResponse,
    operation_id="list_aifmd_funds",
)
async def list_aifmd_funds(
    fund_type: str | None = Query(None, description="Filtrar por tipo: alternative, real-estate, pfav, securitization"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive"),
    home_member_state: str | None = Query(None, description="Filtrar por pais de origen"),
):
    filters = ["1=1"]
    params: dict = {}

    if fund_type:
        filters.append("af.fund_type = :fund_type")
        params["fund_type"] = fund_type
    if status:
        filters.append("af.status = :status")
        params["status"] = status
    if home_member_state:
        filters.append("af.home_member_state = :home_member_state")
        params["home_member_state"] = home_member_state

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, fund_name, aifm_id, fund_type, registration_date,
                       home_member_state, cross_border_passport, total_aum_eur,
                       investor_type, lock_up_period, redemption_frequency,
                       leverage_method, leverage_max_pct, status
                FROM aifmd_fund af
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
                SELECT COUNT(*) FROM aifmd_fund af
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/funds/{fund_id}",
    response_model=AifmdFundDetail,
    operation_id="get_aifmd_fund",
)
async def get_aifmd_fund(fund_id: int):
    with db_session() as db:
        row = db.execute(
            text("""
                SELECT id, fund_name, aifm_id, fund_type, registration_date,
                       home_member_state, cross_border_passport, total_aum_eur,
                       investor_type, lock_up_period, redemption_frequency,
                       leverage_method, leverage_max_pct, status, created_at
                FROM aifmd_fund
                WHERE id = :fund_id
            """),
            {"fund_id": fund_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Fondo AIFMD no encontrado"})
        return dict(row)


# ===========================================================================
# AIFMD Regulatory Reports
# ===========================================================================


@router.get(
    "/regulatory-reports",
    response_model=AifmdRegulatoryReportListResponse,
    operation_id="list_aifmd_regulatory_reports",
)
async def list_aifmd_regulatory_reports(
    fund_id: int | None = Query(None, description="Filtrar por fondo"),
    report_type: str | None = Query(None, description="Filtrar por tipo: annual, semi-annual"),
    status: str | None = Query(None, description="Filtrar por estado: draft, filed"),
):
    filters = ["1=1"]
    params: dict = {}

    if fund_id:
        filters.append("ar.fund_id = :fund_id")
        params["fund_id"] = fund_id
    if report_type:
        filters.append("ar.report_type = :report_type")
        params["report_type"] = report_type
    if status:
        filters.append("ar.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, fund_id, report_type, reporting_period, url,
                       filed_date, status
                FROM aifmd_regulatory_report ar
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
                SELECT COUNT(*) FROM aifmd_regulatory_report ar
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/regulatory-reports/{report_id}",
    response_model=AifmdRegulatoryReportDetail,
    operation_id="get_aifmd_regulatory_report",
)
async def get_aifmd_regulatory_report(report_id: int):
    with db_session() as db:
        row = db.execute(
            text("""
                SELECT id, fund_id, report_type, reporting_period, url,
                       filed_date, status, created_at
                FROM aifmd_regulatory_report
                WHERE id = :report_id
            """),
            {"report_id": report_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Reporte regulatorio AIFMD no encontrado"})
        return dict(row)


# ===========================================================================
# AIFMD Liquidity Management
# ===========================================================================


@router.get(
    "/liquidity-management",
    response_model=AifmdLiquidityManagementListResponse,
    operation_id="list_aifmd_liquidity_management",
)
async def list_aifmd_liquidity_management(
    fund_id: int | None = Query(None, description="Filtrar por fondo"),
    redemption_suspended: bool | None = Query(None, description="Filtrar por suspension de redencion"),
):
    filters = ["1=1"]
    params: dict = {}

    if fund_id:
        filters.append("lm.fund_id = :fund_id")
        params["fund_id"] = fund_id
    if redemption_suspended is not None:
        filters.append("lm.redemption_suspended = :redemption_suspended")
        params["redemption_suspended"] = redemption_suspended

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, fund_id, redemption_suspended, suspension_date,
                       gating_applied, swing_price_applied, side_pocket_applied,
                       stress_test_result, valuation_frequency
                FROM aifmd_liquidity_management lm
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
                SELECT COUNT(*) FROM aifmd_liquidity_management lm
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/liquidity-management/{lm_id}",
    response_model=AifmdLiquidityManagementDetail,
    operation_id="get_aifmd_liquidity_management",
)
async def get_aifmd_liquidity_management(lm_id: int):
    with db_session() as db:
        row = db.execute(
            text("""
                SELECT id, fund_id, redemption_suspended, suspension_date,
                       gating_applied, swing_price_applied, side_pocket_applied,
                       stress_test_result, valuation_frequency, created_at
                FROM aifmd_liquidity_management
                WHERE id = :lm_id
            """),
            {"lm_id": lm_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Gestion de liquidez AIFMD no encontrada"})
        return dict(row)


# ===========================================================================
# UCITS Funds
# ===========================================================================


@ucits_router.get(
    "/funds",
    response_model=UcitsFundListResponse,
    operation_id="list_ucits_funds",
)
async def list_ucits_funds(
    fund_type: str | None = Query(None, description="Filtrar por tipo de fondo"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive"),
    home_member_state: str | None = Query(None, description="Filtrar por pais de origen"),
):
    filters = ["1=1"]
    params: dict = {}

    if fund_type:
        filters.append("uf.fund_type = :fund_type")
        params["fund_type"] = fund_type
    if status:
        filters.append("uf.status = :status")
        params["status"] = status
    if home_member_state:
        filters.append("uf.home_member_state = :home_member_state")
        params["home_member_state"] = home_member_state

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, fund_name, management_company, registration_date,
                       home_member_state, cross_border_passport, total_aum_eur,
                       depositary_id, krid_url, investment_strategy, risk_profile,
                       status
                FROM ucits_fund uf
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
                SELECT COUNT(*) FROM ucits_fund uf
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@ucits_router.get(
    "/funds/{fund_id}",
    response_model=UcitsFundDetail,
    operation_id="get_ucits_fund",
)
async def get_ucits_fund(fund_id: int):
    with db_session() as db:
        row = db.execute(
            text("""
                SELECT id, fund_name, management_company, registration_date,
                       home_member_state, cross_border_passport, total_aum_eur,
                       depositary_id, krid_url, investment_strategy, risk_profile,
                       status, created_at
                FROM ucits_fund
                WHERE id = :fund_id
            """),
            {"fund_id": fund_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Fondo UCITS no encontrado"})
        return dict(row)


# ===========================================================================
# UCITS Regulatory Reports
# ===========================================================================


@ucits_router.get(
    "/regulatory-reports",
    response_model=UcitsRegulatoryReportListResponse,
    operation_id="list_ucits_regulatory_reports",
)
async def list_ucits_regulatory_reports(
    fund_id: int | None = Query(None, description="Filtrar por fondo"),
    report_type: str | None = Query(None, description="Filtrar por tipo: annual, semi-annual"),
    status: str | None = Query(None, description="Filtrar por estado: draft, filed"),
):
    filters = ["1=1"]
    params: dict = {}

    if fund_id:
        filters.append("ur.fund_id = :fund_id")
        params["fund_id"] = fund_id
    if report_type:
        filters.append("ur.report_type = :report_type")
        params["report_type"] = report_type
    if status:
        filters.append("ur.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, fund_id, report_type, reporting_period, url,
                       filed_date, status
                FROM ucits_regulatory_report ur
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
                SELECT COUNT(*) FROM ucits_regulatory_report ur
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@ucits_router.get(
    "/regulatory-reports/{report_id}",
    response_model=UcitsRegulatoryReportDetail,
    operation_id="get_ucits_regulatory_report",
)
async def get_ucits_regulatory_report(report_id: int):
    with db_session() as db:
        row = db.execute(
            text("""
                SELECT id, fund_id, report_type, reporting_period, url,
                       filed_date, status, created_at
                FROM ucits_regulatory_report
                WHERE id = :report_id
            """),
            {"report_id": report_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Reporte regulatorio UCITS no encontrado"})
        return dict(row)
