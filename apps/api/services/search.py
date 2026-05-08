import hashlib
import re

from db import db_session
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError


def _build_source_hash(*parts: object) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_postgres(db) -> bool:
    return db.bind.dialect.name == "postgresql"


def _add_accents(text: str) -> str:
    """Reconstruct accented characters for Spanish stemming compatibility.

    PostgreSQL's spanish stemmer only reduces ASCII words to stems when
    they contain accented characters (non-ASCII). E.g. 'autoliquidacion'
    stays as-is but 'autoliquidación' becomes 'autoliquid'.

    This function adds back common Spanish accents so tsquery/stemmer
    works correctly.
    """
    # Common Spanish words that need accent restoration
    accent_map = {
        "a": ["a", "á", "à", "â", "ä", "ã"],
        "e": ["e", "é", "è", "ê", "ë"],
        "i": ["i", "í", "ì", "î", "ï"],
        "o": ["o", "ó", "ò", "ô", "ö", "õ"],
        "u": ["u", "ú", "ù", "û", "ü"],
        "n": ["n", "ñ"],
    }
    # Reverse map: accented -> base
    reverse = {}
    for base, variants in accent_map.items():
        for v in variants:
            reverse[v] = base

    # Words that commonly need accent in Spanish search context
    accent_fixes = {
        "autoliquidacion": "autoliquidación",
        "declaracion": "declaración",
        "procedimiento": "procedimiento",
        "tributario": "tributario",
        "administracion": "administración",
        "resolucion": "resolución",
        "prescripcion": "prescripción",
        "contabilidad": "contabilidad",
    }

    # First try exact word match for common words
    words = re.findall(r"[\w]+", text.lower())
    result = text
    for word in words:
        if word in accent_fixes:
            result = result.replace(word, accent_fixes[word])

    return result


def _strip_norma_codes(value: str) -> tuple[str, set[str]]:
    """Strip known norma codes from query text before building tsquery.

    Known codes like 'LGT', 'IRNR', 'DAC6' are used as filters, not as
    fulltext search terms. Including them in the tsquery causes 0 results
    because chunks don't contain these codes literally.

    Returns (cleaned_query, stripped_codes).
    """
    # Map from query word -> DB norma code (same as _extract_norma_from_query)
    known_codes = frozenset(
        {
            "IRNR",
            "LIRNR",
            "IRPF",
            "LIRPF",
            "RIRPF",
            "IVA",
            "LIVA",
            "RIVA",
            "IS",
            "LIS",
            "RIS",
            "LGT",
            "ITPAJD",
            "ITP",
            "AJD",
            "IIEE",
            "DAC6",
            "DAC6RD",
            "DAC6EU",
        }
    )

    words = re.findall(r"[A-Za-z0-9]+", value)
    stripped = set()
    remaining = []
    for w in words:
        w_upper = w.upper()
        if w_upper in known_codes:
            stripped.add(w_upper)
        else:
            remaining.append(w)

    cleaned = " ".join(remaining)
    return cleaned, stripped


def _build_tsquery_sql(value: str) -> tuple[str, dict]:
    """Build a PostgreSQL tsquery expression with OR between each word.

    Strips known norma codes (LGT, IRPF, etc.) before building tsquery since
    they're used as filters, not fulltext search terms.

    Returns ('', {}) when the query is empty/None so callers can fall back to ILIKE.
    """
    if value is None:
        return "", {}
    # Strip norma codes before building tsquery
    cleaned, _ = _strip_norma_codes(value)

    if not cleaned or not cleaned.strip():
        return "", {}

    # Extract words (alphanumeric only) from query
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    if not words:
        return "", {}

    # For each word, build plainto_tsquery (handles stemming)
    # PostgreSQL plaintext params: escape single quotes only (plainto_tsquery does NOT accept bind params)
    ts_parts = []
    accents_parts = []
    for w in words:
        escaped_w = w.replace("'", "''")
        accents = _add_accents(w).replace("'", "''")
        ts_parts.append(f"plainto_tsquery('spanish', '{escaped_w}')")
        accents_parts.append(f"plainto_tsquery('spanish', '{accents}')")

    # OR all word queries together — no params needed (all values are escaped inline)
    ts_query = " || ".join(ts_parts)
    accents_query = " || ".join(accents_parts)

    return f"({ts_query}) || ({accents_query})", {}


