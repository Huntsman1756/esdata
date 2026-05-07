"""Unified multi-source retrieval with RRF fusion across all data sources.

Searches across legislacion, doctrina, pgc_cuenta, aeat_modelo, screening_entries,
empresa, norma, articulo, and Fase 31 regulatory domains (mica, dac, pbc, fraud,
mifid, mar, dora, priips, transparency, sfdr, csrd, aifmd_ucits, crd_brrd_emir).
Each source can be filtered via the ``sources`` parameter. Results are fused
via Reciprocal Rank Fusion (RRF).

Supported source types:
    - legislacion: version_articulo + documento_fragmento (fulltext + vector)
    - doctrina: documento_interpretativo (fulltext + vector)
    - pgc: pgc_cuenta (fulltext + vector)
    - modelos: aeat_modelo (fulltext + vector)
    - screening: screening_entries (fulltext + vector)
    - entities: empresa (fulltext + vector)
    - norms: norma (fulltext + vector)
    - articles: articulo (fulltext + vector)
    - mica: MiCA/Crypto assets (documento_fragmento, fulltext + vector)
    - dac: DAC8/DAC9 tax reporting (documento_fragmento, fulltext + vector)
    - pbc: Ley 10/2010 AML (documento_fragmento, fulltext + vector)
    - fraud: Ley 11/2021 antifraud (documento_fragmento, fulltext + vector)
    - mifid: MiFID II/MiFIR (documento_fragmento, fulltext + vector)
    - mar: Market Abuse Regulation (documento_fragmento, fulltext + vector)
    - dora: Digital Operational Resilience Act (documento_fragmento, fulltext + vector)
    - priips: PRIIPs/LIVMC (documento_fragmento, fulltext + vector)
    - transparency: Transparency regulation (documento_fragmento, fulltext + vector)
    - sfdr: SFDR sustainable finance disclosures (documento_fragmento, fulltext + vector)
    - csrd: CSRD corporate sustainability reporting (documento_fragmento, fulltext + vector)
    - aifmd_ucits: AIFMD/UCITS fund regulation (documento_fragmento, fulltext + vector)
    - crd_brrd_emir: CRD/CRR, BRRD, EMIR prudential regulation (documento_fragmento, fulltext + vector)
"""

from __future__ import annotations

import logging
from typing import Any

from db import db_session
from services.search import _is_postgres
from sqlalchemy import text

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
            "mica", "dac", "pbc", "fraud",
            "mifid", "mar", "dora", "priips", "transparency",
            "sfdr", "csrd", "aifmd_ucits", "crd_brrd_emir",
        ]

    with db_session() as db:
        is_pg = _is_postgres(db)
        embed_fn = _get_embed_fn()
        hybrid_weight = max(0.0, min(1.0, hybrid_weight))
        ft_weight = 1.0 - hybrid_weight
        vec_weight = hybrid_weight

        all_source_results: dict[str, list[dict]] = {}
        source_errors: list[dict[str, str]] = []
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
            "mica": _search_31x_source,
            "dac": _search_31x_source,
            "pbc": _search_31x_source,
            "fraud": _search_31x_source,
            "mifid": _search_31x_source,
            "mar": _search_31x_source,
            "dora": _search_31x_source,
            "priips": _search_31x_source,
            "transparency": _search_31x_source,
            "sfdr": _search_31x_source,
            "csrd": _search_31x_source,
            "aifmd_ucits": _search_31x_source,
            "crd_brrd_emir": _search_31x_source,
        }

        for source in sources:
            handler = source_handlers.get(source)
            if handler is None:
                logger.warning("Unknown source type: %s", source)
                continue

            try:
                handler_args: tuple[Any, ...] = (db, q, is_pg, embed_fn, hybrid_weight, limit)
                if handler is _search_31x_source:
                    handler_args = (db, q, source, is_pg, embed_fn, hybrid_weight, limit)

                results = handler(*handler_args)
                if results:
                    all_source_results[source] = results
                    source_ranked.extend(results)
            except Exception as exc:
                logger.exception("Error searching source: %s", source)
                source_errors.append(
                    {
                        "source": source,
                        "error": type(exc).__name__,
                    }
                )

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
            "source_errors": source_errors,
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
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
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
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
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
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
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
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
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
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
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
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
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

