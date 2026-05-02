from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from db import db_session
from schemas import (
    DoctrinaDetail as DoctrinaDetailSchema,
    DoctrinaSearchResponse,
)
from services.search import _build_tsquery_sql, _chunk_rank_boost, _build_fragment
from services.query_audit import get_query_audit_service
from services.semantic_search import hybrid_search_doctrina


def _buscar_normas_boe(db, q: str, limit: int = 5) -> list[dict]:
    params = {"term_like": f"%{q}%", "limit": limit}
    ley_match = __import__("re").search(r"\b(\d{1,4})\s*/\s*(\d{4})\b", q)
    numero = ley_match.group(1) if ley_match else None
    anio = ley_match.group(2) if ley_match else None
    params["numero"] = numero
    params["anio"] = anio

    query = text(
        """
        SELECT
            n.boe_id AS referencia,
            n.tipo_documento,
            'BOE' AS organismo_emisor,
            n.vigente_desde AS fecha,
            n.titulo,
            n.codigo AS norma,
            a.numero,
            n.eli_uri AS source_url,
            COALESCE(va.texto, '') AS texto
        FROM norma n
        LEFT JOIN articulo a ON a.norma_id = n.id
        LEFT JOIN version_articulo va
          ON va.articulo_id = a.id
         AND va.vigente_hasta IS NULL
        WHERE n.tipo_fuente = 'boe'
          AND (
            LOWER(n.titulo) LIKE LOWER(:term_like)
            OR LOWER(n.codigo) LIKE LOWER(:term_like)
            OR LOWER(n.boe_id) LIKE LOWER(:term_like)
            OR (:numero IS NOT NULL AND :anio IS NOT NULL AND LOWER(n.titulo) LIKE LOWER('% ' || :numero || '/' || :anio || '%'))
            OR (:numero IS NOT NULL AND :anio IS NOT NULL AND LOWER(COALESCE(n.eli_uri, '')) LIKE LOWER('%/' || :anio || '/%/' || :numero))
            OR LOWER(COALESCE(va.texto, '')) LIKE LOWER(:term_like)
          )
        ORDER BY n.vigente_desde DESC, a.numero ASC
        LIMIT :limit
        """
    )

    rows = db.execute(query, params).mappings()
    return [
        {
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "titulo": row["titulo"],
            "nivel_enlace": 1.0,
            "norma": row["norma"],
            "numero": row["numero"],
            "fragmento": _build_fragment(row["texto"], q) if row["texto"] else row["titulo"],
            "source_url": row["source_url"],
        }
        for row in rows
    ]

def _build_doctrina_audit_chunks(result: dict) -> list[dict]:
    chunks: list[dict] = []
    for item in result.get("resultados", []):
        chunks.append(
            {
                "referencia": item.get("referencia"),
                "tipo_documento": item.get("tipo_documento"),
                "organismo_emisor": item.get("organismo_emisor"),
                "source_url": item.get("source_url"),
                "norma": item.get("norma"),
                "numero": item.get("numero"),
            }
        )
    return chunks


router = APIRouter(prefix="/v1/doctrina", tags=["doctrina"])


