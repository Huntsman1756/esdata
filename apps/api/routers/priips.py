"""PRIIPs / LIVMC data model endpoints.

Fase 31.8 — Expansion regulatoria.

Endpoints:
    GET  /v1/priips/kids                     — list KID documents
    GET  /v1/priips/kids/{id}                — get KID by ID
    GET  /v1/priips/products                  — list PRIIPs products
    GET  /v1/priips/products/{id}             — get product by ID
    GET  /v1/priips/client-protections        — list client protections (LIVMC)
    GET  /v1/priips/client-protections/{id}  — get client protection by ID
    GET  /v1/priips/voice-procedures          — list voice procedures (LIVMC)
    GET  /v1/priips/voice-procedures/{id}     — get voice procedure by ID
"""

import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    LivmcClientProtectionDetail,
    LivmcClientProtectionListResponse,
    LivmcVoiceProcedureDetail,
    LivmcVoiceProcedureListResponse,
    PriipsKidDetail,
    PriipsKidListResponse,
    PriipsProductDetail,
    PriipsProductListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/priips", tags=["priips"])


def _as_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_priips_kid_row(row):
    """Parse JSON columns in KID rows."""
    import contextlib

    d = dict(row)
    for k in ("cost_impact", "negative_scenario_returns"):
        if d.get(k) and isinstance(d[k], str):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                d[k] = json.loads(d[k])
    return d


# ===========================================================================
# KID Documents (PRIIPs)
# ===========================================================================


@router.get(
    "/kids",
    response_model=PriipsKidListResponse,
    operation_id="list_priips_kids",
)
async def list_priips_kids(
    status: str | None = Query(None, description="Filtrar por estado"),
    product_type: str | None = Query(None, description="Filtrar por tipo de producto"),
    search: str | None = Query(None, description="Buscar por product_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mk.status = :status")
        params["status"] = status
    if product_type:
        filters.append("mk.product_type = :product_type")
        params["product_type"] = product_type
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("mk.product_id = :search")
            params["search"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_id, product_type, risk_scale, cost_impact, status
                FROM priips_kid mk
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [_parse_priips_kid_row(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM priips_kid mk
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/kids/{item_id}",
    response_model=PriipsKidDetail,
    operation_id="get_priips_kid",
)
async def get_priips_kid(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, product_id, product_type, risk_scale, status,
                       currency, cost_impact, negative_scenario_returns,
                       version, publication_date, created_at
                 FROM priips_kid mk
                 WHERE mk.id = :item_id
                 LIMIT 1
                 """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return _parse_priips_kid_row(row)


# ===========================================================================
# PRIIPs Products
# ===========================================================================


@router.get(
    "/products",
    response_model=PriipsProductListResponse,
    operation_id="list_priips_products",
)
async def list_priips_products(
    status: str | None = Query(None, description="Filtrar por estado"),
    currency: str | None = Query(None, description="Filtrar por moneda"),
    search: str | None = Query(None, description="Buscar por product_name o issuer_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mp.status = :status")
        params["status"] = status
    if currency:
        filters.append("mp.currency = :currency")
        params["currency"] = currency
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append(
                "(LOWER(mp.product_name) LIKE LOWER(:search) OR mp.issuer_id = :search2)"
            )
            params["search2"] = search_int
        else:
            filters.append("LOWER(mp.product_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_name, currency, status
                FROM priips_product mp
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
                SELECT COUNT(*) FROM priips_product mp
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/products/{item_id}",
    response_model=PriipsProductDetail,
    operation_id="get_priips_product",
)
async def get_priips_product(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, issuer_id, product_name, currency, status,
                       underlying_assets, maturity_date, min_investment,
                       distribution_channels, created_at
                FROM priips_product mp
                WHERE mp.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Client Protections (LIVMC)
# ===========================================================================


@router.get(
    "/client-protections",
    response_model=LivmcClientProtectionListResponse,
    operation_id="list_livmc_client_protections",
)
async def list_livmc_client_protections(
    status: str | None = Query(None, description="Filtrar por estado"),
    protection_type: str | None = Query(None, description="Filtrar por tipo de proteccion"),
    search: str | None = Query(None, description="Buscar por client_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("ml.status = :status")
        params["status"] = status
    if protection_type:
        filters.append("ml.protection_type = :protection_type")
        params["protection_type"] = protection_type
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("ml.client_id = :search")
            params["search"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, client_id, protection_type, coverage_amount, status
                FROM livmc_client_protection ml
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
                SELECT COUNT(*) FROM livmc_client_protection ml
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/client-protections/{item_id}",
    response_model=LivmcClientProtectionDetail,
    operation_id="get_livmc_client_protection",
)
async def get_livmc_client_protection(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, client_id, protection_type, coverage_amount, status,
                       provider_id, created_at
                FROM livmc_client_protection ml
                WHERE ml.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Voice Procedures (LIVMC)
# ===========================================================================


@router.get(
    "/voice-procedures",
    response_model=LivmcVoiceProcedureListResponse,
    operation_id="list_livmc_voice_procedures",
)
async def list_livmc_voice_procedures(
    status: str | None = Query(None, description="Filtrar por estado"),
    procedure_type: str | None = Query(None, description="Filtrar por tipo de procedimiento"),
    search: str | None = Query(None, description="Buscar por entity_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mv.status = :status")
        params["status"] = status
    if procedure_type:
        filters.append("mv.procedure_type = :procedure_type")
        params["procedure_type"] = procedure_type
    if search:
        search_int = _as_int(search)
        if search_int is not None:
            filters.append("mv.entity_id = :search")
            params["search"] = search_int
        else:
            return {"items": [], "total": 0}

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, procedure_type, description, effective_date, status
                FROM livmc_voice_procedure mv
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
                SELECT COUNT(*) FROM livmc_voice_procedure mv
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/voice-procedures/{item_id}",
    response_model=LivmcVoiceProcedureDetail,
    operation_id="get_livmc_voice_procedure",
)
async def get_livmc_voice_procedure(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, procedure_type, effective_date, status,
                       description, next_review, created_at
                FROM livmc_voice_procedure mv
                WHERE mv.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)