# Tables per domain — maps source_type to table name
_31x_TABLES: dict[str, str] = {
    "mica": "casp",
    "dac": "dac_reporting_entity",
    "pbc": "pbc_obligated_subject",
    "fraud": "fraud_prevention_program",
    "mifid": "mifid_client_category",
    "mar": "mar_insider_transaction",
    "dora": "dora_tic_incident",
    "priips": "priips_product",
    "transparency": "transparency_issuer",
}

# Primary searchable columns per table
_31x_COLUMNS: dict[str, list[str]] = {
    "casp": ["name", "registration_number", "home_member_state", "status"],
    "crypto_asset": ["asset_type", "reference_uid", "issuer_jurisdiction", "status"],
    "tokenized_asset": ["underlying_type", "regulated_market", "status"],
    "wallet_custodian": ["wallet_type", "custody_mechanism", "audit_frequency", "status"],
    "dac_reporting_entity": ["tin", "entity_type", "member_state", "status"],
    "dac_crypto_report": ["reporting_period", "status"],
    "dac_wallet_holder": ["wallet_address", "holder_tin", "holder_member_state", "holder_type", "verification_status"],
    "pbc_obligated_subject": ["subject_type", "tin", "registration_number", "supervisory_authority", "status"],
    "pbc_internal_control": ["compliance_officer"],
    "suspicious_activity_report": ["description", "severity", "status", "sepblac_reference"],
    "beneficial_owner_record": ["owner_name", "ownership_percentage", "verification_method", "verification_date"],
    "fraud_prevention_program": ["code_of_conduct", "internal_reporting_system", "training_schedule", "audit_frequency", "compliance_officer_name", "status"],
    "fraud_risk_assessment": ["risk_areas", "mitigation_measures", "next_review_date"],
    "fraud_incident": ["description", "status", "resolution_date", "regulatory_notification"],
    "mifid_client_category": ["category", "knowledge_level", "experience_level", "status"],
    "mifid_suitability_report": ["suitability_score", "recommendation", "status"],
    "mifid_best_execution_record": ["venue", "execution_price", "market_impact", "status"],
    "mifid_conflict_of_interest_registry": ["conflict_type", "description", "mitigation_measure", "status"],
    "mifid_product_governance": ["target_market", "key_features", "risk_level", "status"],
    "mifid_order_record": ["instrument", "direction", "venue", "status"],
    "mifid_insider_list": ["insider_name", "insider_tin", "inside_information_description", "status"],
    "mifid_compensation_policy": ["policy_version", "alignment_score", "status"],
    "mar_insider_transaction": ["ppi_name", "ppi_role", "instrument", "transaction_type", "status"],
    "mar_suspicious_transaction_report": ["instrument", "pattern_description", "detection_method", "status"],
    "mar_market_manipulation_indicator": ["pattern_type", "instrument", "confidence_score", "status"],
    "mar_insider_communication": ["content_summary", "channel", "inside_info_reference"],
    "dora_tic_incident": ["incident_severity", "description", "impact_scope", "root_cause", "classification", "status"],
    "dora_third_party_provider": ["provider_name", "provider_type", "criticality_assessment", "status"],
    "dora_ict_risk_register": ["risk_description", "likelihood", "impact", "mitigation", "owner", "status"],
    "dora_penetration_test": ["test_type", "tester", "findings_count", "critical_findings", "status"],
    "dora_incident_classification_framework": ["framework_version", "severity_thresholds", "reporting_timelines", "status"],
    "priips_kid": ["product_type", "risk_scale", "cost_impact", "status"],
    "priips_product": ["product_name", "underlying_assets", "currency", "min_investment", "status"],
    "livmc_client_protection": ["protection_type", "coverage_amount", "status"],
    "livmc_voice_procedure": ["procedure_type", "description", "status"],
    "transparency_issuer": ["listing_market", "ticker", "reporting_frequency", "home_member_state", "status"],
    "transparency_regulated_information": ["info_type", "content_url", "filing_reference", "status"],
    "transparency_voting_rights": ["shareholder_id", "voting_rights_pct", "status"],
    "transparency_internal_rule": ["designated_persons", "internal_procedure", "retention_period", "status"],
    "sfdr_product": ["product_name", "product_type", "sustainability_strategy", "principal_adverse_impact", "status"],
    "sfdr_paci_indicator": ["indicator_code", "indicator_name", "value", "unit", "reference_period", "status"],
    "sfdr_entity_paci": ["entity_id", "reporting_year", "aggregated_paci", "sectoral_decarbonization", "status"],
    "sfdr_pre_contractual": ["document_type", "url", "version", "status"],
    "sfdr_annual_report": ["entity_id", "reporting_year", "paci_results", "engagement_activities", "status"],
    "csrd_entity_report": ["entity_id", "reporting_year", "esap_url", "assurance_status", "reporting_standard", "status"],
    "csrd_esg_data_point": ["topic", "indicator_code", "value", "unit", "scope", "verification_status"],
    "csrd_ess": ["standard_code", "topic", "applicable_from_year", "description", "status"],
    "csrd_double_materiality": ["entity_id", "impact_materiality", "financial_materiality", "key_impacts", "key_dependencies", "status"],
    "aifmd_fund": ["fund_name", "fund_type", "home_member_state", "total_aum_eur", "leverage_method", "status"],
    "ucits_fund": ["fund_name", "management_company", "home_member_state", "total_aum_eur", "investment_strategy", "status"],
    "aifmd_regulatory_report": ["fund_id", "report_type", "reporting_period", "filed_date", "status"],
    "ucits_regulatory_report": ["fund_id", "report_type", "reporting_period", "filed_date", "status"],
    "aifmd_liquidity_management": ["fund_id", "redemption_suspended", "gating_applied", "swing_price_applied", "stress_test_result"],
    "crd_capital_position": ["entity_id", "reporting_date", "cet1_ratio", "tier1_ratio", "total_capital_ratio", "leverage_ratio", "status"],
    "crd_stress_test": ["entity_id", "test_date", "scenario_name", "cet1_impact_pct", "competent_authority", "status"],
    "brrd_bail_in": ["entity_id", "total_eligible_liabilities", "mrel_target_pct", "mrel_compliance_pct", "resolution_status", "status"],
    "emir_trade_report": ["trade_id", "asset_class", "instrument_class", "clearing_obligation_applied", "counterparty_type", "status"],
    "emir_clearing_member": ["entity_id", "emir_registration", "clearing_type", "status"],
}

