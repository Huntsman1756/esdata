"""Router de doctrina DGT especifica para rendimientos mobiliarios.

Endpoints:
  - GET /v1/doctrina/dgt/{referencia} — consulta de consulta vinculante
  - GET /v1/doctrina/dgt?busqueda=... — FTS sobre doctrina DGT filtrada por ambito

El router reutiliza los schemas existentes de `doctrina` y la base
de datos compartida en `documento_interpretativo`.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text

from db import db_session
from schemas import (
    DoctrinaDetail as DoctrinaDetailSchema,
    DoctrinaSearchResponse,
)
from services.search import _build_tsquery_sql, _chunk_rank_boost, _build_fragment
from services.semantic_search import hybrid_search_doctrina

router = APIRouter(prefix="/v1/doctrina/dgt", tags=["dgt-rendimientos"])


@router.get(
    "/buscar",
    operation_id="buscar_dgt_rendimientos",
    response_model=DoctrinaSearchResponse,
    summary="Buscar doctrina DGT sobre rendimientos mobiliarios",
)
async def buscar_dgt_rendimientos(
    q: str = Query(
        ..., min_length=1, description="Termino de busqueda en texto de doctrina DGT"
    ),
    tipo: str | None = Query(
        None,
        description="Filtrar por tipo (consulta_vinculante, resolucion_teac, etc.)",
    ),
    desde: str | None = Query(None, description="Fecha minima (YYYY-MM-DD)"),
    organismo_emisor: str | None = Query(
        None, description="Filtrar por organismo (DGT, TEAC, etc.)",
    ),
):
    """Buscar en la doctrina DGT filtrada por ambito de rendimientos mobiliarios.

    Reutiliza la infraestructura de busqueda del router doctrina existente,
    pero filtra por tipo_fuente='dgt' y organismo_emisor='DGT' en la tabla
    documento_interpretativo.
    """
    with db_session() as db:
        is_postgres = db.bind.dialect.name == "postgresql"

        if is_postgres:
            result = _buscar_dgt_rendimientos_pg(db, q, tipo, desde, organismo_emisor)
        else:
            result = _buscar_dgt_rendimientos_sqlite(db, q, tipo, desde, organismo_emisor)

        return result


@router.get(
    "/{referencia:path}",
    operation_id="get_dgt_doctrina",
    response_model=DoctrinaDetailSchema,
    summary="Consulta de consulta vinculante DGT",
)
async def get_dgt_doctrina(referencia: str):
    """Obtiene una consulta vinculante DGT por referencia (ej: V0091-18).

    Este endpoint debe registrarse ANTES del catch-all /{referencia:path}
    del router doctrina para evitar que sea interceptado.
    """
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT
                        d.id,
                        d.referencia,
                        d.tipo_documento,
                        d.organismo_emisor,
                        d.texto
                    FROM documento_interpretativo d
                    WHERE d.referencia = :referencia
                      AND d.tipo_fuente = 'dgt'
                      AND d.organismo_emisor = 'DGT'
                    LIMIT 1
                    """
                ),
                {"referencia": referencia},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Consulta DGT {referencia} no encontrada"},
            )

        linked_articles = list(
            db.execute(
                text(
                    """
                    SELECT
                        n.codigo AS norma,
                        a.numero,
                        da.metodo_enlace,
                        da.confianza_enlace
                    FROM documento_articulo da
                    JOIN articulo a ON a.id = da.articulo_id
                    JOIN norma n ON n.id = a.norma_id
                    WHERE da.documento_id = :documento_id
                    ORDER BY da.confianza_enlace DESC, n.codigo, a.numero
                    """
                ),
                {"documento_id": row["id"]},
            ).mappings()
        )

        max_confidence = max(
            (float(item["confianza_enlace"]) for item in linked_articles), default=0.0
        )
        has_strong_anchor = max_confidence >= 0.85
        has_any_anchor = bool(linked_articles)

        return {
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "texto": row["texto"],
            "articulos_relacionados": [
                {
                    "norma": item["norma"],
                    "numero": item["numero"],
                    "metodo_enlace": item["metodo_enlace"],
                    "confianza_enlace": float(item["confianza_enlace"]),
                }
                for item in linked_articles
            ],
            "confianza": {
                "nivel": 2 if has_strong_anchor else (1 if has_any_anchor else 0),
                "fuentes": [row["referencia"]],
                "aviso": None
                if has_any_anchor
                else "Criterio sin anclaje normativo suficiente",
            },
        }


