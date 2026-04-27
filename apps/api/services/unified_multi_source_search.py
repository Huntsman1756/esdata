"""Unified multi-source retrieval with RRF fusion across all data sources.

Searches across legislacion, doctrina, pgc_cuenta, aeat_modelo, screening_entries,
empresa, norma, and articulo tables. Each source can be filtered via the
``sources`` parameter. Results are fused via Reciprocal Rank Fusion (RRF).

Supported source types:
    - legislacion: version_articulo + documento_fragmento (fulltext + vector)
    - doctrina: documento_interpretativo (fulltext + vector)
    - pgc: pgc_cuenta (fulltext + vector)
    - modelos: aeat_modelo (fulltext + vector)
    - screening: screening_entries (fulltext + vector)
    - entities: empresa (fulltext + vector)
    - norms: norma (fulltext + vector)
    - articles: articulo (fulltext + vector)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from db import db_session
from services.search import _is_postgres

logger = logging.getLogger(__name__)

_RRF_K = 60


def _get_embed_fn():
    """Lazy-load embedding function from workers package."""
    try:
        from apps.workers.embeddings import embed_single
        return embed_single
    except ImportError:
        logger.warning("Embeddings not available — vector search falls back to fulltext")
        return None


def unified_multi_source_search(
    q: str,
    sources: list[str] | None = None,
    hybrid_weight: float = 0.3,
    limit: int = 20,
) -> dict[str, Any]:
    """Unified search across all data sources with per-source filtering.

    Args:
        q: Search query text.
        sources: List of source types to search. If None, searches all.
        hybrid_weight: Weight for vector component (0.0=fulltext, 1.0=vector).
        limit: Max results per source before RRF fusion.

    Returns:
        Dict with fused results, source breakdown, and search metadata.
    """
    if sources is None:
        sources = [
            "legislacion", "doctrina", "pgc", "modelos",
            "screening", "entities", "norms", "articles",
        ]

    with db_session() as db:
        is_pg = _is_postgres(db)
        embed_fn = _get_embed_fn()
        hybrid_weight = max(0.0, min(1.0, hybrid_weight))
        ft_weight = 1.0 - hybrid_weight
        vec_weight = hybrid_weight

        all_source_results: dict[str, list[dict]] = {}
        source_ranked: list[dict[str, Any]] = []

        # Dispatch to each source
        source_handlers = {
            "legislacion": _search_legislacion_source,
            "doctrina": _search_doctrina_source,
            "pgc": _search_pgc_source,
            "modelos": _search_modelos_source,
            "screening": _search_screening_source,
            "entities": _search_entities_source,
            "norms": _search_norms_source,
            "articles": _search_articles_source,
        }

        for source in sources:
            handler = source_handlers.get(source)
            if handler is None:
                logger.warning("Unknown source type: %s", source)
                continue

            try:
                results = handler(
                    db, q, is_pg, embed_fn, hybrid_weight, limit
                )
                if results:
                    all_source_results[source] = results
                    source_ranked.extend(results)
            except Exception:
                logger.exception("Error searching source: %s", source)

        # RRF fuse across all sources
        fused = _rrf_fuse_multi(all_source_results, ft_weight, vec_weight, limit)

        return {
            "q": q,
            "sources_requested": sources,
            "sources_with_results": list(all_source_results.keys()),
            "resultados": fused,
            "source_breakdown": {
                src: len(res) for src, res in all_source_results.items()
            },
            "search_mode": "hybrid" if hybrid_weight > 0 and hybrid_weight < 1.0 else (
                "vector" if hybrid_weight >= 1.0 else "fulltext"
            ),
            "weights": {"fulltext": round(ft_weight, 2), "vector": round(vec_weight, 2)},
        }


# ---------------------------------------------------------------------------
# Per-source search handlers
# ---------------------------------------------------------------------------

def _search_legislacion_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search legislacion: version_articulo + documento_fragmento."""
    from services.semantic_search import hybrid_search_legislacion
    return hybrid_search_legislacion(
        q, hybrid_weight=hybrid_weight, limit=limit
    ).get("resultados", [])


