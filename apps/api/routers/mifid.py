"""MiFID II/MiFIR data model endpoints.

Fase 31.8 — Expansion regulatoria.

Endpoints:
    GET  /v1/mifid/client-categories              — list client categories
    GET  /v1/mifid/client-categories/{id}          — get client category by ID
    GET  /v1/mifid/suitability-reports             — list suitability reports
    GET  /v1/mifid/suitability-reports/{id}        — get suitability report by ID
    GET  /v1/mifid/best-execution-records          — list best execution records
    GET  /v1/mifid/best-execution-records/{id}     — get best execution record by ID
    GET  /v1/mifid/conflict-of-interest            — list conflicts of interest
    GET  /v1/mifid/conflict-of-interest/{id}       — get conflict of interest by ID
    GET  /v1/mifid/product-governance              — list product governance records
    GET  /v1/mifid/product-governance/{id}         — get product governance by ID
    GET  /v1/mifid/order-records                   — list order records
    GET  /v1/mifid/order-records/{id}              — get order record by ID
    GET  /v1/mifid/insider-lists                   — list insider lists
    GET  /v1/mifid/insider-lists/{id}              — get insider list by ID
    GET  /v1/mifid/compensation-policies           — list compensation policies
    GET  /v1/mifid/compensation-policies/{id}      — get compensation policy by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    MifidBestExecutionRecordDetail,
    MifidBestExecutionRecordListResponse,
    MifidClientCategoryDetail,
    MifidClientCategoryListResponse,
    MifidCompensationPolicyDetail,
    MifidCompensationPolicyListResponse,
    MifidConflictOfInterestDetail,
    MifidConflictOfInterestListResponse,
    MifidInsiderListDetail,
    MifidInsiderListResponse,
    MifidOrderRecordDetail,
    MifidOrderRecordListResponse,
    MifidProductGovernanceDetail,
    MifidProductGovernanceListResponse,
    MifidSuitabilityReportDetail,
    MifidSuitabilityReportListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/mifid", tags=["mifid"])


def _as_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ===========================================================================
# Client Categories
# ===========================================================================


@router.get(
    "/client-categories",
    response_model=MifidClientCategoryListResponse,
    operation_id="list_mifid_client_categories",
)
async def list_mifid_client_categories(
    status: str | None = Query(None, description="Filtrar por estado"),
    category: str | None = Query(None, description="Filtrar por categoria: retail, professional, eligible_counterparty"),
    search: str | None = Query(None, description="Buscar por entity_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mc.status = :status")
        params["status"] = status
    if category:
        filters.append("mc.category = :category")
        params["category"] = category
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("mc.entity_id = :search")
            params["search"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, category, assessment_date, status
                FROM mifid_client_category mc
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
                SELECT COUNT(*) FROM mifid_client_category mc
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/client-categories/{item_id}",
    response_model=MifidClientCategoryDetail,
    operation_id="get_mifid_client_category",
)
async def get_mifid_client_category(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, category, assessment_date, status,
                       knowledge_level, experience_level, created_at
                FROM mifid_client_category mc
                WHERE mc.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Suitability Reports
# ===========================================================================


@router.get(
    "/suitability-reports",
    response_model=MifidSuitabilityReportListResponse,
    operation_id="list_mifid_suitability_reports",
)
async def list_mifid_suitability_reports(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por client_id o product_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("ms.status = :status")
        params["status"] = status
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("(ms.client_id = :search OR ms.product_id = :search2)")
            params["search"] = search_int
            params["search2"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, client_id, product_id, assessment_date,
                        suitability_score, recommendation, status
                FROM mifid_suitability_report ms
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
                SELECT COUNT(*) FROM mifid_suitability_report ms
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/suitability-reports/{item_id}",
    response_model=MifidSuitabilityReportDetail,
    operation_id="get_mifid_suitability_report",
)
async def get_mifid_suitability_report(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, client_id, product_id, assessment_date,
                       suitability_score, status, recommendation, advisor_id, created_at
                FROM mifid_suitability_report ms
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
# Best Execution Records
# ===========================================================================


@router.get(
    "/best-execution-records",
    response_model=MifidBestExecutionRecordListResponse,
    operation_id="list_mifid_best_execution_records",
)
async def list_mifid_best_execution_records(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por order_id o venue"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mb.status = :status")
        params["status"] = status
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append(
                "(mb.order_id = :search OR LOWER(mb.venue) LIKE LOWER(:search_like))"
            )
            params["search"] = search_int
        else:
            filters.append("LOWER(mb.venue) LIKE LOWER(:search_like)")
        params["search_like"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, order_id, venue, execution_price, status
                FROM mifid_best_execution_record mb
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
                SELECT COUNT(*) FROM mifid_best_execution_record mb
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/best-execution-records/{item_id}",
    response_model=MifidBestExecutionRecordDetail,
    operation_id="get_mifid_best_execution_record",
)
async def get_mifid_best_execution_record(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, order_id, venue, execution_price, status,
                       market_impact, speed_ms, quality_metrics,
                       execution_timestamp, created_at
                FROM mifid_best_execution_record mb
                WHERE mb.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Conflict of Interest
# ===========================================================================


@router.get(
    "/conflict-of-interest",
    response_model=MifidConflictOfInterestListResponse,
    operation_id="list_mifid_conflicts_of_interest",
)
async def list_mifid_conflicts_of_interest(
    status: str | None = Query(None, description="Filtrar por estado"),
    conflict_type: str | None = Query(None, description="Filtrar por tipo de conflicto"),
    search: str | None = Query(None, description="Buscar por department"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mc.status = :status")
        params["status"] = status
    if conflict_type:
        filters.append("mc.conflict_type = :conflict_type")
        params["conflict_type"] = conflict_type
    if search:
        filters.append("LOWER(mc.department) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, department, conflict_type, status
                FROM mifid_conflict_of_interest_registry mc
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
                SELECT COUNT(*) FROM mifid_conflict_of_interest_registry mc
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/conflict-of-interest/{item_id}",
    response_model=MifidConflictOfInterestDetail,
    operation_id="get_mifid_conflict_of_interest",
)
async def get_mifid_conflict_of_interest(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, department, conflict_type, status,
                       description, mitigation_measure,
                       identified_date, review_date, created_at
                FROM mifid_conflict_of_interest_registry mc
                WHERE mc.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Product Governance
# ===========================================================================


@router.get(
    "/product-governance",
    response_model=MifidProductGovernanceListResponse,
    operation_id="list_mifid_product_governance",
)
async def list_mifid_product_governance(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por product_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mg.status = :status")
        params["status"] = status
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("mg.product_id = :search")
            params["search"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_id, target_market, risk_level, status
                FROM mifid_product_governance mg
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
                SELECT COUNT(*) FROM mifid_product_governance mg
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/product-governance/{item_id}",
    response_model=MifidProductGovernanceDetail,
    operation_id="get_mifid_product_governance",
)
async def get_mifid_product_governance(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, product_id, target_market, risk_level, status,
                       distribution_channels, key_features, review_date, created_at
                FROM mifid_product_governance mg
                WHERE mg.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Order Records
# ===========================================================================


@router.get(
    "/order-records",
    response_model=MifidOrderRecordListResponse,
    operation_id="list_mifid_order_records",
)
async def list_mifid_order_records(
    status: str | None = Query(None, description="Filtrar por estado"),
    direction: str | None = Query(None, description="Filtrar por direccion: buy, sell"),
    search: str | None = Query(None, description="Buscar por client_id o instrument"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mo.status = :status")
        params["status"] = status
    if direction:
        filters.append("mo.direction = :direction")
        params["direction"] = direction
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append(
                "(mo.client_id = :search OR LOWER(mo.instrument) LIKE LOWER(:search_like))"
            )
            params["search"] = search_int
        else:
            filters.append("LOWER(mo.instrument) LIKE LOWER(:search_like)")
        params["search_like"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, client_id, instrument, direction, quantity, price, status
                FROM mifid_order_record mo
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
                SELECT COUNT(*) FROM mifid_order_record mo
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/order-records/{item_id}",
    response_model=MifidOrderRecordDetail,
    operation_id="get_mifid_order_record",
)
async def get_mifid_order_record(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, client_id, instrument, direction, quantity, price, status,
                       timestamp, venue, retention_until, created_at
                FROM mifid_order_record mo
                WHERE mo.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Insider Lists
# ===========================================================================


@router.get(
    "/insider-lists",
    response_model=MifidInsiderListResponse,
    operation_id="list_mifid_insider_lists",
)
async def list_mifid_insider_lists(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por insider_name o inside_information_description"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mi.status = :status")
        params["status"] = status
    if search:
        filters.append(
            "(LOWER(mi.insider_name) LIKE LOWER(:search) OR LOWER(mi.inside_information_description) LIKE LOWER(:search))"
        )
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, insider_name, entity_id, inside_information_description, status
                FROM mifid_insider_list mi
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
                SELECT COUNT(*) FROM mifid_insider_list mi
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/insider-lists/{item_id}",
    response_model=MifidInsiderListDetail,
    operation_id="get_mifid_insider_list",
)
async def get_mifid_insider_list(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, insider_name, entity_id, inside_information_description, status,
                       insider_tin, date_created, date_removed, created_at
                FROM mifid_insider_list mi
                WHERE mi.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Compensation Policies
# ===========================================================================


@router.get(
    "/compensation-policies",
    response_model=MifidCompensationPolicyListResponse,
    operation_id="list_mifid_compensation_policies",
)
async def list_mifid_compensation_policies(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por entity_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mp.status = :status")
        params["status"] = status
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("mp.entity_id = :search")
            params["search"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, policy_version, alignment_score, status
                FROM mifid_compensation_policy mp
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
                SELECT COUNT(*) FROM mifid_compensation_policy mp
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/compensation-policies/{item_id}",
    response_model=MifidCompensationPolicyDetail,
    operation_id="get_mifid_compensation_policy",
)
async def get_mifid_compensation_policy(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, policy_version, alignment_score, status,
                       risk_adjustment_applied, approval_date, next_review, created_at
                FROM mifid_compensation_policy mp
                WHERE mp.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)