def _buscar_dgt_rendimientos_pg(db, q, tipo, desde, organismo_emisor):
    """Postgres branch: FTS sobre documento_interpretativo filtrado por DGT."""
    params: dict = {}
    tsquery_str, _ = _build_tsquery_sql(q)

    if tsquery_str:
        where_filter = "d.search_vector @@ (" + tsquery_str + ")"
        rank_expr = "ts_rank(d.search_vector, (" + tsquery_str + "))"
    else:
        where_filter = "LOWER(d.texto) LIKE LOWER(:term)"
        params["term"] = f"%{q}%"
        rank_expr = "0.0"

    filters = [where_filter, "d.tipo_fuente = 'dgt'", "d.organismo_emisor = 'DGT'"]

    if tipo is not None:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    if desde is not None:
        filters.append("d.fecha >= :desde")
        params["desde"] = desde
    if organismo_emisor is not None:
        filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        params["organismo_emisor"] = organismo_emisor

    where_clause = " AND ".join(filters)

    query = text(
        f"""
        SELECT
            d.id,
            d.referencia,
            d.tipo_documento,
            d.organismo_emisor,
            d.fecha,
            d.titulo,
            d.texto,
            d.url_fuente,
            {rank_expr} AS chunk_rank,
            MAX(da.confianza_enlace) AS nivel_enlace,
            n.codigo AS norma,
            a.numero
        FROM documento_interpretativo d
        LEFT JOIN documento_articulo da ON da.documento_id = d.id
        LEFT JOIN articulo a ON a.id = da.articulo_id
        LEFT JOIN norma n ON n.id = a.norma_id
        WHERE {where_clause}
        GROUP BY d.id, d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto, d.url_fuente, n.codigo, a.numero
        ORDER BY chunk_rank DESC
        LIMIT 20
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        chunk_rank = row.get("chunk_rank")
        if chunk_rank is not None and tsquery_str:
            chunk_rank = _chunk_rank_boost(True, float(chunk_rank))

        texto = row["texto"] or ""
        results.append({
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "nivel_enlace": float(row["nivel_enlace"] or 0),
            "norma": row["norma"],
            "numero": row["numero"],
            "fragmento": _build_fragment(texto, q) if texto else "",
            "source_url": row.get("url_fuente"),
        })

    return {"q": q, "resultados": results}


def _buscar_dgt_rendimientos_sqlite(db, q, tipo, desde, organismo_emisor):
    """SQLite branch: ILIKE sobre documento_interpretativo filtrado por DGT."""
    params: dict = {"term_like": f"%{q}%"}
    where_parts = [
        "(LOWER(d.texto) LIKE LOWER(:term_like) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term_like))",
        "d.tipo_fuente = 'dgt'",
        "d.organismo_emisor = 'DGT'",
    ]

    if tipo is not None:
        where_parts.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    if desde is not None:
        where_parts.append("d.fecha >= :desde")
        params["desde"] = desde
    if organismo_emisor is not None:
        where_parts.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        params["organismo_emisor"] = organismo_emisor

    where_clause = " AND ".join(where_parts)

    query = text(
        f"""
        SELECT
            d.referencia,
            d.tipo_documento,
            d.organismo_emisor,
            d.fecha,
            d.titulo,
            d.texto,
            d.url_fuente,
            n.codigo AS norma,
            a.numero,
            MAX(da.confianza_enlace) AS nivel_enlace
        FROM documento_interpretativo d
        LEFT JOIN documento_articulo da ON da.documento_id = d.id
        LEFT JOIN articulo a ON a.id = da.articulo_id
        LEFT JOIN norma n ON n.id = a.norma_id
        WHERE {where_clause}
        GROUP BY d.id, d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto, d.url_fuente, n.codigo, a.numero
        ORDER BY d.fecha DESC
        LIMIT 20
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        texto = row["texto"] or ""
        results.append({
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "nivel_enlace": float(row["nivel_enlace"] or 0),
            "norma": row["norma"],
            "numero": row["numero"],
            "fragmento": texto[:220] + ("..." if len(texto) > 220 else ""),
            "source_url": row.get("url_fuente"),
        })

    return {"q": q, "resultados": results}