def _search_doctrina_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search doctrina: documento_interpretativo."""
    from services.semantic_search import hybrid_search_doctrina
    return hybrid_search_doctrina(
        q, hybrid_weight=hybrid_weight, limit=limit
    ).get("resultados", [])


def _search_pgc_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search PGC cuentas: fulltext + vector on codigo + descripcion + grupo."""
    results = []

    # Fulltext search
    if hybrid_weight < 1.0:
        ft_results = _pgc_fulltext(db, q, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank

        results.extend(ft_results)

    # Vector search
    if hybrid_weight > 0 and embed_fn:
        vec_results = _pgc_vector(db, q, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank

        results.extend(vec_results)

    return results


def _search_modelos_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search modelos AEAT: fulltext + vector on codigo + nombre + impuesto."""
    results = []

    if hybrid_weight < 1.0:
        ft_results = _modelos_fulltext(db, q, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank

        results.extend(ft_results)

    if hybrid_weight > 0 and embed_fn:
        vec_results = _modelos_vector(db, q, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank

        results.extend(vec_results)

    return results


def _search_screening_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search screening entries: fulltext + vector on nombre + aliases + categorias."""
    results = []

    if hybrid_weight < 1.0:
        ft_results = _screening_fulltext(db, q, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank

        results.extend(ft_results)

    if hybrid_weight > 0 and embed_fn:
        vec_results = _screening_vector(db, q, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank

        results.extend(vec_results)

    return results


def _search_entities_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search empresa entities: fulltext + vector on nombre + nif."""
    results = []

    if hybrid_weight < 1.0:
        ft_results = _entities_fulltext(db, q, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank

        results.extend(ft_results)

    if hybrid_weight > 0 and embed_fn:
        vec_results = _entities_vector(db, q, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank

        results.extend(vec_results)

    return results


def _search_norms_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search normas: fulltext + vector on codigo + nombre + numero_boe + titulo."""
    results = []

    if hybrid_weight < 1.0:
        ft_results = _norms_fulltext(db, q, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank

        results.extend(ft_results)

    if hybrid_weight > 0 and embed_fn:
        vec_results = _norms_vector(db, q, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank

        results.extend(vec_results)

    return results


def _search_articles_source(db, q, is_pg, embed_fn, hybrid_weight, limit):
    """Search articulo: fulltext + vector on numero + titulo + contenido."""
    results = []

    if hybrid_weight < 1.0:
        ft_results = _articles_fulltext(db, q, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank

        results.extend(ft_results)

    if hybrid_weight > 0 and embed_fn:
        vec_results = _articles_vector(db, q, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank

        results.extend(vec_results)

    return results


# ---------------------------------------------------------------------------
# PGC fulltext + vector
# ---------------------------------------------------------------------------

def _pgc_build_search_text(row: dict) -> str:
    """Build searchable text from PGC cuenta row."""
    parts = []
    if row.get("codigo"):
        parts.append(row["codigo"])
    if row.get("descripcion"):
        parts.append(row["descripcion"])
    if row.get("grupo"):
        parts.append(row["grupo"])
    if row.get("clase"):
        parts.append(row["clase"])
    if row.get("tipo_cuenta"):
        parts.append(row["tipo_cuenta"])
    if row.get("nota"):
        parts.append(row["nota"])
    return " ".join(parts)


def _pgc_fulltext(db, q: str, limit: int) -> list[dict]:
    """PGC fulltext search using LIKE (no tsvector configured)."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(descripcion) LIKE :pgc_q{i}")
        params[f"pgc_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT id, codigo, descripcion, nivel, padre_codigo, grupo, clase,
               saldo_normal, tipo_cuenta, vigente, nota, created_at
        FROM pgc_cuenta
        WHERE {' OR '.join(conditions)}
          AND vigente = 1
        ORDER BY
            CASE WHEN LOWER(codigo) = :pgc_exact THEN 0 ELSE 1 END,
            LENGTH(descripcion) ASC
        LIMIT :limit
        """
    )
    params["pgc_exact"] = q_lower
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        search_text = _pgc_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "pgc",
            "source_id": r["id"],
            "codigo": r["codigo"],
            "descripcion": r["descripcion"],
            "nivel": r["nivel"],
            "grupo": r["grupo"],
            "clase": r["clase"],
            "tipo_cuenta": r["tipo_cuenta"],
            "search_text": search_text,
            "score": 1.0,
            "chunk_texto": search_text,
        })
    return results


def _pgc_vector(db, q: str, embed_fn, limit: int) -> list[dict]:
    """PGC vector search on codigo + descripcion + grupo."""
    try:
        query_vec = embed_fn(q)
    except Exception:
        return []

    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT id, codigo, descripcion, nivel, padre_codigo, grupo, clase,
               saldo_normal, tipo_cuenta, vigente, nota, created_at,
               1.0 - (embedding_384 <=> '[{query_vec_str}]') AS similarity
        FROM pgc_cuenta
        WHERE embedding_384 IS NOT NULL
          AND vigente = 1
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        search_text = _pgc_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "pgc",
            "source_id": r["id"],
            "codigo": r["codigo"],
            "descripcion": r["descripcion"],
            "nivel": r["nivel"],
            "grupo": r["grupo"],
            "clase": r["clase"],
            "tipo_cuenta": r["tipo_cuenta"],
            "search_text": search_text,
            "similarity": round(sim, 4),
            "chunk_texto": search_text,
        })
    return results


# ---------------------------------------------------------------------------
# Modelos AEAT fulltext + vector
# ---------------------------------------------------------------------------

def _modelos_build_search_text(row: dict) -> str:
    """Build searchable text from aeat_modelo row."""
    parts = []
    if row.get("codigo"):
        parts.append(row["codigo"])
    if row.get("nombre"):
        parts.append(row["nombre"])
    if row.get("impuesto"):
        parts.append(row["impuesto"])
    return " ".join(parts)


def _modelos_fulltext(db, q: str, limit: int) -> list[dict]:
    """Modelos AEAT fulltext search."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(nombre) LIKE :m_q{i}")
        params[f"m_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT id, codigo, nombre, periodo, impuesto, url_info, created_at
        FROM aeat_modelo
        WHERE {' OR '.join(conditions)}
        ORDER BY
            CASE WHEN LOWER(codigo) = :m_exact THEN 0 ELSE 1 END,
            LENGTH(nombre) ASC
        LIMIT :limit
        """
    )
    params["m_exact"] = q_lower
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        search_text = _modelos_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "modelos",
            "source_id": r["id"],
            "codigo": r["codigo"],
            "nombre": r["nombre"],
            "periodo": r["periodo"],
            "impuesto": r["impuesto"],
            "url_info": r["url_info"],
            "search_text": search_text,
            "score": 1.0,
            "chunk_texto": search_text,
        })
    return results


