from fastapi import APIRouter, Query
from sqlalchemy import text

from db import get_db

router = APIRouter(tags=["buscar"])


def _query_results(
    q: str,
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
):
    db = next(get_db())
    filters = ["LOWER(va.texto) LIKE LOWER(:term)"]
    params = {"term": f"%{q}%"}

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
        filters.append("va.vigente_desde <= :vigente_en AND (va.vigente_hasta IS NULL OR va.vigente_hasta >= :vigente_en)")
        params["vigente_en"] = vigente_en

    rows = db.execute(
        text(
            """
            SELECT n.codigo, a.numero, a.tipo, va.texto, va.vigente_desde, va.vigente_hasta
            FROM norma n
            JOIN articulo a ON a.norma_id = n.id
            JOIN version_articulo va ON va.articulo_id = a.id
            WHERE {where_clause}
            ORDER BY va.vigente_desde DESC
            LIMIT 10
            """.format(where_clause=" AND ".join(filters))
        ),
        params,
    ).mappings()
    return [
        {
            "tipo": row["tipo"],
            "norma": row["codigo"],
            "numero": row["numero"],
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "confianza": {
                "nivel": 1,
                "fuentes": [f'{row["codigo"]} art. {row["numero"]}'],
                "aviso": None,
            },
        }
        for row in rows
    ]


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
