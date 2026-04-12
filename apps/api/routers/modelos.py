from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from db import get_db

router = APIRouter(prefix="/v1/modelos", tags=["modelos"])


@router.get("", operation_id="list_modelos")
async def list_modelos():
    """Lista todos los modelos AEAT disponibles."""
    db = next(get_db())
    rows = db.execute(
        text(
            """
            SELECT
                m.codigo,
                m.nombre,
                m.periodo,
                m.impuesto,
                COUNT(ma.articulo_id) AS articulos_count
            FROM aeat_modelo m
            LEFT JOIN modelo_articulo ma ON ma.modelo_id = m.id
            GROUP BY m.id, m.codigo, m.nombre, m.periodo, m.impuesto
            ORDER BY m.codigo
            """
        )
    ).mappings()

    return {
        "modelos": [
            {
                "codigo": row["codigo"],
                "nombre": row["nombre"],
                "periodo": row["periodo"],
                "impuesto": row["impuesto"],
                "articulos_count": row["articulos_count"],
            }
            for row in rows
        ]
    }


@router.get("/{codigo}", operation_id="get_modelo")
async def get_modelo(codigo: str):
    """Detalle de un modelo con artículos y doctrina relacionada."""
    db = next(get_db())

    # Modelo metadata
    model_row = db.execute(
        text(
            """
            SELECT codigo, nombre, periodo, impuesto, url_info
            FROM aeat_modelo
            WHERE codigo = :codigo
            LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).mappings().first()

    if not model_row:
        raise HTTPException(
            status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
        )

    # Related articles with source
    art_rows = db.execute(
        text(
            """
            SELECT
                n.codigo AS norma,
                a.numero,
                a.titulo,
                ma.casilla,
                ma.nota,
                ma.fuente,
                ma.url_fuente
            FROM modelo_articulo ma
            JOIN articulo a ON a.id = ma.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE ma.modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
            ORDER BY n.codigo, a.numero
            """
        ),
        {"codigo": codigo},
    ).mappings()

    articulos = [
        {
            "norma": row["norma"],
            "numero": row["numero"],
            "titulo": row["titulo"],
            "casilla": row["casilla"],
            "nota": row["nota"],
            "fuente": row["fuente"],
            "url_fuente": row["url_fuente"],
        }
        for row in art_rows
    ]

    # Related doctrine via linked articles (real join, no invention)
    # For each article linked to this model, find doctrina documents
    # that reference that same article.
    if articulos:
        # Build conditions for each (norma, numero) pair
        conditions = []
        params = {}
        for i, art in enumerate(articulos):
            conditions.append(f"n.codigo = :n{i} AND a.numero = :a{i}")
            params[f"n{i}"] = art["norma"]
            params[f"a{i}"] = art["numero"]

        where_clause = " OR ".join(conditions)

        doc_rows = db.execute(
            text(
                f"""
                SELECT DISTINCT
                    di.referencia,
                    di.organismo_emisor,
                    di.fecha,
                    n.codigo AS norma,
                    a.numero
                FROM documento_articulo da
                JOIN documento_interpretativo di ON di.id = da.documento_id
                JOIN articulo a ON a.id = da.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE {where_clause}
                ORDER BY di.fecha DESC
                LIMIT 50
                """
            ),
            params,
        ).mappings()

        # Group by reference
        doctrina_map: dict[str, dict] = {}
        for row in doc_rows:
            ref = row["referencia"]
            if ref not in doctrina_map:
                doctrina_map[ref] = {
                    "referencia": ref,
                    "organismo_emisor": row["organismo_emisor"],
                    "fecha": str(row["fecha"]) if row["fecha"] else None,
                    "via_articulos": [],
                }
            doctrina_map[ref]["via_articulos"].append(
                {"norma": row["norma"], "numero": row["numero"]}
            )

        doctrina_relacionada = list(doctrina_map.values())
    else:
        doctrina_relacionada = []

    return {
        "codigo": model_row["codigo"],
        "nombre": model_row["nombre"],
        "periodo": model_row["periodo"],
        "impuesto": model_row["impuesto"],
        "url_info": model_row["url_info"],
        "articulos": articulos,
        "doctrina_relacionada": doctrina_relacionada,
    }


@router.get("/{codigo}/articulos", operation_id="get_modelo_articulos")
async def get_modelo_articulos(codigo: str):
    """Solo artículos enlazados a un modelo (para filtros/paginación futura)."""
    db = next(get_db())

    model_row = db.execute(
        text(
            """
            SELECT codigo FROM aeat_modelo WHERE codigo = :codigo LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).mappings().first()

    if not model_row:
        raise HTTPException(
            status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
        )

    rows = db.execute(
        text(
            """
            SELECT
                n.codigo AS norma,
                a.numero,
                a.titulo,
                ma.casilla,
                ma.nota,
                ma.fuente,
                ma.url_fuente
            FROM modelo_articulo ma
            JOIN articulo a ON a.id = ma.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE ma.modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
            ORDER BY n.codigo, a.numero
            """
        ),
        {"codigo": codigo},
    ).mappings()

    return {
        "codigo": codigo,
        "articulos": [
            {
                "norma": row["norma"],
                "numero": row["numero"],
                "titulo": row["titulo"],
                "casilla": row["casilla"],
                "nota": row["nota"],
                "fuente": row["fuente"],
                "url_fuente": row["url_fuente"],
            }
            for row in rows
        ],
    }
