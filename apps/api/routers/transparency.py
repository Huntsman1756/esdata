"""Transparency data model endpoints.

Fase 31.8 — Expansion regulatoria.

Endpoints:
    GET  /v1/transparency/issuers             — list issuers
    GET  /v1/transparency/issuers/{id}        — get issuer by ID
    GET  /v1/transparency/regulated-info       — list regulated information
    GET  /v1/transparency/regulated-info/{id}  — get regulated info by ID
    GET  /v1/transparency/voting-rights        — list voting rights
    GET  /v1/transparency/voting-rights/{id}  — get voting rights by ID
    GET  /v1/transparency/internal-rules       — list internal rules
    GET  /v1/transparency/internal-rules/{id}  — get internal rule by ID
"""

import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    TransparencyInternalRuleDetail,
    TransparencyInternalRuleListResponse,
    TransparencyIssuerDetail,
    TransparencyIssuerListResponse,
    TransparencyRegulatedInfoDetail,
    TransparencyRegulatedInfoListResponse,
    TransparencyVotingRightsDetail,
    TransparencyVotingRightsListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/transparency", tags=["transparency"])


def _parse_internal_rule_row(row):
    """Parse JSON columns in internal rule rows."""
    import contextlib

    d = dict(row)
    if d.get("designated_persons") and isinstance(d["designated_persons"], str):
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            d["designated_persons"] = json.loads(d["designated_persons"])
    return d


# ===========================================================================
# Issuers
# ===========================================================================


@router.get(
    "/issuers",
    response_model=TransparencyIssuerListResponse,
    operation_id="list_transparency_issuers",
)
async def list_transparency_issuers(
    status: str | None = Query(None, description="Filtrar por estado"),
    listing_market: str | None = Query(None, description="Filtrar por mercado de listado"),
    search: str | None = Query(None, description="Buscar por ticker o issuer_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("ti.status = :status")
        params["status"] = status
    if listing_market:
        filters.append("ti.listing_market = :listing_market")
        params["listing_market"] = listing_market
    if search:
        filters.append(
            "(LOWER(ti.ticker) LIKE LOWER(:search) OR ti.issuer_id = CAST(:search2 AS INTEGER))"
        )
        params["search"] = f"%{search}%"
        params["search2"] = search

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, issuer_id, ticker, listing_market, status
                FROM transparency_issuer ti
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
                SELECT COUNT(*) FROM transparency_issuer ti
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/issuers/{item_id}",
    response_model=TransparencyIssuerDetail,
    operation_id="get_transparency_issuer",
)
async def get_transparency_issuer(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, issuer_id, ticker, listing_market, status,
                       reporting_frequency, home_member_state, created_at
                FROM transparency_issuer ti
                WHERE ti.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Regulated Information
# ===========================================================================


@router.get(
    "/regulated-info",
    response_model=TransparencyRegulatedInfoListResponse,
    operation_id="list_transparency_regulated_info",
)
async def list_transparency_regulated_info(
    status: str | None = Query(None, description="Filtrar por estado"),
    info_type: str | None = Query(None, description="Filtrar por tipo de informacion"),
    search: str | None = Query(None, description="Buscar por issuer_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("tr.status = :status")
        params["status"] = status
    if info_type:
        filters.append("tr.info_type = :info_type")
        params["info_type"] = info_type
    if search:
        filters.append("tr.issuer_id = :search::integer")
        params["search"] = search

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, issuer_id, info_type, publication_date, filing_reference, status
                FROM transparency_regulated_information tr
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
                SELECT COUNT(*) FROM transparency_regulated_information tr
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/regulated-info/{item_id}",
    response_model=TransparencyRegulatedInfoDetail,
    operation_id="get_transparency_regulated_info",
)
async def get_transparency_regulated_info(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, issuer_id, info_type, publication_date, status,
                       content_url, filing_reference, created_at
                FROM transparency_regulated_information tr
                WHERE tr.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Voting Rights
# ===========================================================================


@router.get(
    "/voting-rights",
    response_model=TransparencyVotingRightsListResponse,
    operation_id="list_transparency_voting_rights",
)
async def list_transparency_voting_rights(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por issuer_id o shareholder_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("tv.status = :status")
        params["status"] = status
    if search:
        filters.append(
            "(tv.issuer_id = :search::integer OR tv.shareholder_id = :search2::integer)"
        )
        params["search"] = search
        params["search2"] = search

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, issuer_id, shareholder_id, voting_rights_pct, date_acquired, status
                FROM transparency_voting_rights tv
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
                SELECT COUNT(*) FROM transparency_voting_rights tv
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/voting-rights/{item_id}",
    response_model=TransparencyVotingRightsDetail,
    operation_id="get_transparency_voting_rights",
)
async def get_transparency_voting_rights(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, issuer_id, shareholder_id, voting_rights_pct, date_acquired, status,
                       date_reported, created_at
                FROM transparency_voting_rights tv
                WHERE tv.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Internal Rules
# ===========================================================================


@router.get(
    "/internal-rules",
    response_model=TransparencyInternalRuleListResponse,
    operation_id="list_transparency_internal_rules",
)
async def list_transparency_internal_rules(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por entity_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("tr.status = :status")
        params["status"] = status
    if search:
        filters.append("tr.entity_id = CAST(:search AS INTEGER)")
        params["search"] = search

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, designated_persons, internal_procedure, retention_period, status
                FROM transparency_internal_rule tr
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [_parse_internal_rule_row(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM transparency_internal_rule tr
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/internal-rules/{item_id}",
    response_model=TransparencyInternalRuleDetail,
    operation_id="get_transparency_internal_rule",
)
async def get_transparency_internal_rule(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, designated_persons, status,
                       internal_procedure, retention_period, created_at
                FROM transparency_internal_rule tr
                WHERE tr.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return _parse_internal_rule_row(row)
