"""CRD V/CRR, BRRD and EMIR API routers.

CRD V/CRR — capital position and stress tests for credit institutions.
BRRD — bail-in and MREL compliance.
EMIR — trade reporting and clearing member data.
"""

import contextlib
import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    BrrdBailInCreate,
    BrrdBailInDetail,
    BrrdBailInListResponse,
    BrrdBailInSummary,
    BrrdBailInUpdate,
    CrdCapitalPositionCreate,
    CrdCapitalPositionDetail,
    CrdCapitalPositionListResponse,
    CrdCapitalPositionSummary,
    CrdCapitalPositionUpdate,
    CrdStressTestCreate,
    CrdStressTestDetail,
    CrdStressTestListResponse,
    CrdStressTestSummary,
    CrdStressTestUpdate,
    EmirClearingMemberCreate,
    EmirClearingMemberDetail,
    EmirClearingMemberListResponse,
    EmirClearingMemberSummary,
    EmirClearingMemberUpdate,
    EmirTradeReportCreate,
    EmirTradeReportDetail,
    EmirTradeReportListResponse,
    EmirTradeReportSummary,
    EmirTradeReportUpdate,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/crd", tags=["crd"])
ucits_router = APIRouter(prefix="/v1/emir", tags=["emir"])


def _parse_json(row: dict, *keys: str) -> dict:
    for key in keys:
        val = row.get(key)
        if val and isinstance(val, str):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                row[key] = json.loads(val)
    return row


# =============================================================================
# CRD/CRR — Capital Position
# =============================================================================

