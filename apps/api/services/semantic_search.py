"""Hybrid search service: fulltext + vector embeddings with RRF fusion.

Reciprocal Rank Fusion (RRF):
    score = rank_ft / (k + rank_ft) + rank_vec / (k + rank_vec)
    where k = 60 (standard constant from Lin & Yang, 2009)
"""

from __future__ import annotations

import logging
from typing import Any

from db import db_session
from sqlalchemy import text

from services.search import _build_fragment, _build_tsquery_sql, _is_postgres

logger = logging.getLogger(__name__)

_RRF_K = 60


def _get_embedding_model():
    """Lazy-load embedding model from workers package."""
    try:
        from apps.workers.embeddings import embed_single

        return embed_single
    except ImportError:
        logger.warning("Embeddings not available — hybrid search falls back to fulltext")
        return None


def hybrid_search_legislacion(
    q: str,
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
    hybrid_weight: float = 0.3,
    limit: int = 10,
):
    """Hybrid search combining fulltext (ts_rank) and vector similarity via RRF.

    hybrid_weight controls the vector component:
        0.0 = pure fulltext (RRF vec weight = 0)
        0.3 = optimal mix (fulltext + vector)
        1.0 = pure vector (RRF ft weight = 0)
    """
    with db_session() as db:
        if not _is_postgres(db):
            return _hybrid_sqlite(db, q, norma, fuente, ambito, tipo, vigente_en, limit)

        return _hybrid_pg(db, q, norma, fuente, ambito, tipo, vigente_en, hybrid_weight, limit)


def _hybrid_pg(
    db,
    q: str,
    norma: str | None,
    fuente: str | None,
    ambito: str | None,
    tipo: str | None,
    vigente_en: str | None,
    hybrid_weight: float,
    limit: int,
) -> dict[str, Any]:
    """Postgres hybrid branch: fulltext + vector RRF fusion."""
    from apps.workers.embeddings import embed_single

    ft_weight = 1.0 - hybrid_weight
    vec_weight = hybrid_weight

    # Step 1: Fulltext search
    ft_results = _fulltext_rank_pg(db, q, norma, fuente, ambito, tipo, vigente_en, limit * 2)

    # Step 2: Vector search (if available)
    vec_results: list[dict[str, Any]] = []
    embed_fn = embed_single
    if embed_fn and hybrid_weight > 0:
        vec_results = _vector_rank_pg(db, q, norma, fuente, ambito, tipo, vigente_en, limit * 2)

    # Step 3: RRF fusion
    fused = _rrf_fuse(ft_results, vec_results, ft_weight, vec_weight, limit)

    return {
        "q": q,
        "resultados": fused,
        "search_mode": "hybrid"
        if hybrid_weight > 0 and hybrid_weight < 1.0
        else ("vector" if hybrid_weight >= 1.0 else "fulltext"),
        "weights": {"fulltext": round(ft_weight, 2), "vector": round(vec_weight, 2)},
    }


def _fulltext_rank_pg(db, q: str, norma, fuente, ambito, tipo, vigente_en, limit: int) -> list[dict[str, Any]]:
    """Run fulltext search reusing _search_legislacion_pg from search.py."""
    from services.search import _search_legislacion_pg

    # _search_legislacion_pg returns {"q": ..., "resultados": [...]}
    resp = _search_legislacion_pg(db, q, norma, fuente, ambito, tipo, vigente_en)
    results = resp.get("resultados", []) if isinstance(resp, dict) else resp

    # Transform results to hybrid format: add source and doc_id
    for r in results:
        r["source"] = "fulltext"
        if "doc_id" not in r and "documento_origen_id" in r:
            r["doc_id"] = r["documento_origen_id"]
        # Ensure chunk_texto exists
        if "chunk_texto" not in r:
            r["chunk_texto"] = r.get("texto", "")

    return results[:limit]


def _hybrid_sqlite(db, q, norma, fuente, ambito, tipo, vigente_en, limit) -> dict[str, Any]:
    """SQLite fallback: fulltext only (no vector support)."""
    from services.search import _search_legislacion_sqlite

    result = _search_legislacion_sqlite(db, q, norma, fuente, ambito, tipo, vigente_en)
    return {
        "q": q,
        "resultados": result.get("resultados", [])[:limit],
        "search_mode": "fulltext",
        "weights": {"fulltext": 1.0, "vector": 0.0},
        "note": "SQLite does not support vector search",
    }