def _modelos_vector(db, q: str, embed_fn, limit: int) -> list[dict]:
    """Modelos AEAT vector search."""
    try:
        query_vec = embed_fn(q)
    except Exception:
        return []

    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT id, codigo, nombre, periodo, impuesto, url_info, created_at,
               1.0 - (embedding_384 <=> '[{query_vec_str}]') AS similarity
        FROM aeat_modelo
        WHERE embedding_384 IS NOT NULL
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        search_text = _modelos_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "modelos",
            "source_id": r["id"],
            "codigo": r["codigo"],
            "nombre": r["nombre"],
            "periodo": r["periodo"],
            "impuesto": r["impuesto"],
            "url_info": r["url_info"],
            "search_text": search_text,
            "similarity": round(sim, 4),
            "chunk_texto": search_text,
        })
    return results


# ---------------------------------------------------------------------------
# Screening fulltext + vector
# ---------------------------------------------------------------------------

def _screening_build_search_text(row: dict) -> str:
    """Build searchable text from screening entry row."""
    parts = []
    if row.get("nombre"):
        parts.append(row["nombre"])
    if row.get("aliases"):
        aliases = row["aliases"]
        if isinstance(aliases, str):
            import json
            try:
                aliases = json.loads(aliases)
            except (json.JSONDecodeError, TypeError):
                aliases = []
        parts.extend(str(a) for a in aliases if a)
    if row.get("categorias"):
        cats = row["categorias"]
        if isinstance(cats, str):
            import json
            try:
                cats = json.loads(cats)
            except (json.JSONDecodeError, TypeError):
                cats = []
        parts.extend(str(c) for c in cats if c)
    if row.get("descripcion"):
        parts.append(row["descripcion"])
    return " ".join(parts)


