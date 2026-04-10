from fastapi import APIRouter, Query
from sqlalchemy import text

from db import get_db

router = APIRouter(tags=["buscar"])


def _is_postgres(db) -> bool:
    """Detect if we're running against Postgres (has pg_trgm) or SQLite."""
    try:
        db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
        return True
    except Exception:
        return False


def _query_results(
    q: str,
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
):
    db = next(get_db())
    use_trgm = _is_postgres(db)

    base_filters: list[str] = []
    params: dict[str, str] = {"q": q}

    if use_trgm:
        # word_similarity works better for searching phrases within long text
        base_filters.append("word_similarity(:q, va.texto) > 0.15")
        params["q"] = q
    else:
        base_filters.append("LOWER(va.texto) LIKE LOWER(:term)")
        params["term"] = f"%{q}%"

    if norma is not None:
        base_filters.append("n.codigo = :norma")
        params["norma"] = norma
    if fuente is not None:
        base_filters.append("n.tipo_fuente = :fuente")
        params["fuente"] = fuente
    if ambito is not None:
        base_filters.append("n.ambito = :ambito")
        params["ambito"] = ambito
    if tipo is not None:
        base_filters.append("a.tipo = :tipo")
        params["tipo"] = tipo
    if vigente_en is not None:
        base_filters.append(
            "va.vigente_desde <= :vigente_en AND (va.vigente_hasta IS NULL OR va.vigente_hasta >= :vigente_en)"
        )
        params["vigente_en"] = vigente_en

    order_clause = "ORDER BY word_similarity(:q, va.texto) DESC" if use_trgm else "ORDER BY va.vigente_desde DESC"

    rows = db.execute(
        text(
            """
            SELECT n.codigo, a.numero, a.tipo, va.texto, va.vigente_desde, va.vigente_hasta
                {sim_col}
            FROM norma n
            JOIN articulo a ON a.norma_id = n.id
            JOIN version_articulo va ON va.articulo_id = a.id
            WHERE {where_clause}
            {order_clause}
            LIMIT 10
            """.format(
                where_clause=" AND ".join(base_filters),
                order_clause=order_clause,
                sim_col=", word_similarity(:q, va.texto) AS sim" if use_trgm else "",
            )
        ),
        params,
    ).mappings()

    results = []
    for row in rows:
        sim = float(row["sim"]) if use_trgm else None
        results.append(
            {
                "tipo": row["tipo"],
                "norma": row["codigo"],
                "numero": row["numero"],
                "texto": row["texto"],
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
                "similarity": round(sim, 3) if sim is not None else None,
                "confianza": {
                    "nivel": 1,
                    "fuentes": [f'{row["codigo"]} art. {row["numero"]}'],
                    "aviso": None,
                },
            }
        )
    return results


@router.get("/v1/buscar")
async def buscar(
    q: str = Query(..., min_length=1),
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    norma: str | None = None,
    vigente_en: str | None = None,
):
    return {"q": q, "resultados": _query_results(q, norma, fuente, ambito, tipo, vigente_en)}


@router.get("/v1/legislacion/buscar")
async def buscar_legislacion(
    q: str = Query(..., min_length=1),
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
):
    return {"q": q, "resultados": _query_results(q, norma, fuente, ambito, tipo, vigente_en)}
