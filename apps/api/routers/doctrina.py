from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import get_db
from schemas import (
    DoctrinaDetail as DoctrinaDetailSchema,
    DoctrinaSearchResponse,
    DoctrinaSearchResult,
)

router = APIRouter(prefix="/v1/doctrina", tags=["doctrina"])


@router.get("/buscar", operation_id="buscar_doctrina", response_model=DoctrinaSearchResponse,
            summary="Buscar doctrina interpretativa")
async def buscar_doctrina(
    q: str = Query(..., min_length=1, description="Termino de busqueda en texto de doctrina"),
    tipo: str | None = Query(None, description="Filtrar por tipo (consulta_vinculante, resolucion_teac, etc.)"),
    desde: str | None = Query(None, description="Fecha minima (YYYY-MM-DD)"),
    organismo_emisor: str | None = Query(None, description="Filtrar por organismo (DGT, TEAC, etc.)"),
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
    if organismo_emisor is not None:
        filters.append("LOWER(d.organismo_emisor) = LOWER(:organismo_emisor)")
        params["organismo_emisor"] = organismo_emisor

    rows = db.execute(
        text(
            """
            SELECT
                d.referencia,
                d.tipo_documento,
                d.organismo_emisor,
                d.fecha,
                d.titulo,
                d.texto,
                n.codigo AS norma,
                a.numero,
                MAX(da.confianza_enlace) AS nivel_enlace
            FROM documento_interpretativo d
            LEFT JOIN documento_articulo da ON da.documento_id = d.id
            LEFT JOIN articulo a ON a.id = da.articulo_id
            LEFT JOIN norma n ON n.id = a.norma_id
            WHERE {where_clause}
            GROUP BY d.id, d.referencia, d.tipo_documento, d.organismo_emisor, d.fecha, d.titulo, d.texto, n.codigo, a.numero
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
                "nivel_enlace": float(row["nivel_enlace"] or 0),
                "norma": row["norma"],
                "numero": row["numero"],
                "fragmento": row["texto"][:220]
                + ("..." if len(row["texto"]) > 220 else ""),
            }
            for row in rows
        ],
    }


@router.get("/{referencia:path}", operation_id="get_doctrina", response_model=DoctrinaDetailSchema)
async def get_doctrina(referencia: str):
    db = next(get_db())
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