def _screening_fulltext(db, q: str, limit: int) -> list[dict]:
    """Screening entries fulltext search on nombre + aliases + descripcion."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(nombre) LIKE :s_q{i}")
        params[f"s_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT se.id, se.entidad_id, se.nombre, se.tipo_entidad, se.pais,
               se.nif, se.fecha_nacimiento, se.aliases, se.categorias,
               se.descripcion, se.fecha_sancion, se.fecha_baja, se.activo,
               l.codigo AS list_codigo, l.nombre AS list_nombre,
               l.tipo AS list_tipo, l.organismo AS list_organismo
        FROM screening_entries se
        JOIN screening_lists l ON l.id = se.list_id
        WHERE {' OR '.join(conditions)}
          AND l.activo = 1 AND se.activo = 1
        ORDER BY se.nombre
        LIMIT :limit
        """
    )
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        search_text = _screening_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "screening",
            "source_id": r["id"],
            "entidad_id": r["entidad_id"],
            "nombre": r["nombre"],
            "tipo_entidad": r["tipo_entidad"],
            "pais": r["pais"],
            "nif": r["nif"],
            "aliases": r["aliases"],
            "categorias": r["categorias"],
            "descripcion": r["descripcion"],
            "list_codigo": r["list_codigo"],
            "list_nombre": r["list_nombre"],
            "list_tipo": r["list_tipo"],
            "search_text": search_text,
            "score": 1.0,
            "chunk_texto": search_text,
        })
    return results


def _screening_vector(db, q: str, embed_fn, limit: int) -> list[dict]:
    """Screening entries vector search."""
    try:
        query_vec = embed_fn(q)
    except Exception:
        return []

    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT se.id, se.entidad_id, se.nombre, se.tipo_entidad, se.pais,
               se.nif, se.fecha_nacimiento, se.aliases, se.categorias,
               se.descripcion, se.fecha_sancion, se.fecha_baja, se.activo,
               l.codigo AS list_codigo, l.nombre AS list_nombre,
               l.tipo AS list_tipo, l.organismo AS list_organismo,
               1.0 - (se.embedding_384 <=> '[{query_vec_str}]') AS similarity
        FROM screening_entries se
        JOIN screening_lists l ON l.id = se.list_id
        WHERE se.embedding_384 IS NOT NULL
          AND l.activo = 1 AND se.activo = 1
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        search_text = _screening_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "screening",
            "source_id": r["id"],
            "entidad_id": r["entidad_id"],
            "nombre": r["nombre"],
            "tipo_entidad": r["tipo_entidad"],
            "pais": r["pais"],
            "nif": r["nif"],
            "aliases": r["aliases"],
            "categorias": r["categorias"],
            "descripcion": r["descripcion"],
            "list_codigo": r["list_codigo"],
            "list_nombre": r["list_nombre"],
            "list_tipo": r["list_tipo"],
            "search_text": search_text,
            "similarity": round(sim, 4),
            "chunk_texto": search_text,
        })
    return results


# ---------------------------------------------------------------------------
# Entities (empresa) fulltext + vector
# ---------------------------------------------------------------------------

def _entities_build_search_text(row: dict) -> str:
    """Build searchable text from empresa row."""
    parts = []
    if row.get("nombre"):
        parts.append(row["nombre"])
    if row.get("nif"):
        parts.append(row["nif"])
    return " ".join(parts)