@router.get("/capital-positions", response_model=CrdCapitalPositionListResponse, operation_id="list_crd_capital_positions")
async def list_crd_capital_positions(
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    reporting_date: str | None = Query(None, description="Filter by reporting date (YYYY-MM-DD)"),
    status: str | None = Query(None, description="Filter by status"),
):
    """List capital positions for CRD/CRR reporting."""
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("entity_id = :entity_id")
        params["entity_id"] = entity_id
    if reporting_date is not None:
        filters.append("reporting_date = :reporting_date")
        params["reporting_date"] = reporting_date
    if status is not None:
        filters.append("status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(f"SELECT * FROM crd_capital_position WHERE {' AND '.join(filters)} ORDER BY reporting_date DESC"),
            params,
        ).mappings().all()
        items = [CrdCapitalPositionSummary(**dict(r)) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM crd_capital_position WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get("/capital-positions/{position_id}", response_model=CrdCapitalPositionDetail, operation_id="get_crd_capital_position")
async def get_crd_capital_position(position_id: int):
    """Get a single capital position by ID."""
    with db_session() as db:
        row = db.execute(
            text("SELECT * FROM crd_capital_position WHERE id = :id"),
            {"id": position_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Capital position not found")
        return CrdCapitalPositionDetail(**dict(row))


@router.post("/capital-positions", response_model=CrdCapitalPositionSummary, status_code=201, operation_id="create_crd_capital_position")
async def create_crd_capital_position(data: CrdCapitalPositionCreate):
    """Create a new capital position record."""
    with db_session() as db:
        row = db.execute(
            text(
                "INSERT INTO crd_capital_position "
                "(entity_id, reporting_date, cet1_ratio, tier1_ratio, total_capital_ratio, "
                "cet1_amount, tier1_amount, total_capital_amount, leverage_ratio, "
                "risk_weighted_assets, status, created_at) "
                "VALUES (:entity_id, :reporting_date, :cet1_ratio, :tier1_ratio, "
                ":total_capital_ratio, :cet1_amount, :tier1_amount, "
                ":total_capital_amount, :leverage_ratio, :risk_weighted_assets, "
                ":status, CURRENT_TIMESTAMP) RETURNING *"
            ),
            {
                "entity_id": data.entity_id,
                "reporting_date": data.reporting_date,
                "cet1_ratio": data.cet1_ratio,
                "tier1_ratio": data.tier1_ratio,
                "total_capital_ratio": data.total_capital_ratio,
                "cet1_amount": data.cet1_amount,
                "tier1_amount": data.tier1_amount,
                "total_capital_amount": data.total_capital_amount,
                "leverage_ratio": data.leverage_ratio,
                "risk_weighted_assets": data.risk_weighted_assets,
                "status": data.status,
            },
        ).mappings().first()
        return CrdCapitalPositionSummary(**dict(row))


@router.put("/capital-positions/{position_id}", response_model=CrdCapitalPositionSummary, operation_id="update_crd_capital_position")
async def update_crd_capital_position(position_id: int, data: CrdCapitalPositionUpdate):
    """Update a capital position record."""
    with db_session() as db:
        existing = db.execute(
            text("SELECT * FROM crd_capital_position WHERE id = :id"),
            {"id": position_id},
        ).mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Capital position not found")

        update_fields = []
        params: dict = {"id": position_id}
        for field in ["cet1_ratio", "tier1_ratio", "total_capital_ratio",
                       "cet1_amount", "tier1_amount", "total_capital_amount",
                       "leverage_ratio", "risk_weighted_assets", "status"]:
            value = getattr(data, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if update_fields:
            update_fields.append("created_at = CURRENT_TIMESTAMP")
            db.execute(
                text(f"UPDATE crd_capital_position SET {', '.join(update_fields)} WHERE id = :id"),
                params,
            )
            db.commit()

        row = db.execute(
            text("SELECT * FROM crd_capital_position WHERE id = :id"),
            {"id": position_id},
        ).mappings().first()
        return CrdCapitalPositionSummary(**dict(row))


# =============================================================================
# CRD — Stress Tests
# =============================================================================

@router.get("/stress-tests", response_model=CrdStressTestListResponse, operation_id="list_crd_stress_tests")
async def list_crd_stress_tests(
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    test_date: str | None = Query(None, description="Filter by test date (YYYY-MM-DD)"),
    status: str | None = Query(None, description="Filter by status"),
):
    """List stress test results for CRD."""
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("entity_id = :entity_id")
        params["entity_id"] = entity_id
    if test_date is not None:
        filters.append("test_date = :test_date")
        params["test_date"] = test_date
    if status is not None:
        filters.append("status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(f"SELECT * FROM crd_stress_test WHERE {' AND '.join(filters)} ORDER BY test_date DESC"),
            params,
        ).mappings().all()
        items = [CrdStressTestSummary(**dict(r)) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM crd_stress_test WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get("/stress-tests/{test_id}", response_model=CrdStressTestDetail, operation_id="get_crd_stress_test")
async def get_crd_stress_test(test_id: int):
    """Get a single stress test by ID."""
    with db_session() as db:
        row = db.execute(
            text("SELECT * FROM crd_stress_test WHERE id = :id"),
            {"id": test_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Stress test not found")
        return CrdStressTestDetail(**dict(row))


@router.post("/stress-tests", response_model=CrdStressTestSummary, status_code=201, operation_id="create_crd_stress_test")
async def create_crd_stress_test(data: CrdStressTestCreate):
    """Create a new stress test record."""
    with db_session() as db:
        row = db.execute(
            text(
                "INSERT INTO crd_stress_test "
                "(entity_id, test_date, scenario_name, cet1_impact_pct, tier1_impact_pct, "
                "capital_ratio_post_test, competent_authority, status, created_at) "
                "VALUES (:entity_id, :test_date, :scenario_name, :cet1_impact_pct, "
                ":tier1_impact_pct, :capital_ratio_post_test, :competent_authority, "
                ":status, CURRENT_TIMESTAMP) RETURNING *"
            ),
            {
                "entity_id": data.entity_id,
                "test_date": data.test_date,
                "scenario_name": data.scenario_name,
                "cet1_impact_pct": data.cet1_impact_pct,
                "tier1_impact_pct": data.tier1_impact_pct,
                "capital_ratio_post_test": data.capital_ratio_post_test,
                "competent_authority": data.competent_authority,
                "status": data.status,
            },
        ).mappings().first()
        return CrdStressTestSummary(**dict(row))


@router.put("/stress-tests/{test_id}", response_model=CrdStressTestSummary, operation_id="update_crd_stress_test")
async def update_crd_stress_test(test_id: int, data: CrdStressTestUpdate):
    """Update a stress test record."""
    with db_session() as db:
        existing = db.execute(
            text("SELECT * FROM crd_stress_test WHERE id = :id"),
            {"id": test_id},
        ).mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Stress test not found")

        update_fields = []
        params: dict = {"id": test_id}
        for field in ["scenario_name", "cet1_impact_pct", "tier1_impact_pct",
                       "capital_ratio_post_test", "competent_authority", "status"]:
            value = getattr(data, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if update_fields:
            update_fields.append("created_at = CURRENT_TIMESTAMP")
            db.execute(
                text(f"UPDATE crd_stress_test SET {', '.join(update_fields)} WHERE id = :id"),
                params,
            )
            db.commit()

        row = db.execute(
            text("SELECT * FROM crd_stress_test WHERE id = :id"),
            {"id": test_id},
        ).mappings().first()
        return CrdStressTestSummary(**dict(row))


# =============================================================================
# BRRD — Bail-In / MREL
# =============================================================================

@router.get("/bail-in", response_model=BrrdBailInListResponse, operation_id="list_brrd_bail_in")
async def list_brrd_bail_in(
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    status: str | None = Query(None, description="Filter by status"),
):
    """List bail-in / MREL records for BRRD."""
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("entity_id = :entity_id")
        params["entity_id"] = entity_id
    if status is not None:
        filters.append("status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(f"SELECT * FROM brrd_bail_in WHERE {' AND '.join(filters)} ORDER BY id DESC"),
            params,
        ).mappings().all()
        items = [BrrdBailInSummary(**dict(r)) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM brrd_bail_in WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get("/bail-in/{bail_in_id}", response_model=BrrdBailInDetail, operation_id="get_brrd_bail_in")
async def get_brrd_bail_in(bail_in_id: int):
    """Get a single bail-in record by ID."""
    with db_session() as db:
        row = db.execute(
            text("SELECT * FROM brrd_bail_in WHERE id = :id"),
            {"id": bail_in_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Bail-in record not found")
        return BrrdBailInDetail(**dict(row))


@router.post("/bail-in", response_model=BrrdBailInSummary, status_code=201, operation_id="create_brrd_bail_in")
async def create_brrd_bail_in(data: BrrdBailInCreate):
    """Create a new bail-in record."""
    with db_session() as db:
        row = db.execute(
            text(
                "INSERT INTO brrd_bail_in "
                "(entity_id, total_eligible_liabilities, mrel_target_pct, "
                "mrel_compliance_pct, internal_mrel, resolution_status, status, created_at) "
                "VALUES (:entity_id, :total_eligible_liabilities, :mrel_target_pct, "
                ":mrel_compliance_pct, :internal_mrel, :resolution_status, "
                ":status, CURRENT_TIMESTAMP) RETURNING *"
            ),
            {
                "entity_id": data.entity_id,
                "total_eligible_liabilities": data.total_eligible_liabilities,
                "mrel_target_pct": data.mrel_target_pct,
                "mrel_compliance_pct": data.mrel_compliance_pct,
                "internal_mrel": data.internal_mrel,
                "resolution_status": data.resolution_status,
                "status": data.status,
            },
        ).mappings().first()
        return BrrdBailInSummary(**dict(row))


@router.put("/bail-in/{bail_in_id}", response_model=BrrdBailInSummary, operation_id="update_brrd_bail_in")
async def update_brrd_bail_in(bail_in_id: int, data: BrrdBailInUpdate):
    """Update a bail-in record."""
    with db_session() as db:
        existing = db.execute(
            text("SELECT * FROM brrd_bail_in WHERE id = :id"),
            {"id": bail_in_id},
        ).mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Bail-in record not found")

        update_fields = []
        params: dict = {"id": bail_in_id}
        for field in ["total_eligible_liabilities", "mrel_target_pct", "mrel_compliance_pct",
                       "internal_mrel", "resolution_status", "status"]:
            value = getattr(data, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if update_fields:
            update_fields.append("created_at = CURRENT_TIMESTAMP")
            db.execute(
                text(f"UPDATE brrd_bail_in SET {', '.join(update_fields)} WHERE id = :id"),
                params,
            )
            db.commit()

        row = db.execute(
            text("SELECT * FROM brrd_bail_in WHERE id = :id"),
            {"id": bail_in_id},
        ).mappings().first()
        return BrrdBailInSummary(**dict(row))


# =============================================================================
# EMIR — Trade Reports
# =============================================================================

@ucits_router.get("/trade-reports", response_model=EmirTradeReportListResponse, operation_id="list_emir_trade_reports")
async def list_emir_trade_reports(
    asset_class: str | None = Query(None, description="Filter by asset class"),
    counterparty_type: str | None = Query(None, description="Filter by counterparty type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """List trade reports for EMIR."""
    filters = ["1=1"]
    params: dict = {}

    if asset_class is not None:
        filters.append("asset_class = :asset_class")
        params["asset_class"] = asset_class
    if counterparty_type is not None:
        filters.append("counterparty_type = :counterparty_type")
        params["counterparty_type"] = counterparty_type
    if status is not None:
        filters.append("status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(f"SELECT * FROM emir_trade_report WHERE {' AND '.join(filters)} ORDER BY id DESC"),
            params,
        ).mappings().all()
        items = [EmirTradeReportSummary(**dict(r)) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM emir_trade_report WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@ucits_router.get("/trade-reports/{trade_id}", response_model=EmirTradeReportDetail, operation_id="get_emir_trade_report")
async def get_emir_trade_report(trade_id: int):
    """Get a single trade report by ID."""
    with db_session() as db:
        row = db.execute(
            text("SELECT * FROM emir_trade_report WHERE id = :id"),
            {"id": trade_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Trade report not found")
        return EmirTradeReportDetail(**dict(row))


@ucits_router.post("/trade-reports", response_model=EmirTradeReportSummary, status_code=201, operation_id="create_emir_trade_report")
async def create_emir_trade_report(data: EmirTradeReportCreate):
    """Create a new trade report record."""
    with db_session() as db:
        row = db.execute(
            text(
                "INSERT INTO emir_trade_report "
                "(trade_id, asset_class, instrument_class, clearing_obligation_applied, "
                "reporting_delay_days, counterparty_type, status, created_at) "
                "VALUES (:trade_id, :asset_class, :instrument_class, "
                ":clearing_obligation_applied, :reporting_delay_days, "
                ":counterparty_type, :status, CURRENT_TIMESTAMP) RETURNING *"
            ),
            {
                "trade_id": data.trade_id,
                "asset_class": data.asset_class,
                "instrument_class": data.instrument_class,
                "clearing_obligation_applied": data.clearing_obligation_applied,
                "reporting_delay_days": data.reporting_delay_days,
                "counterparty_type": data.counterparty_type,
                "status": data.status,
            },
        ).mappings().first()
        return EmirTradeReportSummary(**dict(row))


@ucits_router.put("/trade-reports/{trade_id}", response_model=EmirTradeReportSummary, operation_id="update_emir_trade_report")
async def update_emir_trade_report(trade_id: int, data: EmirTradeReportUpdate):
    """Update a trade report record."""
    with db_session() as db:
        existing = db.execute(
            text("SELECT * FROM emir_trade_report WHERE id = :id"),
            {"id": trade_id},
        ).mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Trade report not found")

        update_fields = []
        params: dict = {"id": trade_id}
        for field in ["asset_class", "instrument_class", "clearing_obligation_applied",
                       "reporting_delay_days", "counterparty_type", "status"]:
            value = getattr(data, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if update_fields:
            update_fields.append("created_at = CURRENT_TIMESTAMP")
            db.execute(
                text(f"UPDATE emir_trade_report SET {', '.join(update_fields)} WHERE id = :id"),
                params,
            )
            db.commit()

        row = db.execute(
            text("SELECT * FROM emir_trade_report WHERE id = :id"),
            {"id": trade_id},
        ).mappings().first()
        return EmirTradeReportSummary(**dict(row))


# =============================================================================
# EMIR — Clearing Members
# =============================================================================

@ucits_router.get("/clearing-members", response_model=EmirClearingMemberListResponse, operation_id="list_emir_clearing_members")
async def list_emir_clearing_members(
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    clearing_type: str | None = Query(None, description="Filter by clearing type"),
    status: str | None = Query(None, description="Filter by status"),
):
    """List clearing members for EMIR."""
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("entity_id = :entity_id")
        params["entity_id"] = entity_id
    if clearing_type is not None:
        filters.append("clearing_type = :clearing_type")
        params["clearing_type"] = clearing_type
    if status is not None:
        filters.append("status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(f"SELECT * FROM emir_clearing_member WHERE {' AND '.join(filters)} ORDER BY id DESC"),
            params,
        ).mappings().all()
        items = [EmirClearingMemberSummary(**dict(r)) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM emir_clearing_member WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@ucits_router.get("/clearing-members/{member_id}", response_model=EmirClearingMemberDetail, operation_id="get_emir_clearing_member")
async def get_emir_clearing_member(member_id: int):
    """Get a single clearing member by ID."""
    with db_session() as db:
        row = db.execute(
            text("SELECT * FROM emir_clearing_member WHERE id = :id"),
            {"id": member_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Clearing member not found")
        return EmirClearingMemberDetail(**dict(row))


@ucits_router.post("/clearing-members", response_model=EmirClearingMemberSummary, status_code=201, operation_id="create_emir_clearing_member")
async def create_emir_clearing_member(data: EmirClearingMemberCreate):
    """Create a new clearing member record."""
    with db_session() as db:
        row = db.execute(
            text(
                "INSERT INTO emir_clearing_member "
                "(entity_id, emir_registration, clearing_type, status, created_at) "
                "VALUES (:entity_id, :emir_registration, :clearing_type, "
                ":status, CURRENT_TIMESTAMP) RETURNING *"
            ),
            {
                "entity_id": data.entity_id,
                "emir_registration": data.emir_registration,
                "clearing_type": data.clearing_type,
                "status": data.status,
            },
        ).mappings().first()
        return EmirClearingMemberSummary(**dict(row))


@ucits_router.put("/clearing-members/{member_id}", response_model=EmirClearingMemberSummary, operation_id="update_emir_clearing_member")
async def update_emir_clearing_member(member_id: int, data: EmirClearingMemberUpdate):
    """Update a clearing member record."""
    with db_session() as db:
        existing = db.execute(
            text("SELECT * FROM emir_clearing_member WHERE id = :id"),
            {"id": member_id},
        ).mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Clearing member not found")

        update_fields = []
        params: dict = {"id": member_id}
        for field in ["emir_registration", "clearing_type", "status"]:
            value = getattr(data, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if update_fields:
            update_fields.append("created_at = CURRENT_TIMESTAMP")
            db.execute(
                text(f"UPDATE emir_clearing_member SET {', '.join(update_fields)} WHERE id = :id"),
                params,
            )
            db.commit()

        row = db.execute(
            text("SELECT * FROM emir_clearing_member WHERE id = :id"),
            {"id": member_id},
        ).mappings().first()
        return EmirClearingMemberSummary(**dict(row))