@router.get(
    "/buscar",
    operation_id="buscar_doctrina",
    response_model=DoctrinaSearchResponse,
    summary="Buscar doctrina interpretativa",
)
async def buscar_doctrina(
    request: Request,
    q: str = Query(
        ..., min_length=1, description="Termino de busqueda en texto de doctrina"
    ),
    tipo: str | None = Query(
        None,
        description="Filtrar por tipo (consulta_vinculante, resolucion_teac, etc.)",
    ),
    desde: str | None = Query(None, description="Fecha minima (YYYY-MM-DD)"),
    organismo_emisor: str | None = Query(
        None, description="Filtrar por organismo (DGT, TEAC, etc.)"
    ),
    include_boe: bool = Query(True, description="Incluir normas BOE relacionadas cuando apliquen"),
):
    with db_session() as db:
        is_postgres = db.bind.dialect.name == "postgresql"

        if is_postgres:
            result = _buscar_doctrina_pg(db, q, tipo, desde, organismo_emisor)
        else:
            result = _buscar_doctrina_sqlite(db, q, tipo, desde, organismo_emisor)

        if include_boe and (organismo_emisor is None or organismo_emisor.upper() == "BOE"):
            result["resultados"].extend(_buscar_normas_boe(db, q))

        get_query_audit_service().record_query(
            request_id=request.headers.get("x-request-id") or request.headers.get("X-Request-ID") or "unknown",
            user_id=request.headers.get("x-user-id") or request.headers.get("X-User-ID"),
            path="/v1/doctrina/buscar",
            query_text=q,
            retrieved_chunks=_build_doctrina_audit_chunks(result),
            response_summary=f"resultados={len(result.get('resultados', []))}",
        )
        return result