# Map source_type -> list of tables
_31x_SOURCE_TABLES: dict[str, list[str]] = {
    "mica": ["casp", "crypto_asset", "tokenized_asset", "wallet_custodian"],
    "dac": ["dac_reporting_entity", "dac_crypto_report", "dac_wallet_holder"],
    "pbc": ["pbc_obligated_subject", "pbc_internal_control", "suspicious_activity_report", "beneficial_owner_record"],
    "fraud": ["fraud_prevention_program", "fraud_risk_assessment", "fraud_incident"],
    "mifid": ["mifid_client_category", "mifid_suitability_report", "mifid_best_execution_record", "mifid_conflict_of_interest_registry", "mifid_product_governance", "mifid_order_record", "mifid_insider_list", "mifid_compensation_policy"],
    "mar": ["mar_insider_transaction", "mar_suspicious_transaction_report", "mar_market_manipulation_indicator", "mar_insider_communication"],
    "dora": ["dora_tic_incident", "dora_third_party_provider", "dora_ict_risk_register", "dora_penetration_test", "dora_incident_classification_framework"],
    "priips": ["priips_kid", "priips_product", "livmc_client_protection", "livmc_voice_procedure"],
    "transparency": ["transparency_issuer", "transparency_regulated_information",
                     "transparency_voting_rights", "transparency_internal_rule"],
    "sfdr": ["sfdr_product", "sfdr_paci_indicator", "sfdr_entity_paci", "sfdr_pre_contractual", "sfdr_annual_report"],
    "csrd": ["csrd_entity_report", "csrd_esg_data_point", "csrd_ess", "csrd_double_materiality"],
    "aifmd_ucits": ["aifmd_fund", "ucits_fund", "aifmd_regulatory_report", "ucits_regulatory_report", "aifmd_liquidity_management"],
    "crd_brrd_emir": ["crd_capital_position", "crd_stress_test", "brrd_bail_in", "emir_trade_report", "emir_clearing_member"],
}