def _build_fragment(text_value: str, query: str, max_length: int = 220) -> str:
    terms = [term for term in re.findall(r"[\wáéíóúüñ]+", query, flags=re.IGNORECASE) if len(term) >= 3]
    if not text_value:
        return ""

    for term in terms:
        match = re.search(re.escape(term), text_value, flags=re.IGNORECASE)
        if not match:
            continue
        start = max(match.start() - 80, 0)
        end = min(match.end() + 120, len(text_value))
        fragment = text_value[start:end].strip()
        highlighted = re.sub(
            re.escape(term),
            lambda item: f"<mark>{item.group(0)}</mark>",
            fragment,
            flags=re.IGNORECASE,
        )
        if start > 0:
            highlighted = f"...{highlighted}"
        if end < len(text_value):
            highlighted = f"{highlighted}..."
        return highlighted

    trimmed = text_value[:max_length].strip()
    if len(text_value) > max_length:
        return f"{trimmed}..."
    return trimmed


def _chunk_rank_boost(has_chunks: bool, base_rank: float) -> float:
    """Small explicit boost for articles that have pre-chunked content.

    Boost is 0.05 — enough to slightly prefer chunked articles when
    ranks are close, without overriding the actual search relevance.
    """
    if has_chunks and base_rank > 0:
        return base_rank * 1.1
    return base_rank


def _extract_norma_from_query(q: str) -> str | None:
    """Extract a known law code from the query to use as a norma filter.

    This prevents convention articles from drowning out actual law results.
    E.g., "IRNR rentas sin establecimiento permanente" -> "IRNR"
    Returns the DB code (n.codigo value), not the search alias.
    """
    # Map from query word -> DB norma code
    query_to_db = {
        "IRNR": "IRNR",
        "LIRNR": "IRNR",
        "IRPF": "LIRPF",
        "LIRPF": "LIRPF",
        "RIRPF": "LIRPF",
        "IVA": "LIVA",
        "LIVA": "LIVA",
        "RIVA": "LIVA",
        "IS": "LIS",
        "LIS": "LIS",
        "RIS": "LIS",
        "LGT": "LGT",
        "ITPAJD": "ITPAJD",
        "ITP": "ITPAJD",
        "AJD": "ITPAJD",
        "IIEE": "IIEE",
        "DAC6": "DAC6",
        "DAC6RD": "DAC6RD",
        "DAC6EU": "DAC6EU",
    }
    words = re.findall(r"[A-Za-z0-9]+", q)
    # Check longer tokens first to avoid partial matches (e.g. DAC6RD before DAC6)
    words_sorted = sorted(words, key=len, reverse=True)
    for w in words_sorted:
        w_upper = w.upper()
        if w_upper in query_to_db:
            return query_to_db[w_upper]
    return None


def search_legislacion(
    q: str,
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
):
    with db_session() as db:
        if _is_postgres(db):
            return _search_legislacion_pg(db, q, norma, fuente, ambito, tipo, vigente_en)
        else:
            return _search_legislacion_sqlite(db, q, norma, fuente, ambito, tipo, vigente_en)


_NORMA_ALIASES = {
    "IRNR": "IRNR",
    "LIRNR": "IRNR",
    "IRPF": "LIRPF",
    "LIRPF": "LIRPF",
    "RIRPF": "LIRPF",
    "IVA": "LIVA",
    "LIVA": "LIVA",
    "RIVA": "LIVA",
    "IS": "LIS",
    "LIS": "LIS",
    "RIS": "LIS",
    "IIEE": "IIEE",
    "DAC6": "DAC6",
    "DAC6RD": "DAC6RD",
    "DAC6EU": "DAC6EU",
}


def _build_common_filters(norma, fuente, ambito, tipo, vigente_en, params):
    """Build filters shared across both chunked and non-chunked branches."""
    filters: list[str] = []
    if norma is not None:
        # Normalize aliases to DB code
        norm = _NORMA_ALIASES.get(norma.upper(), norma)
        filters.append("n.codigo = :norma")
        params["norma"] = norm
    if fuente is not None:
        filters.append("n.tipo_fuente = :fuente")
        params["fuente"] = fuente
    if ambito is not None:
        filters.append("n.ambito = :ambito")
        params["ambito"] = ambito
    if tipo is not None:
        filters.append("a.tipo = :tipo")
        params["tipo"] = tipo
    if vigente_en is not None:
        filters.append(
            "(va.vigente_desde <= :vigente_en AND (va.vigente_hasta IS NULL OR va.vigente_hasta >= :vigente_en))"
        )
        params["vigente_en"] = vigente_en
    return filters


