from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import get_db

router = APIRouter(prefix="/v1/doctrina", tags=["doctrina"])


@router.get("/buscar", operation_id="buscar_doctrina")
async def buscar_doctrina(
    q: str = Query(..., min_length=1),
    tipo: str | None = None,
    desde: str | None = None,
):
    db = next(get_db())
    filters = [
        "(LOWER(d.texto) LIKE LOWER(:term) OR LOWER(COALESCE(d.titulo, '')) LIKE LOWER(:term))"
    ]
    params = {"term": f"%{q}%"}

    if tipo is not None:
        filters.append("d.tipo_documento = :tipo")
        params["tipo"] = tipo
    if desde is not None:
        filters.append("d.fecha >= :desde")
        params["desde"] = desde

    rows = db.execute(
        text(
            """
            SELECT d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto
            FROM documento_interpretativo d
            WHERE {where_clause}
            ORDER BY d.fecha DESC
            LIMIT 20
            """.format(where_clause=" AND ".join(filters))
        ),
        params,
    ).mappings()

    # TODO: migrate doctrina search to tsvector when document volume justifies it.
    return {
        "q": q,
        "resultados": [
            {
                "referencia": row["referencia"],
                "tipo_documento": row["tipo_documento"],
                "organismo_emisor": row["organismo_emisor"],
                "fecha": str(row["fecha"]),
                "titulo": row["titulo"],
                "fragmento": row["texto"][:220]
                + ("..." if len(row["texto"]) > 220 else ""),
            }
            for row in rows
        ],
    }


@router.get("/{referencia}", operation_id="get_doctrina")
async def get_doctrina(referencia: str):
    db = next(get_db())
    row = (
        db.execute(
            text(
                """
            SELECT
                d.referencia,
                d.tipo_documento,
                d.organismo_emisor,
                d.texto,
                a.numero AS articulo_numero
            FROM documento_interpretativo d
            LEFT JOIN documento_articulo da ON da.documento_id = d.id
            LEFT JOIN articulo a ON a.id = da.articulo_id
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

    has_anchor = bool(row["articulo_numero"])
    return {
        "referencia": row["referencia"],
        "tipo_documento": row["tipo_documento"],
        "organismo_emisor": row["organismo_emisor"],
        "texto": row["texto"],
        "confianza": {
            "nivel": 2 if has_anchor else 0,
            "fuentes": [row["referencia"]],
            "aviso": None
            if has_anchor
            else "Criterio sin anclaje normativo suficiente",
        },
    }
