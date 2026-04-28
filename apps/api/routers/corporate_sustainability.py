"""CSRD (Corporate Sustainability Reporting Directive) data model endpoints.

Fase 31.9.2 -- Expansion regulatoria: CSRD.

Endpoints:
    GET  /v1/csrd/entity-reports              -- list CSRD entity reports
    GET  /v1/csrd/entity-reports/{id}         -- get report by ID
    GET  /v1/csrd/esg-data-points             -- list ESG data points
    GET  /v1/csrd/esg-data-points/{id}        -- get data point by ID
    GET  /v1/csrd/ess                         -- list ES standards
    GET  /v1/csrd/ess/{id}                    -- get standard by ID
    GET  /v1/csrd/double-materiality          -- list double materiality assessments
    GET  /v1/csrd/double-materiality/{id}     -- get assessment by ID
"""

import contextlib
import json

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    CsrdDoubleMaterialityDetail,
    CsrdDoubleMaterialityListResponse,
    CsrdEntityReportDetail,
    CsrdEntityReportListResponse,
    CsrdEsgDataPointDetail,
    CsrdEsgDataPointListResponse,
    CsrdEssDetail,
    CsrdEssListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/csrd", tags=["csrd"])


def _parse_json(row: dict, *keys: str) -> dict:
    """Parse JSON columns in row."""
    for key in keys:
        val = row.get(key)
        if val and isinstance(val, str):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                row[key] = json.loads(val)
    return row


# ===========================================================================
# Entity Reports
# ===========================================================================


@router.get(
    "/entity-reports",
    response_model=CsrdEntityReportListResponse,
    operation_id="list_csrd_entity_reports",
)
async def list_csrd_entity_reports(
    entity_id: int | None = Query(None, description="Filtrar por entidad"),
    reporting_year: int | None = Query(None, description="Filtrar por ano de reporte"),
    assurance_status: str | None = Query(None, description="Filtrar por estado de aseguramiento"),
    status: str | None = Query(None, description="Filtrar por estado: draft, published"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id:
        filters.append("cer.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if reporting_year:
        filters.append("cer.reporting_year = :reporting_year")
        params["reporting_year"] = reporting_year
    if assurance_status:
        filters.append("cer.assurance_status = :assurance_status")
        params["assurance_status"] = assurance_status
    if status:
        filters.append("cer.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, reporting_year, esap_url,
                       assurance_status, reporting_standard, status
                FROM csrd_entity_report cer
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
                SELECT COUNT(*) FROM csrd_entity_report cer
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/entity-reports/{item_id}",
    response_model=CsrdEntityReportDetail,
    operation_id="get_csrd_entity_report",
)
async def get_csrd_entity_report(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, reporting_year, esap_url,
                       assurance_status, reporting_standard, status, created_at
                FROM csrd_entity_report cer
                WHERE cer.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Informe CSRD no encontrado"})
        return dict(row)


# ===========================================================================
# ESG Data Points
# ===========================================================================


@router.get(
    "/esg-data-points",
    response_model=CsrdEsgDataPointListResponse,
    operation_id="list_csrd_esg_data_points",
)
async def list_csrd_esg_data_points(
    report_id: int | None = Query(None, description="Filtrar por informe"),
    topic: str | None = Query(None, description="Filtrar por tema: environment, social, governance"),
    verification_status: str | None = Query(None, description="Filtrar por estado de verificacion"),
):
    filters = ["1=1"]
    params: dict = {}

    if report_id:
        filters.append("ced.report_id = :report_id")
        params["report_id"] = report_id
    if topic:
        filters.append("ced.topic = :topic")
        params["topic"] = topic
    if verification_status:
        filters.append("ced.verification_status = :verification_status")
        params["verification_status"] = verification_status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, report_id, topic, indicator_code,
                       value, unit, scope, verification_status
                FROM csrd_esg_data_point ced
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
                SELECT COUNT(*) FROM csrd_esg_data_point ced
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/esg-data-points/{item_id}",
    response_model=CsrdEsgDataPointDetail,
    operation_id="get_csrd_esg_data_point",
)
async def get_csrd_esg_data_point(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, report_id, topic, indicator_code, value,
                       unit, scope, verification_status, created_at
                FROM csrd_esg_data_point ced
                WHERE ced.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Dato ESG CSRD no encontrado"})
        return dict(row)


# ===========================================================================
# ES Standards
# ===========================================================================


@router.get(
    "/ess",
    response_model=CsrdEssListResponse,
    operation_id="list_csrd_ess",
)
async def list_csrd_ess(
    topic: str | None = Query(None, description="Filtrar por tema"),
    status: str | None = Query(None, description="Filtrar por estado"),
):
    filters = ["1=1"]
    params: dict = {}

    if topic:
        filters.append("ce.topic = :topic")
        params["topic"] = topic
    if status:
        filters.append("ce.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, standard_code, topic, applicable_from_year,
                       description, status
                FROM csrd_ess ce
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
                SELECT COUNT(*) FROM csrd_ess ce
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/ess/{item_id}",
    response_model=CsrdEssDetail,
    operation_id="get_csrd_ess",
)
async def get_csrd_ess(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, standard_code, topic, applicable_from_year,
                       description, status, created_at
                FROM csrd_ess ce
                WHERE ce.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Estandar ESRS no encontrado"})
        return dict(row)


# ===========================================================================
# Double Materiality
# ===========================================================================


@router.get(
    "/double-materiality",
    response_model=CsrdDoubleMaterialityListResponse,
    operation_id="list_csrd_double_materiality",
)
async def list_csrd_double_materiality(
    entity_id: int | None = Query(None, description="Filtrar por entidad"),
    status: str | None = Query(None, description="Filtrar por estado: draft, published"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id:
        filters.append("cdm.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if status:
        filters.append("cdm.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, impact_materiality,
                       financial_materiality, assessment_date,
                       key_impacts, key_dependencies, status
                FROM csrd_double_materiality cdm
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [_parse_json(dict(r), "impact_materiality", "financial_materiality") for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM csrd_double_materiality cdm
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/double-materiality/{item_id}",
    response_model=CsrdDoubleMaterialityDetail,
    operation_id="get_csrd_double_materiality",
)
async def get_csrd_double_materiality(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, impact_materiality,
                       financial_materiality, assessment_date,
                       key_impacts, key_dependencies, status, created_at
                FROM csrd_double_materiality cdm
                WHERE cdm.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Evaluacion doble materialidad CSRD no encontrada"})
        return _parse_json(dict(row), "impact_materiality", "financial_materiality")
