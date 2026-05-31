from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import BDNSDetail, BDNSListResponse
from sqlalchemy import text

from routers.retrieval_audit import record_retrieval_query_audit

router = APIRouter(prefix="/v1/bdns", tags=["bdns"])


@router.get("", response_model=BDNSListResponse, operation_id="listar_bdns")
async def listar_bdns(
    request: Request,
    q: str | None = Query(None, description="Filtrar por texto o título"),
):
    filters = [
        "d.organismo_emisor = 'BDNS'",
        "d.tipo_fuente = 'bdns'",
    ]
    params: dict[str, str] = {}

    if q:
        filters.append(
            "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
        )
        params["term"] = f"%{q}%"

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT referencia, fecha, titulo, texto, url_fuente
                FROM documento_interpretativo d
                WHERE {where_clause}
                ORDER BY fecha DESC, referencia DESC
                LIMIT 20
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        convocatorias = [
            {
                "referencia": row["referencia"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "fragmento": row["texto"][:220] + ("..." if len(row["texto"]) > 220 else ""),
                "url_fuente": row["url_fuente"],
                "row_completeness": "partial",
                "row_provenance": "official_best_effort",
            }
            for row in rows
        ]
        record_retrieval_query_audit(
            request,
            path="/v1/bdns",
            query_text=q or "",
            tool_name="listar_bdns",
            items=convocatorias,
            total=len(convocatorias),
            verified=bool(convocatorias),
            completeness="parcial",
        )
        return {
            "convocatorias": convocatorias,
            "items": convocatorias,
            "total": len(convocatorias),
            "coverage_status": "very_limited" if convocatorias else "workflow_empty",
            "safe_to_answer": False,
            "coverage_note": (
                "BDNS expone un corpus muy limitado de convocatorias cargadas; "
                "no implica cobertura amplia de subvenciones."
            ),
        }


@router.get("/{referencia:path}", response_model=BDNSDetail, operation_id="get_bdns")
async def get_bdns(referencia: str, request: Request):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT referencia, fecha, titulo, texto, url_fuente
                    FROM documento_interpretativo d
                    WHERE d.organismo_emisor = 'BDNS'
                      AND d.tipo_fuente = 'bdns'
                      AND d.referencia = :referencia
                    LIMIT 1
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Convocatoria BDNS no encontrada"})

        result = {
            "referencia": row["referencia"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "texto": row["texto"],
            "url_fuente": row["url_fuente"],
            "row_completeness": "partial",
            "row_provenance": "official_best_effort",
        }
        record_retrieval_query_audit(
            request,
            path="/v1/bdns/{referencia}",
            query_text=referencia,
            tool_name="get_bdns",
            items=[result],
            total=1,
            verified=True,
            completeness="parcial",
        )
        return result