def _entities_fulltext(db, q: str, limit: int) -> list[dict]:
    """Empresa fulltext search."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(nombre) LIKE :e_q{i}")
        params[f"e_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT id, nombre, nif, domicilio, fuente_inicial, created_at
        FROM empresa
        WHERE {' OR '.join(conditions)}
        ORDER BY LENGTH(nombre) ASC
        LIMIT :limit
        """
    )
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        search_text = _entities_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "entities",
            "source_id": r["id"],
            "nombre": r["nombre"],
            "nif": r["nif"],
            "domicilio": r["domicilio"],
            "fuente_inicial": r["fuente_inicial"],
            "search_text": search_text,
            "score": 1.0,
            "chunk_texto": search_text,
        })
    return results


def _entities_vector(db, q: str, embed_fn, limit: int) -> list[dict]:
    """Empresa vector search."""
    try:
        query_vec = embed_fn(q)
    except Exception:
        return []

    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT id, nombre, nif, domicilio, fuente_inicial, created_at,
               1.0 - (embedding_384 <=> '[{query_vec_str}]') AS similarity
        FROM empresa
        WHERE embedding_384 IS NOT NULL
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        search_text = _entities_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "entities",
            "source_id": r["id"],
            "nombre": r["nombre"],
            "nif": r["nif"],
            "domicilio": r["domicilio"],
            "fuente_inicial": r["fuente_inicial"],
            "search_text": search_text,
            "similarity": round(sim, 4),
            "chunk_texto": search_text,
        })
    return results


# ---------------------------------------------------------------------------
# Normas fulltext + vector
# ---------------------------------------------------------------------------

def _norms_build_search_text(row: dict) -> str:
    """Build searchable text from norma row."""
    parts = []
    if row.get("codigo"):
        parts.append(row["codigo"])
    if row.get("nombre"):
        parts.append(row["nombre"])
    if row.get("titulo"):
        parts.append(row["titulo"])
    if row.get("numero_boe"):
        parts.append(row["numero_boe"])
    return " ".join(parts)


def _norms_fulltext(db, q: str, limit: int) -> list[dict]:
    """Norma fulltext search."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(nombre) LIKE :n_q{i}")
        params[f"n_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT id, codigo, nombre, numero_boe, titulo, tipo_fuente, ambito,
               tipo, vigente, fecha_publicacion, eli_uri, created_at
        FROM norma
        WHERE {' OR '.join(conditions)}
        ORDER BY
            CASE WHEN LOWER(codigo) = :n_exact THEN 0 ELSE 1 END,
            LENGTH(nombre) ASC
        LIMIT :limit
        """
    )
    params["n_exact"] = q_lower
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        search_text = _norms_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "norms",
            "source_id": r["id"],
            "codigo": r["codigo"],
            "nombre": r["nombre"],
            "numero_boe": r["numero_boe"],
            "titulo": r["titulo"],
            "tipo_fuente": r["tipo_fuente"],
            "ambito": r["ambito"],
            "tipo": r["tipo"],
            "vigente": r["vigente"],
            "search_text": search_text,
            "score": 1.0,
            "chunk_texto": search_text,
        })
    return results


def _norms_vector(db, q: str, embed_fn, limit: int) -> list[dict]:
    """Norma vector search."""
    try:
        query_vec = embed_fn(q)
    except Exception:
        return []

    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT id, codigo, nombre, numero_boe, titulo, tipo_fuente, ambito,
               tipo, vigente, fecha_publicacion, eli_uri, created_at,
               1.0 - (embedding_384 <=> '[{query_vec_str}]') AS similarity
        FROM norma
        WHERE embedding_384 IS NOT NULL
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        search_text = _norms_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "norms",
            "source_id": r["id"],
            "codigo": r["codigo"],
            "nombre": r["nombre"],
            "numero_boe": r["numero_boe"],
            "titulo": r["titulo"],
            "tipo_fuente": r["tipo_fuente"],
            "ambito": r["ambito"],
            "tipo": r["tipo"],
            "vigente": r["vigente"],
            "search_text": search_text,
            "similarity": round(sim, 4),
            "chunk_texto": search_text,
        })
    return results


# ---------------------------------------------------------------------------
# Articulos fulltext + vector
# ---------------------------------------------------------------------------

