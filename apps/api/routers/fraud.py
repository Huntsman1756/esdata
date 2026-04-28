"""Ley 11/2021 Antifraude endpoints.

Fase 31 — Expansion regulatoria.

Endpoints:
    GET  /v1/fraud/programs                      — list fraud prevention programs
    GET  /v1/fraud/programs/{id}                 — get program by ID
    GET  /v1/fraud/risk-assessments              — list risk assessments
    GET  /v1/fraud/risk-assessments/{id}         — get assessment by ID
    GET  /v1/fraud/incidents                     — list fraud incidents
    GET  /v1/fraud/incidents/{id}                — get incident by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    FraudIncidentDetail,
    FraudIncidentListResponse,
    FraudPreventionProgramDetail,
    FraudPreventionProgramListResponse,
    FraudRiskAssessmentDetail,
    FraudRiskAssessmentListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/fraud", tags=["fraud"])


# ===========================================================================
# Fraud Prevention Programs
# ===========================================================================


@router.get(
    "/programs",
    response_model=FraudPreventionProgramListResponse,
    operation_id="list_fraud_prevention_programs",
)
async def list_fraud_prevention_programs(
    entity_id: int | None = Query(None, description="Filtrar por ID de la entidad"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive, suspended"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("fp.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if status:
        filters.append("fp.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, code_of_conduct, internal_reporting_system,
                       training_schedule, audit_frequency, compliance_officer_name, status
                FROM fraud_prevention_program
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        return {"programs": [dict(r) for r in rows]}


@router.get(
    "/programs/{item_id}",
    response_model=FraudPreventionProgramDetail,
    operation_id="get_fraud_prevention_program",
)
async def get_fraud_prevention_program(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, code_of_conduct, internal_reporting_system,
                       training_schedule, audit_frequency, compliance_officer_name,
                       status, created_at
                FROM fraud_prevention_program
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Programa de prevencion de fraude no encontrado"},
            )
        return dict(row)


# ===========================================================================
# Fraud Risk Assessments
# ===========================================================================


@router.get(
    "/risk-assessments",
    response_model=FraudRiskAssessmentListResponse,
    operation_id="list_fraud_risk_assessments",
)
async def list_fraud_risk_assessments(
    entity_id: int | None = Query(None, description="Filtrar por ID de la entidad"),
    search: str | None = Query(None, description="Buscar en areas de riesgo"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("fr.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if search:
        filters.append("fr.risk_areas LIKE :search")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, assessment_date, risk_areas,
                       mitigation_measures, next_review_date
                FROM fraud_risk_assessment
                WHERE {" AND ".join(filters)}
                ORDER BY assessment_date DESC NULLS LAST
                """
            ),
            params,
        ).mappings()
        return {"assessments": [dict(r) for r in rows]}


@router.get(
    "/risk-assessments/{item_id}",
    response_model=FraudRiskAssessmentDetail,
    operation_id="get_fraud_risk_assessment",
)
async def get_fraud_risk_assessment(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, assessment_date, risk_areas,
                       mitigation_measures, next_review_date, created_at
                FROM fraud_risk_assessment
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Evaluacion de riesgo de fraude no encontrada"},
            )
        return dict(row)


# ===========================================================================
# Fraud Incidents
# ===========================================================================


@router.get(
    "/incidents",
    response_model=FraudIncidentListResponse,
    operation_id="list_fraud_incidents",
)
async def list_fraud_incidents(
    entity_id: int | None = Query(None, description="Filtrar por ID de la entidad"),
    status: str | None = Query(None, description="Filtrar por estado: open, under_investigation, resolved, closed"),
    min_amount: float | None = Query(None, description="Filtrar por importe minimo en EUR"),
    search: str | None = Query(None, description="Buscar en descripcion"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("fi.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if status:
        filters.append("fi.status = :status")
        params["status"] = status
    if min_amount is not None:
        filters.append("fi.amount_eur >= :min_amount")
        params["min_amount"] = min_amount
    if search:
        filters.append("fi.description LIKE :search")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, incident_date, amount_eur, status,
                       resolution_date, regulatory_notification
                FROM fraud_incident
                WHERE {" AND ".join(filters)}
                ORDER BY incident_date DESC NULLS LAST
                """
            ),
            params,
        ).mappings()
        return {"incidents": [dict(r) for r in rows]}


@router.get(
    "/incidents/{item_id}",
    response_model=FraudIncidentDetail,
    operation_id="get_fraud_incident",
)
async def get_fraud_incident(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, incident_date, description, amount_eur,
                       status, resolution_date, regulatory_notification, created_at
                FROM fraud_incident
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Incidente de fraude no encontrado"},
            )
        return dict(row)
