from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    ArticuloDetail as ArticuloDetailSchema,
    ArticulosListResponse,
    Norma as NormaSchema,
    NormasListResponse,
)

router = APIRouter(prefix="/v1/legislacion", tags=["legislacion"])


@router.get("", operation_id="list_legislacion", response_model=NormasListResponse)
async def list_legislacion():
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, titulo, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                ORDER BY codigo
                """
            )
        ).mappings()
        return {"normas": list(rows)}


@router.get("/cobertura")
async def get_cobertura():
    """Recuento de artículos y versiones por norma para verificar ingesta."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    n.codigo,
                    n.titulo,
                    COUNT(DISTINCT a.id) AS articulos,
                    COUNT(va.id) AS versiones,
                    MAX(va.vigente_desde) AS ultima_version
                FROM norma n
                LEFT JOIN articulo a ON a.norma_id = n.id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                GROUP BY n.id, n.codigo, n.titulo
                ORDER BY n.codigo
                """
            )
        ).mappings()
        return {
            "normas": [
                {
                    "codigo": row["codigo"],
                    "titulo": row["titulo"],
                    "articulos": row["articulos"],
                    "versiones": row["versiones"],
                    "ultima_version": str(row["ultima_version"])
                    if row["ultima_version"]
                    else None,
                }
                for row in rows
            ]
        }


@router.get("/{codigo}", operation_id="get_norma", response_model=NormaSchema)
async def get_norma(codigo: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                SELECT codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                WHERE codigo = :codigo
                """
                ),
                {"codigo": codigo},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Norma no encontrada"})
        return dict(row)


@router.get("/{codigo}/articulos", operation_id="list_articulos", response_model=ArticulosListResponse,
            summary="Lista articulos de una norma")
async def list_articulos(codigo: str, tipo: str | None = Query(None, description="Filtrar por tipo de articulo")):
    with db_session() as db:
        filters = ["n.codigo = :codigo"]
        params = {"codigo": codigo}

        if tipo is not None:
            filters.append("a.tipo = :tipo")
            params["tipo"] = tipo

        rows = list(
            db.execute(
                text(
                    """
                    SELECT a.numero, a.titulo, a.tipo
                    FROM norma n
                    JOIN articulo a ON a.norma_id = n.id
                    WHERE {where_clause}
                    ORDER BY a.numero
                    """.format(where_clause=" AND ".join(filters))
                ),
                params,
            ).mappings()
        )
        if not rows:
            existe_norma = db.execute(
                text("SELECT 1 FROM norma WHERE codigo = :codigo"),
                {"codigo": codigo},
            ).first()
            if not existe_norma:
                raise HTTPException(
                    status_code=404, detail={"error": "Norma no encontrada"}
                )
        return {"norma": codigo, "articulos": rows}


@router.get("/{codigo}/articulos/{numero}", operation_id="get_articulo", response_model=ArticuloDetailSchema,
            summary="Detalle de un articulo de ley")
async def get_articulo(codigo: str, numero: str, vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)")):
    with db_session() as db:
        filters = ["n.codigo = :codigo", "a.numero = :numero"]
        params = {"codigo": codigo, "numero": numero}

        if vigente_en is not None:
            filters.append(
                """
                va.vigente_desde <= :vigente_en
                AND (va.vigente_hasta IS NULL OR va.vigente_hasta >= :vigente_en)
                """
            )
            params["vigente_en"] = vigente_en

        row = (
            db.execute(
                text(
                    """
                SELECT n.codigo, a.numero, va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE {where_clause}
                ORDER BY va.vigente_desde DESC
                LIMIT 1
                """.format(where_clause=" AND ".join(filters))
                ),
                params,
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail={"error": "Articulo no encontrado"})
        return {
            "norma": row["codigo"],
            "numero": row["numero"],
            "texto": row["texto"],
            "vigente_desde": str(row["vigente_desde"]),
            "vigente_hasta": str(row["vigente_hasta"]) if row["vigente_hasta"] else None,
            "confianza": {
                "nivel": 1,
                "fuentes": [f"{row['codigo']} art. {row['numero']}"],
                "aviso": None,
            },
        }


@router.get(
    "/{codigo}/articulos/{numero}/historial", operation_id="get_articulo_historial"
)
async def get_articulo_historial(codigo: str, numero: str):
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT va.texto, va.vigente_desde, va.vigente_hasta
                FROM norma n
                JOIN articulo a ON a.norma_id = n.id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE n.codigo = :codigo AND a.numero = :numero
                ORDER BY va.vigente_desde DESC
                """
            ),
            {"codigo": codigo, "numero": numero},
        ).mappings()
        historial = [
            {
                "texto": row["texto"],
                "vigente_desde": str(row["vigente_desde"]),
                "vigente_hasta": str(row["vigente_hasta"])
                if row["vigente_hasta"]
                else None,
            }
            for row in rows
        ]
        if not historial:
            raise HTTPException(status_code=404, detail={"error": "Articulo no encontrado"})
        return {"norma": codigo, "numero": numero, "historial": historial}
