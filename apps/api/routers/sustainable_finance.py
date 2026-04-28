"""SFDR (Sustainable Finance Disclosure Regulation) data model endpoints.

Fase 31.9.1 — Expansion regulatoria: SFDR.

Endpoints:
    GET  /v1/sfdr/products                  — list SFDR products
    GET  /v1/sfdr/products/{id}             — get product by ID
    GET  /v1/sfdr/pacai-indicators          — list PCAI indicators
    GET  /v1/sfdr/pacai-indicators/{id}     — get indicator by ID
    GET  /v1/sfdr/entity-paci               — list entity PCAI
    GET  /v1/sfdr/entity-paci/{id}          — get entity PCAI by ID
    GET  /v1/sfdr/pre-contractual           — list pre-contractual docs
    GET  /v1/sfdr/pre-contractual/{id}      — get doc by ID
    GET  /v1/sfdr/annual-reports            — list annual reports
    GET  /v1/sfdr/annual-reports/{id}       — get report by ID
"""

import contextlib
import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    SfdrAnnualReportDetail,
    SfdrAnnualReportListResponse,
    SfdrEntityPaciDetail,
    SfdrEntityPaciListResponse,
    SfdrPaciiIndicatorDetail,
    SfdrPaciiIndicatorListResponse,
    SfdrPreContractualDetail,
    SfdrPreContractualListResponse,
    SfdrProductDetail,
    SfdrProductListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/sfdr", tags=["sfdr"])


def _parse_json(row: dict, *keys: str) -> dict:
    """Parse JSON columns in row."""
    for key in keys:
        val = row.get(key)
        if val and isinstance(val, str):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                row[key] = json.loads(val)
    return row


# ===========================================================================
# Products
# ===========================================================================