def _articles_build_search_text(row: dict) -> str:
    """Build searchable text from articulo row."""
    parts = []
    if row.get("numero"):
        parts.append(row["numero"])
    if row.get("titulo"):
        parts.append(row["titulo"])
    if row.get("contenido"):
        parts.append(row["contenido"])
    return " ".join(parts)


def _articles_fulltext(db, q: str, limit: int) -> list[dict]:
    """Articulo fulltext search."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(titulo) LIKE :a_q{i}")
        params[f"a_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT id, numero, titulo, contenido, tipo, norma_id, created_at
        FROM articulo
        WHERE {' OR '.join(conditions)}
        ORDER BY LENGTH(titulo) ASC
        LIMIT :limit
        """
    )
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        search_text = _articles_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "articles",
            "source_id": r["id"],
            "numero": r["numero"],
            "titulo": r["titulo"],
            "contenido": r["contenido"],
            "tipo": r["tipo"],
            "norma_id": r["norma_id"],
            "search_text": search_text,
            "score": 1.0,
            "chunk_texto": search_text,
        })
    return results


def _articles_vector(db, q: str, embed_fn, limit: int) -> list[dict]:
    """Articulo vector search."""
    try:
        query_vec = embed_fn(q)
    except Exception:
        return []

    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT id, numero, titulo, contenido, tipo, norma_id, created_at,
               1.0 - (embedding_384 <=> '[{query_vec_str}]') AS similarity
        FROM articulo
        WHERE embedding_384 IS NOT NULL
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        search_text = _articles_build_search_text(r)
        results.append({
            "id": r["id"],
            "source_type": "articles",
            "source_id": r["id"],
            "numero": r["numero"],
            "titulo": r["titulo"],
            "contenido": r["contenido"],
            "tipo": r["tipo"],
            "norma_id": r["norma_id"],
            "search_text": search_text,
            "similarity": round(sim, 4),
            "chunk_texto": search_text,
        })
    return results


# ---------------------------------------------------------------------------
# RRF fusion across multiple sources
# ---------------------------------------------------------------------------

def _rrf_fuse_multi(
    source_results: dict[str, list[dict]],
    ft_weight: float,
    vec_weight: float,
    limit: int,
) -> list[dict[str, Any]]:
    """RRF fusion across multiple source types.

    Each source result has either rrf_ft_rank or rrf_vec_rank set.
    We assign each result a unique key (source_type + source_id) and
    compute RRF score per unique item.
    """
    rrf_scores: dict[str, dict[str, Any]] = {}

    for source_type, results in source_results.items():
        for rank, item in enumerate(results, 1):
            # Build unique key from source_type + source_id
            item_id = item.get("source_id") or item.get("id") or 0
            key = f"{source_type}:{item_id}"

            # Normalize: some sources use doc_id instead of source_id
            doc_id = item.get("doc_id") or item.get("documento_origen_id")
            if doc_id:
                key = f"{source_type}:{doc_id}"

            if key not in rrf_scores:
                rrf_scores[key] = {
                    "item": item,
                    "rrf_score": 0.0,
                    "has_ft": False,
                    "has_vec": False,
                    "source_types": set(),
                }

            entry = rrf_scores[key]
            entry["source_types"].add(source_type)

            ft_rank = item.get("rrf_ft_rank")
            vec_rank = item.get("rrf_vec_rank")
            similarity = item.get("similarity")

            if ft_rank is not None and ft_weight > 0:
                entry["rrf_score"] += ft_weight * (1.0 / (_RRF_K + ft_rank))
                entry["has_ft"] = True

            if vec_rank is not None and vec_weight > 0:
                entry["rrf_score"] += vec_weight * (1.0 / (_RRF_K + vec_rank))
                entry["has_vec"] = True

            # If no rank was assigned (fallback similarity score), use it as rank
            if ft_rank is None and vec_rank is None and similarity is not None:
                # Convert similarity to approximate rank for RRF
                approx_rank = max(1, int((1.0 - similarity) * 100) + 1)
                if vec_weight > 0:
                    entry["rrf_score"] += vec_weight * (1.0 / (_RRF_K + approx_rank))
                    entry["has_vec"] = True

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
        item["source_types"] = sorted(entry["source_types"])

        results.append(item)

    return results
