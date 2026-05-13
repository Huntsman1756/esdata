from __future__ import annotations

from db import db_session
from fastapi import APIRouter, Query, Request
from routers.retrieval_audit import record_retrieval_query_audit
from sqlalchemy import text

router = APIRouter(prefix="/v1/esma/firds", tags=["esma-firds"])


@router.get("/files", operation_id="list_esma_firds_files")
async def list_firds_files(
    request: Request,
    tipo: str | None = Query(default=None, description="FULINS or DLTINS"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if tipo:
        conditions.append("tipo = :tipo")
        params["tipo"] = tipo.upper()
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT id, tipo, fecha, url_esma, size_bytes, source_hash,
                       downloaded, processed, capture_date, verified, completeness
                FROM esma_firds_file
                {where}
                ORDER BY fecha DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = db.execute(text(f"SELECT COUNT(*) FROM esma_firds_file {where}"), params).scalar_one()

    items = [dict(row) | {"source_url": row["url_esma"], "quality_signal": "official_esma_file_metadata"} for row in rows]
    response = {
        "items": items,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "verified": False,
        "completeness": "parcial",
        "quality_signal": "evidence_limited_firds_pilot" if items else "configured_but_unavailable",
        "safe_to_answer": bool(items),
    }
    record_retrieval_query_audit(
        request,
        path="/v1/esma/firds/files",
        query_text=tipo or "",
        tool_name="list_esma_firds_files",
        items=items,
        total=response["total"],
        verified=False,
        completeness="parcial",
        response_summary=f"total={response['total']}; quality_signal={response['quality_signal']}",
    )
    return response


@router.get("/instruments", operation_id="list_esma_firds_instruments")
async def list_firds_instruments(
    request: Request,
    isin: str | None = Query(default=None, min_length=2, max_length=12),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if isin:
        conditions.append("i.isin = :isin")
        params["isin"] = isin.upper()
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT i.id, i.isin, i.nombre, i.tipo_instrumento,
                       i.fecha_admision, i.mic, i.moneda,
                       f.url_esma AS source_url, i.source_hash, i.capture_date
                FROM esma_firds_instrument i
                LEFT JOIN esma_firds_file f ON f.id = i.source_file_id
                {where}
                ORDER BY i.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = db.execute(
            text(f"SELECT COUNT(*) FROM esma_firds_instrument i {where}"),
            params,
        ).scalar_one()

    items = [dict(row) | {"quality_signal": "evidence_limited_firds_pilot"} for row in rows]
    response = {
        "items": items,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "verified": False,
        "completeness": "parcial",
        "quality_signal": "evidence_limited_firds_pilot",
        "safe_to_answer": bool(items),
        "evidence_notice": "FIRDS has only a bounded DLTINS pilot sample loaded; absence is not authoritative.",
    }
    record_retrieval_query_audit(
        request,
        path="/v1/esma/firds/instruments",
        query_text=isin or "",
        tool_name="list_esma_firds_instruments",
        items=items,
        total=response["total"],
        verified=False,
        completeness="parcial",
        response_summary=f"total={response['total']}; returned={len(items)}; quality_signal={response['quality_signal']}",
    )
    return response