@router.get(
    "/products",
    response_model=SfdrProductListResponse,
    operation_id="list_sfdr_products",
)
async def list_sfdr_products(
    product_type: str | None = Query(None, description="Filtrar por tipo: art-6, art-8, art-9, other"),
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por nombre de producto"),
):
    filters = ["1=1"]
    params: dict = {}

    if product_type:
        filters.append("sp.product_type = :product_type")
        params["product_type"] = product_type
    if status:
        filters.append("sp.status = :status")
        params["status"] = status
    if search:
        filters.append("LOWER(sp.product_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_name, product_type, sustainability_strategy,
                       principal_adverse_impact, paci_aggregated, distribution_country, status
                FROM sfdr_product sp
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [_parse_json(dict(r), "paci_aggregated", "distribution_country") for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM sfdr_product sp
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/products/{item_id}",
    response_model=SfdrProductDetail,
    operation_id="get_sfdr_product",
)
async def get_sfdr_product(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, product_name, product_type, sustainability_strategy,
                       principal_adverse_impact, paci_aggregated, paci_detailed_url,
                       distribution_country, status, created_at
                FROM sfdr_product sp
                WHERE sp.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Producto SFDR no encontrado"})
        return _parse_json(dict(row), "paci_aggregated", "distribution_country")


# ===========================================================================
# PCAI Indicators
# ===========================================================================


@router.get(
    "/pacai-indicators",
    response_model=SfdrPaciiIndicatorListResponse,
    operation_id="list_sfdr_pacai_indicators",
)
async def list_sfdr_pacai_indicators(
    product_id: int | None = Query(None, description="Filtrar por producto"),
    indicator_code: str | None = Query(None, description="Filtrar por codigo indicador"),
    status: str | None = Query(None, description="Filtrar por estado"),
):
    filters = ["1=1"]
    params: dict = {}

    if product_id:
        filters.append("spi.product_id = :product_id")
        params["product_id"] = product_id
    if indicator_code:
        filters.append("spi.indicator_code = :indicator_code")
        params["indicator_code"] = indicator_code
    if status:
        filters.append("spi.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_id, indicator_code, indicator_name,
                       value, unit, reference_period, status
                FROM sfdr_paci_indicator spi
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
                SELECT COUNT(*) FROM sfdr_paci_indicator spi
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/pacai-indicators/{item_id}",
    response_model=SfdrPaciiIndicatorDetail,
    operation_id="get_sfdr_pacai_indicator",
)
async def get_sfdr_pacai_indicator(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, product_id, indicator_code, indicator_name, value,
                       unit, reference_period, methodology, status, created_at
                FROM sfdr_paci_indicator spi
                WHERE spi.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Indicador PCAI SFDR no encontrado"})
        return dict(row)


# ===========================================================================
# Entity PCAI
# ===========================================================================


@router.get(
    "/entity-paci",
    response_model=SfdrEntityPaciListResponse,
    operation_id="list_sfdr_entity_paci",
)
async def list_sfdr_entity_paci(
    entity_id: int | None = Query(None, description="Filtrar por entidad"),
    reporting_year: int | None = Query(None, description="Filtrar por ano de reporte"),
    status: str | None = Query(None, description="Filtrar por estado: draft, published"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id:
        filters.append("sep.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if reporting_year:
        filters.append("sep.reporting_year = :reporting_year")
        params["reporting_year"] = reporting_year
    if status:
        filters.append("sep.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, reporting_year, aggregated_paci,
                       sectoral_decarbonization, status
                FROM sfdr_entity_paci sep
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [_parse_json(dict(r), "aggregated_paci", "sectoral_decarbonization") for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM sfdr_entity_paci sep
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/entity-paci/{item_id}",
    response_model=SfdrEntityPaciDetail,
    operation_id="get_sfdr_entity_paci",
)
async def get_sfdr_entity_paci(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, reporting_year, aggregated_paci,
                       sectoral_decarbonization, status, created_at
                FROM sfdr_entity_paci sep
                WHERE sep.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "PCAI entidad SFDR no encontrado"})
        return _parse_json(dict(row), "aggregated_paci", "sectoral_decarbonization")


# ===========================================================================
# Pre-contractual Documents
# ===========================================================================


@router.get(
    "/pre-contractual",
    response_model=SfdrPreContractualListResponse,
    operation_id="list_sfdr_pre_contractual",
)
async def list_sfdr_pre_contractual(
    product_id: int | None = Query(None, description="Filtrar por producto"),
    document_type: str | None = Query(None, description="Filtrar por tipo: KID, PPI, prospectus"),
    status: str | None = Query(None, description="Filtrar por estado"),
):
    filters = ["1=1"]
    params: dict = {}

    if product_id:
        filters.append("spc.product_id = :product_id")
        params["product_id"] = product_id
    if document_type:
        filters.append("spc.document_type = :document_type")
        params["document_type"] = document_type
    if status:
        filters.append("spc.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_id, document_type, url, published_date, version, status
                FROM sfdr_pre_contractual spc
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
                SELECT COUNT(*) FROM sfdr_pre_contractual spc
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/pre-contractual/{item_id}",
    response_model=SfdrPreContractualDetail,
    operation_id="get_sfdr_pre_contractual",
)
async def get_sfdr_pre_contractual(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, product_id, document_type, url, published_date, version, status, created_at
                FROM sfdr_pre_contractual spc
                WHERE spc.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Documento precontractual SFDR no encontrado"})
        return dict(row)


# ===========================================================================
# Annual Reports
# ===========================================================================


@router.get(
    "/annual-reports",
    response_model=SfdrAnnualReportListResponse,
    operation_id="list_sfdr_annual_reports",
)
async def list_sfdr_annual_reports(
    entity_id: int | None = Query(None, description="Filtrar por entidad"),
    reporting_year: int | None = Query(None, description="Filtrar por ano de reporte"),
    status: str | None = Query(None, description="Filtrar por estado: draft, published"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id:
        filters.append("sar.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if reporting_year:
        filters.append("sar.reporting_year = :reporting_year")
        params["reporting_year"] = reporting_year
    if status:
        filters.append("sar.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, reporting_year, paci_results,
                       engagement_activities, good_practice_examples, url, published_date, status
                FROM sfdr_annual_report sar
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [_parse_json(dict(r), "paci_results", "engagement_activities") for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM sfdr_annual_report sar
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/annual-reports/{item_id}",
    response_model=SfdrAnnualReportDetail,
    operation_id="get_sfdr_annual_report",
)
async def get_sfdr_annual_report(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, reporting_year, paci_results,
                       engagement_activities, good_practice_examples, url, published_date, status, created_at
                FROM sfdr_annual_report sar
                WHERE sar.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Informe anual SFDR no encontrado"})
        return _parse_json(dict(row), "paci_results", "engagement_activities")
