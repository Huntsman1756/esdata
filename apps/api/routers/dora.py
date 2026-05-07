"""DORA (Digital Operational Resilience Act) data model endpoints.

Fase 31.8 — Expansion regulatoria.

Endpoints:
    GET  /v1/dora/tic-incidents               — list TIC incidents
    GET  /v1/dora/tic-incidents/{id}          — get TIC incident by ID
    GET  /v1/dora/third-party-providers        — list third-party providers
    GET  /v1/dora/third-party-providers/{id}  — get third-party provider by ID
    GET  /v1/dora/ict-risk-registers          — list ICT risk registers
    GET  /v1/dora/ict-risk-registers/{id}     — get ICT risk register by ID
    GET  /v1/dora/penetration-tests           — list penetration tests
    GET  /v1/dora/penetration-tests/{id}      — get penetration test by ID
    GET  /v1/dora/inclassification-frameworks  — list incident classification frameworks
    GET  /v1/dora/inclassification-frameworks/{id} — get framework by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    DoraIctRiskRegisterDetail,
    DoraIctRiskRegisterListResponse,
    DoraIncidentClassificationFrameworkDetail,
    DoraIncidentClassificationFrameworkListResponse,
    DoraPenetrationTestDetail,
    DoraPenetrationTestListResponse,
    DoraThirdPartyProviderDetail,
    DoraThirdPartyProviderListResponse,
    DoraTicIncidentDetail,
    DoraTicIncidentListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/dora", tags=["dora"])


# ===========================================================================
# TIC Incidents
# ===========================================================================


@router.get(
    "/tic-incidents",
    response_model=DoraTicIncidentListResponse,
    operation_id="list_dora_tic_incidents",
)
async def list_dora_tic_incidents(
    status: str | None = Query(None, description="Filtrar por estado: open, in_progress, resolved, closed"),
    incident_severity: str | None = Query(None, description="Filtrar por severidad"),
    classification: str | None = Query(None, description="Filtrar por clasificacion"),
    search: str | None = Query(None, description="Buscar por entity_id"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("md.status = :status")
        params["status"] = status
    if incident_severity:
        filters.append("md.incident_severity = :incident_severity")
        params["incident_severity"] = incident_severity
    if classification:
        filters.append("md.classification = :classification")
        params["classification"] = classification
    if search:
        filters.append("CAST(md.entity_id AS TEXT) = :search")
        params["search"] = search

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, incident_severity, classification, status
                FROM dora_tic_incident md
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
                SELECT COUNT(*) FROM dora_tic_incident md
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/tic-incidents/{item_id}",
    response_model=DoraTicIncidentDetail,
    operation_id="get_dora_tic_incident",
)
async def get_dora_tic_incident(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, incident_severity, classification, status,
                       description, impact_scope, detection_date,
                       resolution_date, root_cause, created_at
                FROM dora_tic_incident md
                WHERE md.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Third-Party Providers
# ===========================================================================


@router.get(
    "/third-party-providers",
    response_model=DoraThirdPartyProviderListResponse,
    operation_id="list_dora_third_party_providers",
)
async def list_dora_third_party_providers(
    status: str | None = Query(None, description="Filtrar por estado"),
    provider_type: str | None = Query(None, description="Filtrar por tipo de proveedor"),
    criticality_assessment: str | None = Query(None, description="Filtrar por evaluacion de criticidad"),
    search: str | None = Query(None, description="Buscar por provider_name"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mp.status = :status")
        params["status"] = status
    if provider_type:
        filters.append("mp.provider_type = :provider_type")
        params["provider_type"] = provider_type
    if criticality_assessment:
        filters.append("mp.criticality_assessment = :criticality_assessment")
        params["criticality_assessment"] = criticality_assessment
    if search:
        filters.append("LOWER(mp.provider_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, provider_name, provider_type, criticality_assessment, status
                FROM dora_third_party_provider mp
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
                SELECT COUNT(*) FROM dora_third_party_provider mp
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/third-party-providers/{item_id}",
    response_model=DoraThirdPartyProviderDetail,
    operation_id="get_dora_third_party_provider",
)
async def get_dora_third_party_provider(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, provider_name, provider_type, criticality_assessment, status,
                       contract_start, contract_end, eu_supervision_status, exit_strategy,
                       created_at
                FROM dora_third_party_provider mp
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
# ICT Risk Registers
# ===========================================================================


@router.get(
    "/ict-risk-registers",
    response_model=DoraIctRiskRegisterListResponse,
    operation_id="list_dora_ict_risk_registers",
)
async def list_dora_ict_risk_registers(
    status: str | None = Query(None, description="Filtrar por estado"),
    likelihood: str | None = Query(None, description="Filtrar por probabilidad"),
    impact: str | None = Query(None, description="Filtrar por impacto"),
    search: str | None = Query(None, description="Buscar por entity_id o owner"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mr.status = :status")
        params["status"] = status
    if likelihood:
        filters.append("mr.likelihood = :likelihood")
        params["likelihood"] = likelihood
    if impact:
        filters.append("mr.impact = :impact")
        params["impact"] = impact
    if search:
        filters.append(
            "(CAST(mr.entity_id AS TEXT) = :search OR LOWER(mr.owner) LIKE LOWER(:search_like))"
        )
        params["search"] = search
        params["search_like"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, risk_description, likelihood, impact, owner, status
                FROM dora_ict_risk_register mr
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
                SELECT COUNT(*) FROM dora_ict_risk_register mr
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/ict-risk-registers/{item_id}",
    response_model=DoraIctRiskRegisterDetail,
    operation_id="get_dora_ict_risk_register",
)
async def get_dora_ict_risk_register(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, risk_description, likelihood, impact, owner, status,
                       mitigation, review_date, created_at
                FROM dora_ict_risk_register mr
                WHERE mr.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)


# ===========================================================================
# Penetration Tests
# ===========================================================================


@router.get(
    "/penetration-tests",
    response_model=DoraPenetrationTestListResponse,
    operation_id="list_dora_penetration_tests",
)
async def list_dora_penetration_tests(
    status: str | None = Query(None, description="Filtrar por estado"),
    test_type: str | None = Query(None, description="Filtrar por tipo de prueba"),
    search: str | None = Query(None, description="Buscar por entity_id o tester"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mp.status = :status")
        params["status"] = status
    if test_type:
        filters.append("mp.test_type = :test_type")
        params["test_type"] = test_type
    if search:
        filters.append(
            "(CAST(mp.entity_id AS TEXT) = :search OR LOWER(mp.tester) LIKE LOWER(:search_like))"
        )
        params["search"] = search
        params["search_like"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, test_type, tester, findings_count, critical_findings, status
                FROM dora_penetration_test mp
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
                SELECT COUNT(*) FROM dora_penetration_test mp
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/penetration-tests/{item_id}",
    response_model=DoraPenetrationTestDetail,
    operation_id="get_dora_penetration_test",
)
async def get_dora_penetration_test(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, test_type, tester, test_date, findings_count,
                       critical_findings, remediation_deadline, status, created_at
                FROM dora_penetration_test mp
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
# Incident Classification Frameworks
# ===========================================================================


@router.get(
    "/incident-classification-frameworks",
    response_model=DoraIncidentClassificationFrameworkListResponse,
    operation_id="list_dora_inc_classification_frameworks",
)
async def list_dora_inc_classification_frameworks(
    status: str | None = Query(None, description="Filtrar por estado"),
    search: str | None = Query(None, description="Buscar por framework_version"),
):
    filters = ["1=1"]
    params: dict = {}

    if status:
        filters.append("mf.status = :status")
        params["status"] = status
    if search:
        filters.append("LOWER(mf.framework_version) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, framework_version, effective_date, status
                FROM dora_incident_classification_framework mf
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
                SELECT COUNT(*) FROM dora_incident_classification_framework mf
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/incident-classification-frameworks/{item_id}",
    response_model=DoraIncidentClassificationFrameworkDetail,
    operation_id="get_dora_inc_classification_framework",
)
async def get_dora_inc_classification_framework(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, framework_version, effective_date, status,
                       severity_thresholds, reporting_timelines, created_at
                FROM dora_incident_classification_framework mf
                WHERE mf.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Entidad no encontrada"})
        return dict(row)
