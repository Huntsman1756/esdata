"""International obligations (FATCA / CRS) router.

Endpoints para consultar obligaciones internacionales de reporte
como FATCA, CRS y acuerdos IGA.
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    ObligacionInternacionalDetailResponse,
    ObligacionInternacionalListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/internacional/obligaciones", tags=["internacional"])


@router.get(
    "",
    response_model=ObligacionInternacionalListResponse,
    operation_id="listar_obligaciones_internacionales",
)
async def listar_obligaciones_internacionales(
    tipo: str | None = Query(None, description="Filtrar por tipo: tratado, convenio, directiva, ley"),
    estado: str = Query("activo", description="Estado: activo, inactivo, obsoleto"),
    jurisdiccion: str | None = Query(None, description="Filtrar por jurisdiccion de origen"),
):
    filters = ["1=1"]
    params: dict = {}

    if tipo:
        filters.append("tipo = :tipo")
        params["tipo"] = tipo

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado

    if jurisdiccion:
        filters.append("jurisdiccion_origen = :jurisdiccion")
        params["jurisdiccion"] = jurisdiccion

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, titulo, tipo, jurisdiccion_origen,
                       jurisdiccion_aplicacion, vigente_desde, vigente_hasta, estado
                FROM obligacion_internacional
                WHERE {where_clause}
                ORDER BY vigente_desde DESC, codigo ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        items = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM obligacion_internacional
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {"items": items, "total": total}


@router.get(
    "/{codigo}",
    response_model=ObligacionInternacionalDetailResponse,
    operation_id="detalle_obligacion_internacional",
)
async def detalle_obligacion_internacional(codigo: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, titulo, tipo, jurisdiccion_origen,
                       jurisdiccion_aplicacion, vigente_desde, vigente_hasta,
                       descripcion, estado, creado_en, actualizado_en
                FROM obligacion_internacional
                WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Obligacion internacional no encontrada: {codigo}",
            )

        return {"item": dict(row)}
