from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import XbrlFactsResponse, XbrlFilingDetailResponse, PgcXbrlMappingsResponse, XbrlTaxonomyEntry, XbrlTaxonomyResponse, XbrlFactWithPgc, XbrlFactsWithPgcResponse

router = APIRouter(prefix="/v1/xbrl", tags=["xbrl"])


@router.get("/facts", response_model=XbrlFactsResponse, operation_id="list_xbrl_facts")
async def list_xbrl_facts(
    entity_id: str | None = Query(None, description="Filtrar por identificador externo XBRL de la entidad"),
    concept: str | None = Query(None, description="Filtrar por concepto XBRL"),
    limit: int = Query(100, ge=1, le=1000, description="Maximo de facts a devolver"),
):
    conditions = []
    params = {}

    if entity_id:
        conditions.append("entity_identifier = :entity_id")
        params["entity_id"] = entity_id
    if concept:
        conditions.append("concept = :concept")
        params["concept"] = concept

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT filing_id, concept, value_raw, value_numeric, unit, context_ref,
                       period_start, period_end, entity_identifier, decimals
                FROM xbrl_fact
                {where_clause}
                ORDER BY period_end DESC, concept ASC, id ASC
                LIMIT :limit
                """
            ),
            {**params, "limit": limit},
        ).mappings().all()

    return {
        "entity_id": entity_id,
        "concept": concept,
        "facts": [dict(row) for row in rows],
    }


@router.get("/filings/{filing_id}", response_model=XbrlFilingDetailResponse, operation_id="get_xbrl_filing_detail")
async def get_xbrl_filing(filing_id: int):
    with db_session() as db:
        filing_row = db.execute(
            text(
                """
                SELECT id, source_name, source_path, entity_identifier, period_start, period_end, filing_type, created_at
                FROM xbrl_filing
                WHERE id = :filing_id
                """
            ),
            {"filing_id": filing_id},
        ).mappings().one_or_none()

        if not filing_row:
            raise HTTPException(status_code=404, detail="Filing not found")

        facts_rows = db.execute(
            text(
                """
                SELECT filing_id, concept, value_raw, value_numeric, unit, context_ref,
                       period_start, period_end, entity_identifier, decimals
                FROM xbrl_fact
                WHERE filing_id = :filing_id
                ORDER BY concept ASC, id ASC
                """
            ),
            {"filing_id": filing_id},
        ).mappings().all()

    return {
        "filing": dict(filing_row),
        "facts": [dict(row) for row in facts_rows],
    }


@router.get(
    "/pgc-xbrl-mappings",
    response_model=PgcXbrlMappingsResponse,
    operation_id="list_pgc_xbrl_mappings",
)
async def list_pgc_xbrl_mappings(
    xbrl_concept: str | None = Query(None, description="Filtrar por concepto XBRL parcial"),
    pgc_account: str | None = Query(None, description="Filtrar por cuenta PGC"),
    confidence: str | None = Query(None, description="Filtrar por confianza (high, medium, low)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximo de mapeos a devolver"),
):
    conditions = []
    params: dict = {"limit": limit}

    if xbrl_concept:
        conditions.append("m.xbrl_concept_qname LIKE :xbrl_concept")
        params["xbrl_concept"] = f"%{xbrl_concept}%"
    if pgc_account:
        conditions.append("m.pgc_account_codigo = :pgc_account")
        params["pgc_account"] = pgc_account
    if confidence:
        conditions.append("m.confidence = :confidence")
        params["confidence"] = confidence
    conditions.append("m.is_active = true")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT m.xbrl_concept_qname, m.pgc_account_codigo,
                       c.descripcion as pgc_account_descripcion,
                       m.confidence, m.mapping_type, m.note
                FROM pgc_xbrl_mapping m
                LEFT JOIN pgc_cuenta c ON c.codigo = m.pgc_account_codigo
                {where_clause}
                ORDER BY m.xbrl_concept_qname ASC, m.pgc_account_codigo ASC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

    return {
        "xbrl_concept": xbrl_concept,
        "pgc_account": pgc_account,
        "confidence": confidence,
        "mappings": [dict(row) for row in rows],
    }


@router.get("/taxonomy", response_model=XbrlTaxonomyResponse, operation_id="list_xbrl_taxonomy")
async def list_xbrl_taxonomy(
    standard: str | None = Query(None, description="Filtrar por norma (IFRS 18, IAS 1, ESEF, etc.)"),
    language: str | None = Query(None, description="Filtrar por idioma (en, es, etc.)"),
    concept: str | None = Query(None, description="Filtrar por concept_qname parcial"),
    limit: int = Query(100, ge=1, le=1000, description="Maximo de entradas a devolver"),
):
    conditions = []
    params: dict = {"limit": limit}

    if standard:
        conditions.append("standard = :standard")
        params["standard"] = standard
    if language:
        conditions.append("label_language = :language")
        params["language"] = language
    if concept:
        conditions.append("concept_qname LIKE :concept")
        params["concept"] = f"%{concept}%"

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT concept_qname, namespace, label, label_language, label_role,
                       standard, data_type, period_type, is_monetary, is_negative_allowed
                FROM xbrl_taxonomy
                {where_clause}
                ORDER BY standard, concept_qname ASC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

    return {
        "standard": standard,
        "language": language,
        "concept": concept,
        "entries": [dict(row) for row in rows],
    }


@router.get(
    "/enriched-facts",
    response_model=XbrlFactsWithPgcResponse,
    operation_id="list_xbrl_enriched_facts",
)
async def list_xbrl_enriched_facts(
    entity_id: str | None = Query(None, description="Filtrar por identificador externo XBRL de la entidad"),
    concept: str | None = Query(None, description="Filtrar por concepto XBRL"),
    pgc_account: str | None = Query(None, description="Filtrar por cuenta PGC mapeada"),
    confidence: str | None = Query(None, description="Filtrar por confianza del mapeo (high, medium, low)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximo de facts a devolver"),
):
    conditions = []
    params: dict = {"limit": limit}

    if entity_id:
        conditions.append("f.entity_identifier = :entity_id")
        params["entity_id"] = entity_id
    if concept:
        conditions.append("f.concept = :concept")
        params["concept"] = concept

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT f.filing_id, f.concept, f.value_raw, f.value_numeric,
                       f.unit, f.context_ref, f.period_start, f.period_end,
                       f.entity_identifier, f.decimals,
                       m.pgc_account_codigo,
                       c.descripcion as pgc_account_descripcion,
                       m.confidence as mapping_confidence,
                       m.mapping_type,
                       m.note as mapping_note
                FROM xbrl_fact f
                LEFT JOIN pgc_xbrl_mapping m ON m.xbrl_concept_qname = f.concept AND m.is_active = true
                LEFT JOIN pgc_cuenta c ON c.codigo = m.pgc_account_codigo
                {where_clause}
                """
            ),
            params,
        ).mappings().all()

    # Apply pgc_account and confidence filters after LEFT JOIN
    # (to avoid filtering out facts without any PGC mapping)
    filtered = []
    for row in rows:
        if pgc_account and (row["pgc_account_codigo"] != pgc_account):
            continue
        if confidence and (row["mapping_confidence"] != confidence):
            continue
        filtered.append(dict(row))

    return {
        "entity_id": entity_id,
        "concept": concept,
        "pgc_account": pgc_account,
        "confidence": confidence,
        "facts": filtered[:limit],
    }
