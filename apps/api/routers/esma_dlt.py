from __future__ import annotations

from db import db_session
from fastapi import APIRouter, Query, Request
from routers.retrieval_audit import record_retrieval_query_audit
from sqlalchemy import text

router = APIRouter(prefix="/v1/esma/dlt", tags=["esma-dlt"])


@router.get("/infrastructures", operation_id="list_esma_dlt_infrastructures")
async def list_dlt_infrastructures(
    request: Request,
    pais: str | None = Query(default=None, min_length=2, max_length=3),
    tipo: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if pais:
        conditions.append("pais = :pais")
        params["pais"] = pais.upper()
    if tipo:
        conditions.append("tipo ILIKE :tipo")
        params["tipo"] = f"%{tipo}%"
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, nombre, pais, tipo, autoridad_competente,
                       fecha_autorizacion, url_esma, source_hash, capture_date,
                       verified, completeness
                FROM esma_dlt_market_infrastructure
                {where}
                ORDER BY pais, nombre
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = db.execute(text(f"SELECT COUNT(*) FROM esma_dlt_market_infrastructure {where}"), params).scalar_one()

    items = [dict(row) | {"source_url": row["url_esma"], "quality_signal": "official_esma_dlt_register"} for row in rows]
    response = {
        "items": items,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "verified": bool(items) and all(item.get("verified") for item in items),
        "completeness": "completa" if items and all(item.get("completeness") == "completa" for item in items) else "parcial",
        "quality_signal": "official_esma_dlt_register" if items else "configured_but_unavailable",
        "safe_to_answer": bool(items),
    }
    record_retrieval_query_audit(
        request,
        path="/v1/esma/dlt/infrastructures",
        query_text=" ".join(part for part in (pais or "", tipo or "") if part),
        tool_name="list_esma_dlt_infrastructures",
        items=items,
        total=response["total"],
        verified=response["verified"],
        completeness=response["completeness"],
        response_summary=f"total={response['total']}; returned={len(items)}; quality_signal={response['quality_signal']}",
    )
    return response