def _search_31x_source(
    db, q: str, source_type: str, is_pg: bool, embed_fn, hybrid_weight: float, limit: int,
) -> list[dict]:
    """Search Fase 31.x regulatory domains via documento_fragmento.

    All 31.x domains store their chunks in documento_fragmento with
    documento_origen_tipo in ('mica','dac','pbc','fraud','mifid','mar','dora','priips','transparency','sfdr','csrd','aifmd_ucits','crd_brrd_emir').
    Fulltext + vector search uses the chunk table, not the raw entity tables.
    """
    results: list[dict] = []
    # Fulltext search on chunks via documento_fragmento filtered by domain_origen_tipo
    if hybrid_weight < 1.0:
        ft_results = _31x_fulltext(db, q, source_type, limit)
        for rank, item in enumerate(ft_results, 1):
            item["rrf_ft_rank"] = rank
        results.extend(ft_results)

    # Vector search on chunks
    if hybrid_weight > 0 and embed_fn:
        vec_results = _31x_vector(db, q, source_type, embed_fn, limit)
        for rank, item in enumerate(vec_results, 1):
            item["rrf_vec_rank"] = rank
        results.extend(vec_results)

    return results


def _31x_fulltext(db, q: str, source_type: str, limit: int) -> list[dict]:
    """Fulltext search over documento_fragmento for 31.x domains."""
    q_lower = q.lower().strip()
    words = q_lower.split()

    conditions: list[str] = []
    params: dict = {}

    for i, word in enumerate(words):
        conditions.append(f"LOWER(df.texto) LIKE :_31x_q{i}")
        params[f"_31x_q{i}"] = f"%{word}%"

    if not conditions:
        return []

    sql = text(
        f"""
        SELECT df.id, df.documento_origen_tipo, df.documento_origen_id,
               df.chunk_index, df.chunk_type, df.titulo, df.texto,
               df.token_count, df.documento_origen_tipo AS source_type
        FROM documento_fragmento df
        WHERE df.documento_origen_tipo = :source_type
          AND {' OR '.join(conditions)}
        ORDER BY ts_rank(df.search_vector, plainto_tsquery('spanish', :_31x_ts_query)) DESC
        LIMIT :limit
        """
    )
    params["source_type"] = source_type
    params["_31x_ts_query"] = q_lower
    params["limit"] = limit

    rows = db.execute(sql, params).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        results.append({
            "id": r["id"],
            "source_type": r["documento_origen_tipo"],
            "source_id": r["documento_origen_id"],
            "chunk_index": r["chunk_index"],
            "chunk_type": r["chunk_type"],
            "titulo": r["titulo"],
            "chunk_texto": r["texto"],
            "search_text": r["texto"],
            "score": 1.0,
            "token_count": r["token_count"],
        })
    return results


def _31x_vector(db, q: str, source_type: str, embed_fn, limit: int) -> list[dict]:
    """Vector search over documento_fragmento for 31.x domains."""
    if not embed_fn:
        return []
    query_vec = embed_fn(q)
    if not query_vec:
        return []

    query_vec_str = ",".join(f"{v:.6f}" for v in query_vec)
    sql = text(
        f"""
        SELECT df.id, df.documento_origen_tipo, df.documento_origen_id,
               df.chunk_index, df.chunk_type, df.titulo, df.texto,
               df.token_count,
               1.0 - (df.embedding <=> '[{query_vec_str}]') AS similarity
        FROM documento_fragmento df
        WHERE df.documento_origen_tipo = :source_type
          AND df.embedding IS NOT NULL
        ORDER BY similarity DESC
        LIMIT :limit
        """
    )

    rows = db.execute(sql, {"source_type": source_type, "limit": limit}).mappings().fetchall()
    results = []
    for row in rows:
        r = dict(row)
        sim = float(r["similarity"]) if r.get("similarity") is not None else 0.0
        results.append({
            "id": r["id"],
            "source_type": r["documento_origen_tipo"],
            "source_id": r["documento_origen_id"],
            "chunk_index": r["chunk_index"],
            "chunk_type": r["chunk_type"],
            "titulo": r["titulo"],
            "chunk_texto": r["texto"],
            "search_text": r["texto"],
            "similarity": round(sim, 4),
            "token_count": r["token_count"],
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
