from __future__ import annotations

from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from routers.retrieval_audit import record_retrieval_query_audit
from sqlalchemy import text

router = APIRouter(prefix="/v1/eurlex/market", tags=["eurlex-market"])


def _act_item(row) -> dict:
    item = dict(row)
    item["source_url"] = item.pop("url_eurlex", None)
    item["quality_signal"] = "official_eurlex_text" if item.get("verified") else "evidence_limited"
    return item


@router.get("/acts", operation_id="list_eurlex_market_acts")
async def list_market_acts(
    request: Request,
    q: str | None = Query(default=None, description="Filter by CELEX or title"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if q:
        conditions.append("(celex ILIKE :q OR titulo ILIKE :q)")
        params["q"] = f"%{q}%"
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT celex, titulo, tipo, fecha_publicacion, fecha_vigor,
                       url_eurlex, source_hash, capture_date, verified, completeness
                FROM eurlex_act
                {where}
                ORDER BY celex
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = db.execute(text(f"SELECT COUNT(*) FROM eurlex_act {where}"), params).scalar_one()

    items = [_act_item(row) for row in rows]
    response = {
        "items": items,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "verified": bool(items) and all(item.get("verified") for item in items),
        "completeness": "completa" if items and all(item.get("completeness") == "completa" for item in items) else "parcial",
        "quality_signal": "official_eurlex_text" if items else "configured_but_unavailable",
    }
    record_retrieval_query_audit(
        request,
        path="/v1/eurlex/market/acts",
        query_text=q or "",
        tool_name="list_eurlex_market_acts",
        items=items,
        total=response["total"],
        verified=response["verified"],
        completeness=response["completeness"],
        response_summary=f"total={response['total']}; returned={len(items)}; quality_signal={response['quality_signal']}",
    )
    return response


@router.get("/{celex}/articulos/{numero}", operation_id="get_eurlex_market_article")
async def get_market_article(request: Request, celex: str, numero: str):
    normalized_celex = celex.strip().upper()
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT a.celex, a.titulo AS acto_titulo, a.tipo,
                       a.verified, a.completeness, a.url_eurlex AS act_source_url,
                       ar.numero, ar.titulo, ar.texto, ar.url_eurlex,
                       ar.source_hash, ar.capture_date
                FROM eurlex_act a
                JOIN eurlex_article ar ON ar.act_id = a.id
                WHERE a.celex = :celex AND ar.numero = :numero
                LIMIT 1
                """
            ),
            {"celex": normalized_celex, "numero": numero},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail={"error": "Articulo EUR-Lex market no encontrado"})

    item = dict(row)
    item["source_url"] = item.pop("url_eurlex", None) or item.get("act_source_url")
    item["quality_signal"] = "official_eurlex_text" if item.get("verified") and item.get("texto") else "evidence_limited"
    record_retrieval_query_audit(
        request,
        path=f"/v1/eurlex/market/{normalized_celex}/articulos/{numero}",
        query_text=f"{normalized_celex}:{numero}",
        tool_name="get_eurlex_market_article",
        items=[item],
        total=1,
        verified=bool(item.get("verified")),
        completeness=item.get("completeness") or "parcial",
        response_summary=f"celex={normalized_celex}; article={numero}; quality_signal={item['quality_signal']}",
    )
    return item