def _vector_rank_pg(db, q: str, norma, fuente, ambito, tipo, vigente_en, limit: int) -> list[dict[str, Any]]:
    """Run vector similarity search and return ranked results."""
    from apps.workers.embeddings import embed_texts

    # Generate query embedding
    query_vec = embed_texts([q])
    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec[0])

    params: dict = {"query_vec": f"[{query_vec_str}]", "limit": limit, "vigente_en": vigente_en}

    if norma is not None:
        params["norma"] = norma
    if fuente is not None:
        params["fuente"] = fuente
    if ambito is not None:
        params["ambito"] = ambito
    if tipo is not None:
        params["tipo"] = tipo

    filter_parts = ["cf.documento_origen_tipo = 'legislacion'"]
    if norma:
        filter_parts.append("n.codigo = :norma")
    if fuente:
        filter_parts.append("n.tipo_fuente = :fuente")
    if ambito:
        filter_parts.append("n.ambito = :ambito")
    if tipo:
        filter_parts.append("a.tipo = :tipo")

    where_clause = " AND ".join(filter_parts)

    query = text(
        f"""
        SELECT DISTINCT ON (cf.documento_origen_id)
            cf.documento_origen_id AS doc_id,
            n.codigo,
            a.numero,
            a.tipo,
            va.texto,
            va.vigente_desde,
            va.vigente_hasta,
            1.0 - (cf.embedding <=> :query_vec) AS similarity,
            cf.texto AS chunk_texto,
            cf.id AS chunk_id,
            cf.chunk_type,
            cf.titulo AS chunk_titulo,
            n.boe_id,
            n.eli_uri
        FROM documento_fragmento cf
        JOIN articulo a ON a.id = cf.documento_origen_id
        JOIN norma n ON n.id = a.norma_id
        JOIN version_articulo va ON va.articulo_id = a.id
        WHERE {where_clause}
          AND cf.embedding IS NOT NULL
          AND va.vigente_desde = (
              SELECT MAX(v2.vigente_desde)
              FROM version_articulo v2
              JOIN articulo a2 ON a2.id = v2.articulo_id
              WHERE a2.id = cf.documento_origen_id
                AND (:vigente_en IS NULL OR (
                    v2.vigente_desde <= :vigente_en
                    AND (v2.vigente_hasta IS NULL OR v2.vigente_hasta >= :vigente_en)
                ))
          )
        ORDER BY cf.documento_origen_id, similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        sim = row.get("similarity")
        if sim is not None:
            sim = float(sim)

        chunk_texto = row.get("chunk_texto")
        fragmento = _build_fragment(chunk_texto, q) if chunk_texto else None

        results.append(
            {
                "doc_id": row["doc_id"],
                "tipo": row["tipo"],
                "norma": row["codigo"],
                "numero": row["numero"],
                "texto": row["texto"],
                "fragmento": fragmento or _build_fragment(row["texto"], q),
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
                "rank": round(sim, 4) if sim is not None else None,
                "chunk_texto": chunk_texto,
                "chunk_id": row.get("chunk_id"),
                "fuente_norma": row.get("boe_id") or row.get("eli_uri"),
                "source_url": (
                    f"https://www.boe.es/diario_boe/txt.php?id={row['boe_id']}"
                    if row.get("boe_id")
                    else row.get("eli_uri")
                ),
                "source": "vector",
            }
        )

    return results


def _rrf_fuse(
    ft_results: list[dict],
    vec_results: list[dict],
    ft_weight: float,
    vec_weight: float,
    limit: int,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion to combine fulltext and vector rankings.

    RRF formula: score = w_ft * rank_ft/(k+rank_ft) + w_vec * rank_vec/(k+rank_vec)
    """
    rrf_scores: dict[int, dict[str, Any]] = {}

    for rank, item in enumerate(ft_results, 1):
        doc_id = item["doc_id"]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {
                "item": item,
                "rrf_score": 0.0,
                "has_ft": False,
                "has_vec": False,
            }
        if ft_weight > 0:
            rrf_scores[doc_id]["rrf_score"] += ft_weight * (1.0 / (_RRF_K + rank))
            rrf_scores[doc_id]["has_ft"] = True

    for rank, item in enumerate(vec_results, 1):
        doc_id = item["doc_id"]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {
                "item": item,
                "rrf_score": 0.0,
                "has_ft": False,
                "has_vec": False,
            }
        if vec_weight > 0:
            rrf_scores[doc_id]["rrf_score"] += vec_weight * (1.0 / (_RRF_K + rank))
            rrf_scores[doc_id]["has_vec"] = True

    # Sort by fused score descending
    sorted_items = sorted(
        rrf_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    results = []
    for entry in sorted_items[:limit]:
        item = entry["item"].copy()
        item["rrf_score"] = round(entry["rrf_score"], 6)
        item["rrf_sources"] = []
        if entry["has_ft"]:
            item["rrf_sources"].append("fulltext")
        if entry["has_vec"]:
            item["rrf_sources"].append("vector")

        results.append(item)

    return results


def hybrid_search_doctrina(
    q: str,
    tipo: str | None = None,
    desde: str | None = None,
    organismo_emisor: str | None = None,
    hybrid_weight: float = 0.3,
    limit: int = 10,
):
    """Hybrid search for doctrine: fulltext (ts_rank) + vector similarity via RRF."""
    with db_session() as db:
        if not _is_postgres(db):
            return _hybrid_doctrina_sqlite(db, q, tipo, desde, organismo_emisor, limit)

        return _hybrid_doctrina_pg(db, q, tipo, desde, organismo_emisor, hybrid_weight, limit)


def _hybrid_doctrina_pg(
    db,
    q: str,
    tipo: str | None,
    desde: str | None,
    organismo_emisor: str | None,
    hybrid_weight: float,
    limit: int,
) -> dict[str, Any]:
    """Postgres hybrid branch for doctrine: fulltext + vector RRF fusion."""
    from apps.workers.embeddings import embed_single

    ft_weight = 1.0 - hybrid_weight
    vec_weight = hybrid_weight

    # Step 1: Fulltext search
    ft_results = _doctrina_fulltext_pg(db, q, tipo, desde, organismo_emisor, limit * 2)

    # Step 2: Vector search (if available)
    vec_results: list[dict[str, Any]] = []
    embed_fn = embed_single
    if embed_fn and hybrid_weight > 0:
        vec_results = _doctrina_vector_pg(db, q, tipo, desde, organismo_emisor, limit * 2)

    # Step 3: RRF fusion
    fused = _rrf_fuse_doctrina(ft_results, vec_results, ft_weight, vec_weight, limit)

    return {
        "q": q,
        "resultados": fused,
        "search_mode": "hybrid"
        if hybrid_weight > 0 and hybrid_weight < 1.0
        else ("vector" if hybrid_weight >= 1.0 else "fulltext"),
        "weights": {"fulltext": round(ft_weight, 2), "vector": round(vec_weight, 2)},
    }


def _doctrina_fulltext_pg(db, q: str, tipo, desde, organismo_emisor, limit: int) -> list[dict[str, Any]]:
    """Fulltext search over documento_interpretativo with ts_rank."""
    params: dict = {}

    if q and q.strip():
        tsquery, tsquery_params = _build_tsquery_sql(q)
        params.update(tsquery_params)
        if tsquery:
            search_filter = "d.search_vector @@ " + tsquery
            rank_expr = "ts_rank(d.search_vector, " + tsquery + ")"
        else:
            search_filter = "LOWER(d.texto) LIKE LOWER(:term)"
            params["term"] = f"%{q}%"
            rank_expr = "0.0"
    else:
        search_filter = "1=1"
        rank_expr = "0.0"

    filters = [search_filter]
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
        LIMIT :limit
        """
    )
    params["limit"] = limit

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        chunk_rank = row.get("chunk_rank")
        if chunk_rank is not None and float(chunk_rank) > 0:
            chunk_rank = float(chunk_rank)

        texto = row["texto"] or ""
        fragmento = (
            _build_fragment(texto, q) if texto and chunk_rank else (texto[:220] + ("..." if len(texto) > 220 else ""))
        )

        results.append(
            {
                "doc_id": row["id"],
                "referencia": row["referencia"],
                "tipo_documento": row["tipo_documento"],
                "organismo_emisor": row["organismo_emisor"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "fragmento": fragmento or "",
                "nivel_enlace": float(row["nivel_enlace"] or 0),
                "norma": row["norma"],
                "numero": row["numero"],
                "rank": round(chunk_rank, 4) if chunk_rank else None,
                "source_url": row.get("url_fuente"),
                "source": "fulltext",
            }
        )

    return results


def _doctrina_vector_pg(db, q: str, tipo, desde, organismo_emisor, limit: int) -> list[dict[str, Any]]:
    """Vector similarity search over documento_interpretativo."""
    from apps.workers.embeddings import embed_texts

    query_vec = embed_texts([q])
    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec[0])

    params: dict = {"query_vec": f"[{query_vec_str}]", "limit": limit}

    filters = ["d.embedding IS NOT NULL"]
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
            1.0 - (d.embedding <=> :query_vec) AS similarity,
            MAX(da.confianza_enlace) AS nivel_enlace,
            n.codigo AS norma,
            a.numero
        FROM documento_interpretativo d
        LEFT JOIN documento_articulo da ON da.documento_id = d.id
        LEFT JOIN articulo a ON a.id = da.articulo_id
        LEFT JOIN norma n ON n.id = a.norma_id
        WHERE {where_clause}
        GROUP BY d.id, d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto, d.url_fuente, n.codigo, a.numero
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        sim = row.get("similarity")
        if sim is not None:
            sim = float(sim)

        texto = row["texto"] or ""
        fragmento = _build_fragment(texto, q) if sim and texto else (texto[:220] + ("..." if len(texto) > 220 else ""))

        results.append(
            {
                "doc_id": row["id"],
                "referencia": row["referencia"],
                "tipo_documento": row["tipo_documento"],
                "organismo_emisor": row["organismo_emisor"],
                "fecha": str(row["fecha"]) if row["fecha"] else None,
                "titulo": row["titulo"],
                "fragmento": fragmento or "",
                "nivel_enlace": float(row["nivel_enlace"] or 0),
                "norma": row["norma"],
                "numero": row["numero"],
                "rank": round(sim, 4) if sim is not None else None,
                "source_url": row.get("url_fuente"),
                "source": "vector",
            }
        )

    return results


def _rrf_fuse_doctrina(
    ft_results: list[dict],
    vec_results: list[dict],
    ft_weight: float,
    vec_weight: float,
    limit: int,
) -> list[dict[str, Any]]:
    """RRF fusion for doctrine results, keyed by doc_id."""
    rrf_scores: dict[int, dict[str, Any]] = {}

    for rank, item in enumerate(ft_results, 1):
        doc_id = item["doc_id"]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {
                "item": item,
                "rrf_score": 0.0,
                "has_ft": False,
                "has_vec": False,
            }
        if ft_weight > 0:
            rrf_scores[doc_id]["rrf_score"] += ft_weight * (1.0 / (_RRF_K + rank))
            rrf_scores[doc_id]["has_ft"] = True

    for rank, item in enumerate(vec_results, 1):
        doc_id = item["doc_id"]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {
                "item": item,
                "rrf_score": 0.0,
                "has_ft": False,
                "has_vec": False,
            }
        if vec_weight > 0:
            rrf_scores[doc_id]["rrf_score"] += vec_weight * (1.0 / (_RRF_K + rank))
            rrf_scores[doc_id]["has_vec"] = True

    sorted_items = sorted(
        rrf_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    results = []
    for entry in sorted_items[:limit]:
        item = entry["item"].copy()
        item["rrf_score"] = round(entry["rrf_score"], 6)
        item["rrf_sources"] = []
        if entry["has_ft"]:
            item["rrf_sources"].append("fulltext")
        if entry["has_vec"]:
            item["rrf_sources"].append("vector")

        # Remove internal doc_id from output
        item.pop("doc_id", None)
        results.append(item)

    return results


def _hybrid_doctrina_sqlite(db, q, tipo, desde, organismo_emisor, limit) -> dict[str, Any]:
    """SQLite fallback: fulltext only (no vector support)."""
    from routers.doctrina import _buscar_doctrina_sqlite

    result = _buscar_doctrina_sqlite(db, q, tipo, desde, organismo_emisor)
    return {
        "q": q,
        "resultados": result.get("resultados", [])[:limit],
        "search_mode": "fulltext",
        "weights": {"fulltext": 1.0, "vector": 0.0},
        "note": "SQLite does not support vector search",
    }
