"""Fase 31.10 — PSD2/PSD3, SEPA, Consumer Credit, IDD, Solvency II endpoints.

Routers:
    /v1/psd2          — PSD2/PSD3 payment services
    /v1/consumer-credit — Consumer credit contracts
    /v1/insurance      — IDD and Solvency II

Fase 31.10 — Expansion regulatoria: PSD2/PSD3, SEPA, Consumer Credit, IDD, Solvency II.
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/v1/psd2", tags=["psd2"])
consumer_credit_router = APIRouter(prefix="/v1/consumer-credit", tags=["consumer credit"])
insurance_router = APIRouter(prefix="/v1/insurance", tags=["insurance"])


# ===========================================================================
# PSD2 — ASPSP
# ===========================================================================


@router.get(
    "/aspsp",
    operation_id="list_psd2_aspsp",
)
async def list_psd2_aspsp(
    regulatory_status: str | None = Query(None, description="Estado regulatorio: registered, suspended, revoked"),
    home_member_state: str | None = Query(None, description="Estado miembro: ES, DE, FR, etc."),
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = ["1=1"]
    params: dict = {}
    if regulatory_status:
        filters.append("p.regulatory_status = :regulatory_status")
        params["regulatory_status"] = regulatory_status
    if home_member_state:
        filters.append("p.home_member_state = :home_member_state")
        params["home_member_state"] = home_member_state

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, bic, psd2_license, strong_customer_auth_applied,
                       api_version, regulatory_status, home_member_state
                FROM psd2_aspsp p
                WHERE {" AND ".join(filters)}
                ORDER BY id
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM psd2_aspsp p WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        next_offset = offset + limit if offset + len(items) < int(count or 0) else None
        return {"items": items, "total": count, "limit": limit, "offset": offset, "has_more": next_offset is not None, "next_offset": next_offset}


@router.get(
    "/aspsp/{item_id}",
    operation_id="get_psd2_aspsp",
)
async def get_psd2_aspsp(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, bic, psd2_license, strong_customer_auth_applied,
                       api_version, regulatory_status, home_member_state, created_at
                FROM psd2_aspsp
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"ASPSP no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# PSD2 — AISP
# ===========================================================================


@router.get(
    "/aisp",
    operation_id="list_psd2_aisp",
)
async def list_psd2_aisp(
    status: str | None = Query(None, description="Estado: active, inactive, suspended"),
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = ["1=1"]
    params: dict = {}
    if status:
        filters.append("a.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, registration_number, registration_id,
                       access_scope, valid_from, valid_to, status
                FROM psd2_aisp a
                WHERE {" AND ".join(filters)}
                ORDER BY id
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM psd2_aisp a WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        next_offset = offset + limit if offset + len(items) < int(count or 0) else None
        return {"items": items, "total": count, "limit": limit, "offset": offset, "has_more": next_offset is not None, "next_offset": next_offset}


@router.get(
    "/aisp/{item_id}",
    operation_id="get_psd2_aisp",
)
async def get_psd2_aisp(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, registration_number, registration_id,
                       access_scope, valid_from, valid_to, status, created_at
                FROM psd2_aisp
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"AISP no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# PSD2 — PISP
# ===========================================================================


@router.get(
    "/pisp",
    operation_id="list_psd2_pisp",
)
async def list_psd2_pisp(
    authorization_status: str | None = Query(None, description="Estado: authorized, suspended, revoked"),
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = ["1=1"]
    params: dict = {}
    if authorization_status:
        filters.append("p.authorization_status = :authorization_status")
        params["authorization_status"] = authorization_status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, registration_number, authorization_status,
                       home_member_state, psd3_transition_status
                FROM psd2_pisp p
                WHERE {" AND ".join(filters)}
                ORDER BY id
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM psd2_pisp p WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        next_offset = offset + limit if offset + len(items) < int(count or 0) else None
        return {"items": items, "total": count, "limit": limit, "offset": offset, "has_more": next_offset is not None, "next_offset": next_offset}


@router.get(
    "/pisp/{item_id}",
    operation_id="get_psd2_pisp",
)
async def get_psd2_pisp(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, registration_number, authorization_status,
                       home_member_state, psd3_transition_status, created_at
                FROM psd2_pisp
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"PISP no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# PSD2 — Consent
# ===========================================================================


@router.get(
    "/consent",
    operation_id="list_psd2_consent",
)
async def list_psd2_consent(
    consent_type: str | None = Query(None, description="Tipo: AIS, PIS"),
    status: str | None = Query(None, description="Estado: active, expired, revoked"),
):
    filters = ["1=1"]
    params: dict = {}
    if consent_type:
        filters.append("c.consent_type = :consent_type")
        params["consent_type"] = consent_type
    if status:
        filters.append("c.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, client_id, aspsp_id, consent_type, accounts_accessed,
                       payment_count_limit, used_count, valid_from, valid_to, status
                FROM psd2_consent c
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM psd2_consent c WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/consent/{item_id}",
    operation_id="get_psd2_consent",
)
async def get_psd2_consent(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, client_id, aspsp_id, consent_type, accounts_accessed,
                       payment_count_limit, used_count, valid_from, valid_to, status, created_at
                FROM psd2_consent
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Consentimiento no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# PSD2 — Incident Report
# ===========================================================================


@router.get(
    "/incidents",
    operation_id="list_psd2_incidents",
)
async def list_psd2_incidents(
    severity: str | None = Query(None, description="Gravedad: low, medium, high, critical"),
):
    filters = ["1=1"]
    params: dict = {}
    if severity:
        filters.append("i.severity = :severity")
        params["severity"] = severity

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, aspsp_id, incident_type, severity, description,
                       reported_to_bde, reported_date
                FROM psd2_incident_report i
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM psd2_incident_report i WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@router.get(
    "/incidents/{item_id}",
    operation_id="get_psd2_incident",
)
async def get_psd2_incident(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, aspsp_id, incident_type, severity, description,
                       reported_to_bde, reported_date, created_at
                FROM psd2_incident_report
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Incidente no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# SEPA — Payment Rules
# ===========================================================================


@router.get(
    "/sepa-rules",
    operation_id="list_sepa_payment_rules",
)
async def list_sepa_payment_rules(
    payment_type: str | None = Query(None, description="Tipo de pago: SEPA CT, SEPA CCT, SEPA Core, SEPA B2B"),
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset de paginacion"),
):
    filters = ["1=1"]
    params: dict = {}
    if payment_type:
        filters.append("s.payment_type = :payment_type")
        params["payment_type"] = payment_type

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, scheme_version, payment_type, service_level,
                       local_instrument, category_purpose, cut_off_time, settlement_days
                FROM sepa_payment_rule s
                WHERE {" AND ".join(filters)}
                ORDER BY id
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM sepa_payment_rule s WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        next_offset = offset + limit if offset + len(items) < int(count or 0) else None
        return {"items": items, "total": count, "limit": limit, "offset": offset, "has_more": next_offset is not None, "next_offset": next_offset}


@router.get(
    "/sepa-rules/{item_id}",
    operation_id="get_sepa_payment_rule",
)
async def get_sepa_payment_rule(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, scheme_version, payment_type, service_level,
                       local_instrument, category_purpose, cut_off_time, settlement_days, created_at
                FROM sepa_payment_rule
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Regla SEPA no encontrada: {item_id}")
        return dict(row)


# ===========================================================================
# Consumer Credit — Contracts
# ===========================================================================


@consumer_credit_router.get(
    "/contracts",
    operation_id="list_consumer_credit_contracts",
)
async def list_consumer_credit_contracts(
    credit_type: str | None = Query(None, description="Tipo: installment, revolving, real-secured"),
    status: str | None = Query(None, description="Estado: active, completed, defaulted, terminated"),
):
    filters = ["1=1"]
    params: dict = {}
    if credit_type:
        filters.append("c.credit_type = :credit_type")
        params["credit_type"] = credit_type
    if status:
        filters.append("c.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, lender_id, borrower_id, credit_type, principal_amount,
                       annual_percentage_rate, total_amount, term_months, purpose,
                       signing_date, status
                FROM consumer_credit_contract c
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM consumer_credit_contract c WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@consumer_credit_router.get(
    "/contracts/{item_id}",
    operation_id="get_consumer_credit_contract",
)
async def get_consumer_credit_contract(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, lender_id, borrower_id, credit_type, principal_amount,
                       annual_percentage_rate, total_amount, term_months, purpose,
                       signing_date, status, created_at
                FROM consumer_credit_contract
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Contrato no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# Consumer Credit — Disclosure
# ===========================================================================


@consumer_credit_router.get(
    "/disclosures",
    operation_id="list_consumer_credit_disclosures",
)
async def list_consumer_credit_disclosures(
    contract_id: int | None = Query(None, description="Filtrar por ID de contrato"),
):
    filters = ["1=1"]
    params: dict = {}
    if contract_id is not None:
        filters.append("d.contract_id = :contract_id")
        params["contract_id"] = contract_id

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, contract_id, fap, total_cost, regular_payment,
                       amortization_schedule_url, right_of_withdrawal,
                       early_repayment_penalty, url
                FROM consumer_credit_disclosure d
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM consumer_credit_disclosure d WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@consumer_credit_router.get(
    "/disclosures/{item_id}",
    operation_id="get_consumer_credit_disclosure",
)
async def get_consumer_credit_disclosure(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, contract_id, fap, total_cost, regular_payment,
                       amortization_schedule_url, right_of_withdrawal,
                       early_repayment_penalty, url, created_at
                FROM consumer_credit_disclosure
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Disclosure no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# Consumer Credit — Overindebtedness
# ===========================================================================


@consumer_credit_router.get(
    "/overindebtedness",
    operation_id="list_consumer_credit_overindebtedness",
)
async def list_consumer_credit_overindebtedness(
    procedure_status: str | None = Query(None, description="Estado del procedimiento"),
):
    filters = ["1=1"]
    params: dict = {}
    if procedure_status:
        filters.append("o.procedure_status = :procedure_status")
        params["procedure_status"] = procedure_status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, borrower_id, declared_date, total_debt, monthly_income,
                       unsecured_debt, procedure_status, court_reference
                FROM consumer_credit_overindebtedness o
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM consumer_credit_overindebtedness o WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@consumer_credit_router.get(
    "/overindebtedness/{item_id}",
    operation_id="get_consumer_credit_overindebtedness",
)
async def get_consumer_credit_overindebtedness(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, borrower_id, declared_date, total_debt, monthly_income,
                       unsecured_debt, procedure_status, court_reference, created_at
                FROM consumer_credit_overindebtedness
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Registro no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# IDD — Distributors
# ===========================================================================


@insurance_router.get(
    "/distributors",
    operation_id="list_idd_distributors",
)
async def list_idd_distributors(
    status: str | None = Query(None, description="Estado: active, inactive, suspended"),
):
    filters = ["1=1"]
    params: dict = {}
    if status:
        filters.append("d.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, registration_number, insurance_ao,
                       products_covered, professional_indemnity, training_certified, status
                FROM idd_distributor d
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM idd_distributor d WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@insurance_router.get(
    "/distributors/{item_id}",
    operation_id="get_idd_distributor",
)
async def get_idd_distributor(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, registration_number, insurance_ao,
                       products_covered, professional_indemnity, training_certified, status, created_at
                FROM idd_distributor
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Distribuidor IDD no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# IDD — UCI Products
# ===========================================================================


@insurance_router.get(
    "/uci-products",
    operation_id="list_idd_uci_products",
)
async def list_idd_uci_products(
    product_type: str | None = Query(None, description="Tipo: life, non-life"),
    status: str | None = Query(None, description="Estado: active, withdrawn"),
):
    filters = ["1=1"]
    params: dict = {}
    if product_type:
        filters.append("u.product_type = :product_type")
        params["product_type"] = product_type
    if status:
        filters.append("u.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, product_id, product_type, risk_coverage, cost_breakdown,
                       exit_costs, taxes, version, status
                FROM idd_product_uci u
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM idd_product_uci u WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@insurance_router.get(
    "/uci-products/{item_id}",
    operation_id="get_idd_uci_product",
)
async def get_idd_uci_product(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, product_id, product_type, risk_coverage, cost_breakdown,
                       exit_costs, taxes, version, status, created_at
                FROM idd_product_uci
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Producto UCI no encontrado: {item_id}")
        return dict(row)


# ===========================================================================
# Solvency II — Entities
# ===========================================================================


@insurance_router.get(
    "/solvency-entities",
    operation_id="list_solvency_ii_entities",
)
async def list_solvency_ii_entities(
    entity_type: str | None = Query(None, description="Tipo: life, non-life, mixed, branch"),
    home_supervisor: str | None = Query(None, description="Supervisor nacional"),
):
    filters = ["1=1"]
    params: dict = {}
    if entity_type:
        filters.append("e.entity_type = :entity_type")
        params["entity_type"] = entity_type
    if home_supervisor:
        filters.append("e.home_supervisor = :home_supervisor")
        params["home_supervisor"] = home_supervisor

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, entity_type, solvency_capital_requirement,
                       minimum_capital_requirement, solvency_ratio, reporting_date, home_supervisor
                FROM solvency_ii_entity e
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM solvency_ii_entity e WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@insurance_router.get(
    "/solvency-entities/{item_id}",
    operation_id="get_solvency_ii_entity",
)
async def get_solvency_ii_entity(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, entity_type, solvency_capital_requirement,
                       minimum_capital_requirement, solvency_ratio, reporting_date, home_supervisor, created_at
                FROM solvency_ii_entity
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Entidad Solvency II no encontrada: {item_id}")
        return dict(row)


# ===========================================================================
# Solvency II — SFP
# ===========================================================================


@insurance_router.get(
    "/solvency-sfp",
    operation_id="list_solvency_ii_sfp",
)
async def list_solvency_ii_sfp(
    status: str | None = Query(None, description="Estado: published, draft"),
):
    filters = ["1=1"]
    params: dict = {}
    if status:
        filters.append("s.status = :status")
        params["status"] = status

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, entity_id, reporting_period, fund_breakdown,
                       asset_allocation, url, status
                FROM solvency_ii_sfp s
                WHERE {" AND ".join(filters)}
                ORDER BY id
                """
            ),
            params,
        ).mappings()
        items = [dict(r) for r in rows]
        count = db.execute(
            text(f"SELECT COUNT(*) FROM solvency_ii_sfp s WHERE {' AND '.join(filters)}"),
            params,
        ).scalar()
        return {"items": items, "total": count}


@insurance_router.get(
    "/solvency-sfp/{item_id}",
    operation_id="get_solvency_ii_sfp",
)
async def get_solvency_ii_sfp(item_id: int):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, entity_id, reporting_period, fund_breakdown,
                       asset_allocation, url, status, created_at
                FROM solvency_ii_sfp
                WHERE id = :item_id
                """
            ),
            {"item_id": item_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"SFP no encontrado: {item_id}")
        return dict(row)
