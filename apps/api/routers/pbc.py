"""Ley 10/2010 PBC (Prevencion Blanqueo de Capitales) endpoints.

Fase 31 — Expansion regulatoria.

Endpoints:
    GET  /v1/pbc/obligated-subjects              — list obligated subjects
    GET  /v1/pbc/obligated-subjects/{id}         — get subject by ID
    GET  /v1/pbc/internal-controls                — list internal controls
    GET  /v1/pbc/internal-controls/{id}           — get control by ID
    GET  /v1/pbc/suspicious-reports               — list SAR/MAR
    GET  /v1/pbc/suspicious-reports/{id}          — get report by ID
    GET  /v1/pbc/beneficial-owners                — list beneficial owners
    GET  /v1/pbc/beneficial-owners/{id}           — get owner by ID
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    BeneficialOwnerRecordDetail,
    BeneficialOwnerRecordListResponse,
    PbcInternalControlDetail,
    PbcInternalControlListResponse,
    PbcObligatedSubjectDetail,
    PbcObligatedSubjectListResponse,
    SuspiciousActivityReportDetail,
    SuspiciousActivityReportListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/pbc", tags=["pbc"])


# ===========================================================================
# PBC Obligated Subjects
# ===========================================================================


@router.get(
    "/obligated-subjects",
    response_model=PbcObligatedSubjectListResponse,
    operation_id="list_pbc_obligated_subjects",
)
async def list_pbc_obligated_subjects(
    subject_type: str | None = Query(None, description="Filtrar por tipo: credit entity, PBC entity, auditor, notary, lawyer, real_estate_agency, casino, art_dealer"),
    supervisory_authority: str | None = Query(None, description="Filtrar por autoridad supervisora"),
    status: str | None = Query(None, description="Filtrar por estado: active, inactive, suspended"),
    search: str | None = Query(None, description="Buscar por NIF o numero de registro"),
):
    filters = ["1=1"]
    params: dict = {}

    if subject_type:
        filters.append("ps.subject_type = :subject_type")
        params["subject_type"] = subject_type
    if supervisory_authority:
        filters.append("ps.supervisory_authority = :supervisory_authority")
        params["supervisory_authority"] = supervisory_authority
    if status:
        filters.append("ps.status = :status")
        params["status"] = status
    if search:
        filters.append(
            "(LOWER(ps.tin) LIKE LOWER(:search) OR LOWER(ps.registration_number) LIKE LOWER(:search))"
        )
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, subject_type, tin, registration_number,
                       supervisory_authority, pbc_license, status
                FROM pbc_obligated_subject ps
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        subjects = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM pbc_obligated_subject ps
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"subjects": subjects, "total": count}


@router.get(
    "/obligated-subjects/{item_id}",
    response_model=PbcObligatedSubjectDetail,
    operation_id="get_pbc_obligated_subject",
)
async def get_pbc_obligated_subject(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, subject_type, tin, registration_number,
                       supervisory_authority, pbc_license, status, created_at
                FROM pbc_obligated_subject ps
                WHERE ps.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Sujeto obligado PBC no encontrado"},
            )
        return dict(row)


# ===========================================================================
# PBC Internal Controls
# ===========================================================================


@router.get(
    "/internal-controls",
    response_model=PbcInternalControlListResponse,
    operation_id="list_pbc_internal_controls",
)
async def list_pbc_internal_controls(
    obligated_subject_id: int | None = Query(None, description="Filtrar por ID del sujeto obligado"),
):
    filters = ["1=1"]
    params: dict = {}

    if obligated_subject_id is not None:
        filters.append("ic.obligated_subject_id = :obligated_subject_id")
        params["obligated_subject_id"] = obligated_subject_id

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, obligated_subject_id, risk_assessment_date,
                       compliance_officer, internal_reporting_channel,
                       training_program, audit_trail
                FROM pbc_internal_control ic
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        controls = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM pbc_internal_control ic
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"controls": controls, "total": count}


@router.get(
    "/internal-controls/{item_id}",
    response_model=PbcInternalControlDetail,
    operation_id="get_pbc_internal_control",
)
async def get_pbc_internal_control(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, obligated_subject_id, risk_assessment_date,
                       compliance_officer, internal_reporting_channel,
                       training_program, audit_trail, created_at
                FROM pbc_internal_control ic
                WHERE ic.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Control interno PBC no encontrado"},
            )
        return dict(row)


# ===========================================================================
# Suspicious Activity Reports (SAR/MAR)
# ===========================================================================


@router.get(
    "/suspicious-reports",
    response_model=SuspiciousActivityReportListResponse,
    operation_id="list_suspicious_activity_reports",
)
async def list_suspicious_activity_reports(
    obligated_subject_id: int | None = Query(None, description="Filtrar por ID del sujeto obligado"),
    status: str | None = Query(None, description="Filtrar por estado: filed, under_review, investigated, closed"),
    severity: str | None = Query(None, description="Filtrar por gravedad: low, medium, high, critical"),
    search: str | None = Query(None, description="Buscar por referencia SEPBLAC"),
):
    filters = ["1=1"]
    params: dict = {}

    if obligated_subject_id is not None:
        filters.append("sar.obligated_subject_id = :obligated_subject_id")
        params["obligated_subject_id"] = obligated_subject_id
    if status:
        filters.append("sar.status = :status")
        params["status"] = status
    if severity:
        filters.append("sar.severity = :severity")
        params["severity"] = severity
    if search:
        filters.append("LOWER(sar.sepblac_reference) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, obligated_subject_id, submission_date, severity,
                       status, sepblac_reference
                FROM suspicious_activity_report sar
                WHERE {" AND ".join(filters)}
                ORDER BY sar.submission_date DESC
                """
            ),
            params,
        ).mappings()
        reports = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM suspicious_activity_report sar
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"reports": reports, "total": count}


