"""Router para Ley 13/2023 de regulacion de la IA.

Endpoints para consultar la normativa de IA y sus articulos.
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    ArticuloHistoryItem,
    ArticulosHistoryResponse,
    ArticuloListItem,
    ArticulosListResponse,
    Norma,
    NormasListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/ley13-2023", tags=["ley 13/2023 ia"])


@router.get(
    "",
    response_model=NormasListResponse,
    operation_id="listar_normas_ley13_2023",
)
async def listar_normas(
    estado: str = Query(
        "activo", description="Estado: activo, inactivo, obsoleto"
    ),
):
    """Listar normas de la Ley 13/2023."""
    filters = ["codigo = :codigo"]
    params: dict = {"codigo": "LEY13_2023"}

    if estado:
        filters.append("estado_cobertura = :estado")
        params["estado"] = estado

    where_clause = "WHERE " + " AND ".join(filters)

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT codigo, titulo, boe_id, eli_uri, jurisdiccion,
                       tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                {where_clause}
                ORDER BY vigente_desde DESC
                """
            ),
            params,
        ).mappings()

        items = [Norma(**dict(row)).model_dump() for row in rows]

        total = db.execute(
            text(f"SELECT COUNT(*) FROM norma {where_clause}"),
            params,
        ).scalar()

        return {"normas": items, "total": total}


@router.get(
    "/articulos",
    response_model=ArticulosListResponse,
    operation_id="listar_articulos_ley13_2023",
)
async def listar_articulos(
    codigo_norma: str = Query("LEY13_2023", description="Codigo de la norma"),
    tipo: str | None = Query(
        None, description="Tipo: articulo, disposicion_adicional, etc."
    ),
    vigente: bool = Query(True, description="Solo vigentes"),
):
    """Listar articulos de la Ley 13/2023."""
    filters = ["n.codigo = :codigo_norma"]
    params: dict = {"codigo_norma": codigo_norma}

    if tipo:
        filters.append("a.tipo = :tipo")
        params["tipo"] = tipo

    if vigente:
        filters.append("(va.vigente_hasta IS NULL OR va.vigente_hasta > CURRENT_DATE)")

    where_clause = "WHERE " + " AND ".join(filters)

    with db_session() as db:
        rows = db.execute(
            text(
                f"""
                SELECT a.numero, a.titulo, a.tipo
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                    AND va.vigente_desde = (
                        SELECT MAX(va2.vigente_desde)
                        FROM version_articulo va2
                        WHERE va2.articulo_id = a.id
                    )
                {where_clause}
                ORDER BY CAST(a.numero AS INTEGER) ASC
                """
            ),
            params,
        ).mappings()

        items = [ArticuloListItem(**dict(row)).model_dump() for row in rows]

        # COUNT usa la misma logica de JOINs que la query principal
        total = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                    AND va.vigente_desde = (
                        SELECT MAX(va2.vigente_desde)
                        FROM version_articulo va2
                        WHERE va2.articulo_id = a.id
                    )
                {where_clause}
                """
            ),
            params,
        ).scalar()

        return {"norma": codigo_norma, "articulos": items, "total": total}


@router.get(
    "/articulos/{articulo_id}",
    operation_id="detalle_articulo_ley13_2023",
)
async def detalle_articulo(articulo_id: int):
    """Detalle de un articulo de la Ley 13/2023."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT a.id as articulo_id, a.norma_id, a.numero, a.titulo, a.tipo,
                       va.texto, va.vigente_desde, va.vigente_hasta,
                       n.codigo as norma_codigo, n.titulo as norma_titulo
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                LEFT JOIN version_articulo va ON va.articulo_id = a.id
                    AND va.vigente_desde = (
                        SELECT MAX(va2.vigente_desde)
                        FROM version_articulo va2
                        WHERE va2.articulo_id = a.id
                    )
                WHERE a.id = :articulo_id
                """
            ),
            {"articulo_id": articulo_id},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Articulo no encontrado: {articulo_id}",
            )

        return dict(row)


@router.get(
    "/articulos/{articulo_id}/historial",
    response_model=ArticulosHistoryResponse,
    operation_id="historial_articulo_ley13_2023",
)
async def historial_articulo(articulo_id: int):
    """Historial de versiones de un articulo de la Ley 13/2023."""
    with db_session() as db:
        row = db.execute(
            text("SELECT n.codigo FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE a.id = :articulo_id"),
            {"articulo_id": articulo_id},
        ).mappings().first()

        codigo_norma = row["codigo"] if row else "LEY13_2023"

        rows = db.execute(
            text(
                """
                SELECT a.numero, a.titulo, a.tipo,
                       va.texto, va.vigente_desde, va.vigente_hasta
                FROM version_articulo va
                JOIN articulo a ON a.id = va.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE va.articulo_id = :articulo_id
                ORDER BY va.vigente_desde DESC
                """
            ),
            {"articulo_id": articulo_id},
        ).mappings()

        items = [ArticuloHistoryItem(**dict(row)).model_dump() for row in rows]

        if not items:
            raise HTTPException(
                status_code=404,
                detail=f"Articulo no encontrado: {articulo_id}",
            )

        return {"norma": codigo_norma, "articulos": items}


@router.get(
    "/{codigo}",
    response_model=Norma,
    operation_id="detalle_norma_ley13_2023",
)
async def detalle_norma(codigo: str = "LEY13_2023"):
    """Detalle de una norma de la Ley 13/2023."""
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT codigo, titulo, boe_id, eli_uri, jurisdiccion,
                       tipo_fuente, tipo_documento, ambito, estado_cobertura
                FROM norma
                WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Norma no encontrada: {codigo}",
            )

        return Norma(**dict(row))