def _search_legislacion_pg(db, q, norma, fuente, ambito, tipo, vigente_en):
    """Postgres branch: search over documento_fragmento chunks with ts_rank."""
    # Auto-detect norma code from query words if not explicitly provided
    if norma is None:
        norma = _extract_norma_from_query(q)

    # When norma was auto-detected from the query, strip it from the query
    # before building tsquery. The norma word lives in n.codigo, not in chunk text,
    # so including it in tsquery causes zero matches (e.g. "IRNR rentas..." fails
    # because "IRNR" is not in any chunk, only in n.codigo='IRNR').
    search_q = q
    if norma is not None and norma not in q:
        # norma was explicitly provided, no stripping needed
        pass
    elif norma is not None:
        # Strip the detected norma word from the query to avoid tsquery mismatch
        query_to_norma = {
            "IRNR": "IRNR",
            "LIRNR": "IRNR",
            "IRPF": "LIRPF",
            "LIRPF": "LIRPF",
            "RIRPF": "LIRPF",
            "IVA": "LIVA",
            "LIVA": "LIVA",
            "RIVA": "LIVA",
            "IS": "LIS",
            "LIS": "LIS",
            "RIS": "LIS",
            "LGT": "LGT",
            "ITPAJD": "ITPAJD",
            "ITP": "ITPAJD",
            "AJD": "ITPAJD",
            "IIEE": "IIEE",
            "DAC6": "DAC6",
            "DAC6RD": "DAC6RD",
            "DAC6EU": "DAC6EU",
        }
        db_code = norma
        for query_word, norm_code in query_to_norma.items():
            if norm_code == db_code:
                search_q = re.sub(r"\b" + re.escape(query_word) + r"\b", "", search_q, flags=re.IGNORECASE).strip()
        if not search_q:
            # If stripping removed everything (e.g. query was just "IRNR"),
            # use ILIKE fallback instead of tsquery to avoid zero matches.
            search_q = None

    params: dict = {}
    if search_q is not None:
        tsquery_str, tsq_params = _build_tsquery_sql(search_q)
        use_ts_rank = bool(tsquery_str)
        params.update(tsq_params)
    else:
        tsquery_str = ""
        use_ts_rank = False
        tsq_params = {}
        params.update(tsq_params)

    if use_ts_rank:
        full_tsq = f"({tsquery_str})"
        search_filter = f"cf.search_vector @@ {full_tsq}"
        rank_expr = f"ts_rank(cf.search_vector, {full_tsq})"
    else:
        # No tsquery available (empty query or None after stripping).
        # Use ILIKE with search_q if available, otherwise fall back to
        # norma-only search (no text filter) to return top articles.
        if search_q is not None and search_q.strip():
            search_filter = "cf.texto ILIKE :term"
            params["term"] = f"%{search_q}%"
        else:
            # No text filter - return top articles of the detected norma
            search_filter = "TRUE"
        rank_expr = "0.0"

    common_filters = _build_common_filters(norma, fuente, ambito, tipo, vigente_en, params)
    common_filters.append(search_filter)
    where_clause = " AND ".join(common_filters)

    # Build vig_subquery: the subquery that selects the latest version
    # If vigente_en is provided, it must be incorporated into the subquery
    # to avoid returning a version that was not valid at the requested date.
    vig_subquery_where = "a2.id = a.id"
    vig_subquery_params: dict = {}
    if vigente_en is not None:
        vig_subquery_where += (
            " AND v2.vigente_desde <= :vigente_en AND (v2.vigente_hasta IS NULL OR v2.vigente_hasta >= :vigente_en)"
        )
        vig_subquery_params["vigente_en"] = vigente_en

    vig_subquery = (
        f"SELECT MAX(v2.vigente_desde) "
        f"FROM version_articulo v2 "
        f"JOIN articulo a2 ON v2.articulo_id = a2.id "
        f"WHERE {vig_subquery_where}"
    )

    query = text(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (cf.documento_origen_id)
                cf.documento_origen_id AS doc_id,
                n.codigo,
                a.numero,
                a.tipo,
                va.texto,
                va.vigente_desde,
                va.vigente_hasta,
                {rank_expr} AS rank,
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
            WHERE """
        + where_clause
        + f"""
                AND cf.documento_origen_tipo = 'legislacion'
                AND va.vigente_desde = ({vig_subquery})
                ORDER BY cf.documento_origen_id, rank DESC, va.vigente_desde DESC
        ) AS sub
        ORDER BY rank DESC
        LIMIT 10
        """
    )
    params.update(vig_subquery_params)

    query_with_binds = query.bindparams(**{k: v for k, v in params.items() if k in ("tsq", "accents")})
    remaining_params = {k: v for k, v in params.items() if k not in ("tsq", "accents")}
    try:
        rows = db.execute(query_with_binds, remaining_params).mappings()
    except ProgrammingError as exc:
        message = str(exc).lower()
        if "documento_fragmento" in message and "does not exist" in message:
            db.rollback()
            return {
                "q": q,
                "resultados": _search_version_articulo_pg(
                    db, q, norma, fuente, ambito, tipo, vigente_en, params, vig_subquery_params
                ),
            }
        raise
    results = []
    for row in rows:
        rank = row.get("rank")
        if rank is not None and use_ts_rank:
            has_chunks = bool(row.get("chunk_id"))
            rank = _chunk_rank_boost(has_chunks, float(rank))

        chunk_texto = row.get("chunk_texto")
        fragmento = None
        if chunk_texto:
            fragmento = _build_fragment(chunk_texto, q)

        results.append(
            {
                "doc_id": int(row["doc_id"]),
                "tipo": row["tipo"],
                "norma": row["codigo"],
                "numero": row["numero"],
                "texto": row["texto"],
                "fragmento": fragmento or _build_fragment(row["texto"], q),
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
                "rank": round(float(rank), 4) if rank is not None else None,
                "fuente_norma": row.get("boe_id") or row.get("eli_uri"),
                "source_url": (
                    f"https://www.boe.es/diario_boe/txt.php?id={row['boe_id']}"
                    if row.get("boe_id")
                    else row.get("eli_uri")
                ),
                "chunk_id": row.get("chunk_id"),
                "source_hash": _build_source_hash(
                    row["codigo"],
                    row["numero"],
                    row.get("chunk_id"),
                    row.get("chunk_texto") or row["texto"],
                    row.get("boe_id") or row.get("eli_uri"),
                ),
                "motivo_ranking": (f"ts_rank={round(float(rank), 4)}" if rank is not None else "ILIKE match"),
                "confianza": {
                    "nivel": 1,
                    "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                    "aviso": None,
                },
            }
        )

    # Fallback: if no chunked results, search version_articulo directly
    # (documento_fragmento may not be backfilled yet)
    if not results:
        results = _search_version_articulo_pg(
            db, q, norma, fuente, ambito, tipo, vigente_en, params, vig_subquery_params
        )

    return {
        "q": q,
        "resultados": results,
    }


def _search_version_articulo_pg(db, q, norma, fuente, ambito, tipo, vigente_en, chunk_params, vig_subquery_params):
    """Fallback search over version_articulo when documento_fragmento is empty."""
    # Auto-detect norma code from query words if not explicitly provided
    if norma is None:
        norma = _extract_norma_from_query(q)

    params: dict = {}
    tsquery_str, tsq_params = _build_tsquery_sql(q)
    use_ts_rank = bool(tsquery_str)
    params.update(tsq_params)

    if use_ts_rank:
        full_tsq = f"({tsquery_str})"
        search_filter = f"va.search_vector @@ {full_tsq}"
        rank_expr = f"ts_rank(va.search_vector, {full_tsq})"
    else:
        search_filter = "LOWER(va.texto) LIKE LOWER(:term)"
        params["term"] = f"%{q}%"
        rank_expr = "0.0"

    common_filters = _build_common_filters(norma, fuente, ambito, tipo, vigente_en, params)
    common_filters.append(search_filter)
    where_clause = " AND ".join(common_filters)

    vig_subquery_where = "a2.id = a.id"
    if vigente_en is not None:
        vig_subquery_where += (
            " AND v2.vigente_desde <= :vigente_en AND (v2.vigente_hasta IS NULL OR v2.vigente_hasta >= :vigente_en)"
        )

    vig_subquery = (
        "SELECT MAX(v2.vigente_desde) "
        "FROM version_articulo v2 "
        "JOIN articulo a2 ON v2.articulo_id = a2.id "
        f"WHERE {vig_subquery_where}"
    )

    query = text(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (a.id)
                a.id AS doc_id,
                n.codigo,
                a.numero,
                a.tipo,
                va.texto,
                va.vigente_desde,
                va.vigente_hasta,
                {rank_expr} AS rank,
                n.boe_id,
                n.eli_uri
            FROM version_articulo va
            JOIN articulo a ON a.id = va.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE {where_clause}
              AND va.vigente_desde = ({vig_subquery})
              AND va.search_vector IS NOT NULL
            ORDER BY a.id, rank DESC, va.vigente_desde DESC
        ) AS sub
        ORDER BY rank DESC
        LIMIT 10
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        rank = row.get("rank")
        if rank is not None and use_ts_rank:
            rank = float(rank)

        results.append(
            {
                "tipo": row["tipo"],
                "norma": row["codigo"],
                "numero": row["numero"],
                "texto": row["texto"],
                "fragmento": _build_fragment(row["texto"], q),
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
                "rank": round(rank, 4) if rank is not None else None,
                "fuente_norma": row.get("boe_id") or row.get("eli_uri"),
                "source_url": (
                    f"https://www.boe.es/diario_boe/txt.php?id={row['boe_id']}"
                    if row.get("boe_id")
                    else row.get("eli_uri")
                ),
                "chunk_id": None,
                "source_hash": _build_source_hash(
                    row["codigo"],
                    row["numero"],
                    row["texto"],
                    row.get("boe_id") or row.get("eli_uri"),
                ),
                "motivo_ranking": (f"ts_rank={round(rank, 4)}" if rank is not None else "ILIKE match"),
                "confianza": {
                    "nivel": 1,
                    "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                    "aviso": None,
                },
            }
        )

    return results


def _search_legislacion_sqlite(db, q, norma, fuente, ambito, tipo, vigente_en):
    """SQLite branch: legacy search over version_articulo (no chunks)."""
    params: dict[str, str] = {}
    filters: list[str] = []

    if q:
        term_filters = []
        for index, term in enumerate(re.findall(r"[\wáéíóúüñ]+", q, flags=re.IGNORECASE)):
            param_name = f"term_{index}"
            term_filters.append(f"LOWER(va.texto) LIKE LOWER(:{param_name})")
            params[param_name] = f"%{term}%"
        if term_filters:
            filters.append("(" + " AND ".join(term_filters) + ")")

    common_filters = _build_common_filters(norma, fuente, ambito, tipo, vigente_en, params)
    filters.extend(common_filters)

    if filters:
        where_clause = "WHERE " + " AND ".join(filters)
    else:
        where_clause = ""

    query = text(
        """
        SELECT n.codigo, a.numero, a.tipo, va.texto, va.vigente_desde, va.vigente_hasta,
               n.boe_id, n.eli_uri
        FROM norma n
        JOIN articulo a ON a.norma_id = n.id
        JOIN version_articulo va ON va.articulo_id = a.id
        """
        + where_clause
        + """
        GROUP BY n.codigo, a.numero
        ORDER BY va.vigente_desde DESC
        LIMIT 10
        """
    )

    rows = db.execute(query, params).mappings()
    results = []
    for row in rows:
        results.append(
            {
                "tipo": row["tipo"],
                "norma": row["codigo"],
                "numero": row["numero"],
                "texto": row["texto"],
                "fragmento": _build_fragment(row["texto"], q),
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
                "rank": None,
                "fuente_norma": row.get("boe_id") or row.get("eli_uri"),
                "source_url": (
                    f"https://www.boe.es/diario_boe/txt.php?id={row['boe_id']}"
                    if row.get("boe_id")
                    else row.get("eli_uri")
                ),
                "chunk_id": None,
                "source_hash": _build_source_hash(
                    row["codigo"],
                    row["numero"],
                    row["texto"],
                    row.get("boe_id") or row.get("eli_uri"),
                ),
                "motivo_ranking": "ILIKE match",
                "confianza": {
                    "nivel": 1,
                    "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                    "aviso": None,
                },
            }
        )

    return {
        "q": q,
        "resultados": results,
    }