@router.get(
    "/suspicious-reports/{item_id}",
    response_model=SuspiciousActivityReportDetail,
    operation_id="get_suspicious_activity_report",
)
async def get_suspicious_activity_report(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, obligated_subject_id, submission_date, description,
                       severity, status, sepblac_reference, created_at
                FROM suspicious_activity_report sar
                WHERE sar.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Reporte de actividad sospechosa no encontrado"},
            )
        return dict(row)


# ===========================================================================
# Beneficial Owner Records
# ===========================================================================


@router.get(
    "/beneficial-owners",
    response_model=BeneficialOwnerRecordListResponse,
    operation_id="list_beneficial_owners",
)
async def list_beneficial_owners(
    entity_id: int | None = Query(None, description="Filtrar por ID de la entidad"),
    search: str | None = Query(None, description="Buscar por nombre del beneficiario"),
):
    filters = ["1=1"]
    params: dict = {}

    if entity_id is not None:
        filters.append("bo.entity_id = :entity_id")
        params["entity_id"] = entity_id
    if search:
        filters.append("LOWER(bo.owner_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, owner_name, ownership_percentage,
                       acquisition_date, verification_method, verification_date
                FROM beneficial_owner_record bo
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        records = [dict(r) for r in rows]
        count = db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM beneficial_owner_record bo
                WHERE {" AND ".join(filters)}
                """
            ),
            params,
        ).scalar()
        return {"records": records, "total": count}


@router.get(
    "/beneficial-owners/{item_id}",
    response_model=BeneficialOwnerRecordDetail,
    operation_id="get_beneficial_owner",
)
async def get_beneficial_owner(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, owner_name, ownership_percentage,
                       acquisition_date, verification_method, verification_date, created_at
                FROM beneficial_owner_record bo
                WHERE bo.id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "Registro de beneficiario real no encontrado"},
            )
        return dict(row)
