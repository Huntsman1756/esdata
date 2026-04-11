import re

from sqlalchemy import text

from db import get_db


def _is_postgres(db) -> bool:
    return db.bind.dialect.name == "postgresql"


def _to_tsquery(value: str) -> str:
    tokens = [
        token for token in re.findall(r"[\wáéíóúüñ]+", value.lower()) if len(token) >= 3
    ]
    return " & ".join(f"{token}:*" for token in tokens)


def _build_fragment(text_value: str, query: str, max_length: int = 220) -> str:
    terms = [
        term
        for term in re.findall(r"[\wáéíóúüñ]+", query, flags=re.IGNORECASE)
        if len(term) >= 3
    ]
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


def search_legislacion(
    q: str,
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
):
    db = next(get_db())

    try:
        filters: list[str] = []
        params: dict[str, str] = {"q": q}

        if _is_postgres(db):
            tsquery = _to_tsquery(q)
            if tsquery:
                filters.append("va.search_vector @@ to_tsquery('spanish', :tsquery)")
                params["tsquery"] = tsquery
            else:
                filters.append("va.texto ILIKE :term")
                params["term"] = f"%{q}%"
        else:
            filters.append("LOWER(va.texto) LIKE LOWER(:term)")
            params["term"] = f"%{q}%"

        if norma is not None:
            filters.append("n.codigo = :norma")
            params["norma"] = norma
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
                "va.vigente_desde <= :vigente_en AND (va.vigente_hasta IS NULL OR va.vigente_hasta >= :vigente_en)"
            )
            params["vigente_en"] = vigente_en

        where_clause = " AND ".join(filters)
        if _is_postgres(db):
            query = text(
                """
                SELECT
                    n.codigo,
                    a.numero,
                    a.tipo,
                    va.texto,
                    va.vigente_desde,
                    va.vigente_hasta,
                    ts_rank(va.search_vector, to_tsquery('spanish', :tsquery)) AS rank,
                    ts_headline(
                        'spanish',
                        va.texto,
                        to_tsquery('spanish', :tsquery),
                        'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=25, MinWords=8'
                    ) AS fragmento
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE """
                + where_clause
                + """
                ORDER BY rank DESC, va.vigente_desde DESC
                LIMIT 10
                """
            )
        else:
            query = text(
                """
                SELECT n.codigo, a.numero, a.tipo, va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE """
                + where_clause
                + """
                ORDER BY va.vigente_desde DESC
                LIMIT 10
                """
            )

        rows = db.execute(query, params).mappings()
        return {
            "q": q,
            "resultados": [
                {
                    "tipo": row["tipo"],
                    "norma": row["codigo"],
                    "numero": row["numero"],
                    "texto": row["texto"],
                    "fragmento": row.get("fragmento")
                    or _build_fragment(row["texto"], q),
                    "vigente_desde": str(row["vigente_desde"]),
                    "vigente_hasta": str(row["vigente_hasta"])
                    if row["vigente_hasta"]
                    else None,
                    "rank": round(float(row["rank"]), 4)
                    if row.get("rank") is not None
                    else None,
                    "confianza": {
                        "nivel": 1,
                        "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                        "aviso": None,
                    },
                }
                for row in rows
            ],
        }
    finally:
        db.close()