def _buscar_doctrina_pg(db, q, tipo, desde, organismo_emisor):
    """Postgres branch: search over documento_fragmento chunks with ts_rank.

    Falls back to direct search on documento_interpretativo if the
    documento_fragmento table does not exist (not yet backfilled).
    """
    params: dict = {}
    tsquery_str, _ = _build_tsquery_sql(q)
    use_ts_rank = bool(tsquery_str)

    exact_reference = q.strip()

    if use_ts_rank:
        chunk_filter = (
            "(df.search_vector @@ ("
            + tsquery_str
            + ") OR LOWER(d.referencia) = LOWER(:exact_referencia))"
        )
        rank_expr = (
            "CASE WHEN LOWER(d.referencia) = LOWER(:exact_referencia) THEN 1.0 "
            "ELSE ts_rank(df.search_vector, ("
            + tsquery_str
            + ")) END"
        )
        params["exact_referencia"] = exact_reference
    else:
        chunk_filter = "(df.texto ILIKE :term OR d.titulo ILIKE :term OR d.referencia ILIKE :term)"
        params["term"] = f"%{q}%"
        rank_expr = "0.0"

    chunk_filters = [chunk_filter, "df.documento_origen_tipo = 'doctrina'"]

    if tipo is not None:
        chunk_filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    if desde is not None:
        chunk_filters.append("d.fecha >= :desde")
        params["desde"] = desde
    if organismo_emisor is not None:
        chunk_filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        params["organismo_emisor"] = organismo_emisor

    where_clause = " AND ".join(chunk_filters)

    try:
        query = text(
            f"""
            SELECT
                df.documento_origen_id AS d_id,
                d.referencia,
                d.tipo_documento,
                d.organismo_emisor,
                d.fecha,
                d.titulo,
                d.url_fuente,
                df.texto AS chunk_texto,
                df.id AS chunk_id,
                {rank_expr} AS chunk_rank,
                MAX(da.confianza_enlace) AS nivel_enlace,
                n.codigo AS norma,
                a.numero
            FROM documento_fragmento df
            JOIN documento_interpretativo d ON d.id = df.documento_origen_id
            LEFT JOIN documento_articulo da ON da.documento_id = d.id
            LEFT JOIN articulo a ON a.id = da.articulo_id
            LEFT JOIN norma n ON n.id = a.norma_id
            WHERE {where_clause}
            GROUP BY d.id, df.id, df.texto, n.codigo, a.numero
            ORDER BY chunk_rank DESC
            LIMIT 20
            """
        )

        rows = db.execute(query, params).mappings()
        results = []
        for row in rows:
            chunk_rank = row.get("chunk_rank")
            if chunk_rank is not None and use_ts_rank:
                has_chunks = bool(row.get("chunk_id"))
                chunk_rank = _chunk_rank_boost(has_chunks, float(chunk_rank))

            chunk_texto = row.get("chunk_texto")
            fragmento = None
            if chunk_texto and use_ts_rank:
                fragmento = _build_fragment(chunk_texto, q)
            elif chunk_texto:
                fragmento = chunk_texto[:220] + ("..." if len(chunk_texto) > 220 else "")

            results.append({
                "referencia": row["referencia"],
                "tipo_documento": row["tipo_documento"],
                "organismo_emisor": row["organismo_emisor"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "nivel_enlace": float(row["nivel_enlace"] or 0),
                "norma": row["norma"],
                "numero": row["numero"],
                "fragmento": fragmento or "",
                "source_url": row.get("url_fuente"),
            })

        return {"q": q, "resultados": results}

    except Exception:
        # documento_fragmento table does not exist — fall back to direct search
        return _buscar_doctrina_pg_fallback(db, q, tipo, desde, organismo_emisor, params, use_ts_rank)


def _buscar_doctrina_pg_fallback(db, q, tipo, desde, organismo_emisor, params, use_ts_rank):
    """Fallback search over documento_interpretativo when documento_fragmento is missing."""
    fallback_params: dict = {}
    exact_reference = q.strip()
    if use_ts_rank:
        tsquery_str, _ = _build_tsquery_sql(q)
        search_filter = (
            "(d.search_vector @@ ("
            + tsquery_str
            + ") OR LOWER(d.referencia) = LOWER(:exact_referencia))"
        )
        rank_expr = (
            "CASE WHEN LOWER(d.referencia) = LOWER(:exact_referencia) THEN 1.0 "
            "ELSE ts_rank(d.search_vector, ("
            + tsquery_str
            + ")) END"
        )
        fallback_params["exact_referencia"] = exact_reference
    else:
        search_filter = "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term) OR LOWER(d.referencia) LIKE LOWER(:term))"
        fallback_params["term"] = f"%{q}%"
        rank_expr = "0.0"

    filters = [search_filter]
    if tipo is not None:
        filters.append("d.tipo_documento = :tipo")
        fallback_params["tipo"] = tipo
    if desde is not None:
        filters.append("d.fecha >= :desde")
        fallback_params["desde"] = desde
    if organismo_emisor is not None:
        filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        fallback_params["organismo_emisor"] = organismo_emisor

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

    rows = db.execute(query, fallback_params).mappings()
    results = []
    for row in rows:
        chunk_rank = row.get("chunk_rank")
        if chunk_rank is not None and use_ts_rank:
            chunk_rank = float(chunk_rank)

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


def _buscar_doctrina_sqlite(db, q, tipo, desde, organismo_emisor):
    """SQLite branch: legacy ILIKE search over documento_interpretativo."""
    params: dict = {"term_like": f"%{q}%"}
    where_parts = [
        "(LOWER(d.texto) LIKE LOWER(:term_like) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term_like) OR LOWER(d.referencia) LIKE LOWER(:term_like))"
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


@router.get(
    "/{referencia:path}",
    operation_id="get_doctrina",
    response_model=DoctrinaDetailSchema,
)
async def get_doctrina(referencia: str):
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
                status_code=404, detail={"error": "Documento no encontrado"}
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


@router.get("/buscar/hybrid", operation_id="buscar_doctrina_hybrid")
async def buscar_doctrina_hybrid(
    q: str = Query(..., min_length=1, description="Termino de busqueda en texto de doctrina"),
    tipo: str | None = Query(None, description="Filtrar por tipo (consulta_vinculante, resolucion_teac, etc.)"),
    desde: str | None = Query(None, description="Fecha minima (YYYY-MM-DD)"),
    organismo_emisor: str | None = Query(None, description="Filtrar por organismo (DGT, TEAC, etc.)"),
    hybrid_weight: float = Query(0.3, ge=0.0, le=1.0, description="Peso busqueda vectorial (0.0=fulltext, 0.3=optimo, 1.0=vectorial)"),
    limit: int = Query(10, ge=1, le=50, description="Numero maximo de resultados"),
):
    result = hybrid_search_doctrina(
        q, tipo, desde, organismo_emisor, hybrid_weight, limit
    )
    return JSONResponse(content=result)
