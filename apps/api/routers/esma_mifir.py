from __future__ import annotations

from db import db_session
from fastapi import APIRouter, Query, Request
from routers.retrieval_audit import record_retrieval_query_audit
from sqlalchemy import text

router = APIRouter(prefix="/v1/esma/mifir", tags=["esma-mifir"])


@router.get("/schemas", operation_id="list_esma_mifir_schemas")
async def list_mifir_schemas(request: Request):
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, nombre, version, dominio, url_esma, source_hash,
                       capture_date, verified, completeness
                FROM esma_schema
                WHERE dominio = 'TRANSACTION_REPORTING'
                ORDER BY version DESC NULLS LAST, id
                """
            )
        ).mappings().all()

    items = [dict(row) | {"source_url": row["url_esma"], "quality_signal": "official_esma_schema"} for row in rows]
    response = {
        "items": items,
        "total": len(items),
        "verified": bool(items) and all(item.get("verified") for item in items),
        "completeness": "completa" if items and all(item.get("completeness") == "completa" for item in items) else "parcial",
        "quality_signal": "official_esma_schema" if items else "configured_but_unavailable",
    }
    record_retrieval_query_audit(
        request,
        path="/v1/esma/mifir/schemas",
        query_text="TRANSACTION_REPORTING",
        tool_name="list_esma_mifir_schemas",
        items=items,
        total=response["total"],
        verified=response["verified"],
        completeness=response["completeness"],
        response_summary=f"total={response['total']}; quality_signal={response['quality_signal']}",
    )
    return response


@router.get("/transaction-reporting/fields", operation_id="list_esma_mifir_transaction_reporting_fields")
async def list_transaction_reporting_fields(
    request: Request,
    q: str | None = Query(default=None, description="Filter by field name or description"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    conditions = ["s.dominio = 'TRANSACTION_REPORTING'"]
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if q:
        conditions.append("(sf.nombre_campo ILIKE :q OR sf.descripcion ILIKE :q)")
        params["q"] = f"%{q}%"
    where = "WHERE " + " AND ".join(conditions)
    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT sf.id, s.nombre AS schema_nombre, s.version, s.verified,
                       s.completeness, sf.nombre_campo, sf.tipo, sf.longitud,
                       sf.obligatorio, sf.descripcion, sf.rts_referencia,
                       sf.formato, sf.source_url, sf.source_hash, sf.capture_date
                FROM esma_schema_field sf
                JOIN esma_schema s ON s.id = sf.schema_id
                {where}
                ORDER BY sf.nombre_campo
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = db.execute(
            text(f"SELECT COUNT(*) FROM esma_schema_field sf JOIN esma_schema s ON s.id = sf.schema_id {where}"),
            params,
        ).scalar_one()

    items = [dict(row) | {"quality_signal": "official_esma_xsd"} for row in rows]
    response = {
        "items": items,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "verified": bool(items) and all(item.get("verified") for item in items),
        "completeness": "completa" if items and all(item.get("completeness") == "completa" for item in items) else "parcial",
        "quality_signal": "official_esma_xsd" if items else "configured_but_unavailable",
    }
    record_retrieval_query_audit(
        request,
        path="/v1/esma/mifir/transaction-reporting/fields",
        query_text=q or "TRANSACTION_REPORTING",
        tool_name="list_esma_mifir_transaction_reporting_fields",
        items=items,
        total=response["total"],
        verified=response["verified"],
        completeness=response["completeness"],
        response_summary=f"total={response['total']}; returned={len(items)}; quality_signal={response['quality_signal']}",
    )
    return response
