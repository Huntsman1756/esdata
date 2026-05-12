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
    limit: int = Query(100, ge=1, le=500, description="Numero maximo de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginacion"),
):
    filters = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if tipo:
        filters.append("oi.tipo = :tipo")
        params["tipo"] = tipo

    if estado:
        filters.append("oi.estado = :estado")
        params["estado"] = estado

    if jurisdiccion:
        filters.append("oi.jurisdiccion_origen = :jurisdiccion")
        params["jurisdiccion"] = jurisdiccion

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT oi.id, oi.codigo, oi.titulo, oi.tipo, oi.jurisdiccion_origen,
                       oi.jurisdiccion_aplicacion,
                       CAST(oi.vigente_desde AS TEXT) AS vigente_desde,
                       CAST(oi.vigente_hasta AS TEXT) AS vigente_hasta,
                       oi.estado, oi.descripcion,
                       sr.dgt_url AS source_url,
                       sr.worker_name AS source_worker,
                       CAST(sr.fetched_at AS TEXT) AS source_fetched_at
                FROM obligacion_internacional oi
                LEFT JOIN source_revision sr
                  ON sr.worker_name = 'official-regulatory-references'
                 AND sr.source_entity_tipo = 'obligacion_internacional'
                 AND sr.source_entity_id = oi.codigo
                WHERE {where_clause}
                ORDER BY oi.vigente_desde DESC, oi.codigo ASC
                LIMIT :limit OFFSET :offset
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        items = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM obligacion_internacional oi
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
        }


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
                SELECT oi.id, oi.codigo, oi.titulo, oi.tipo, oi.jurisdiccion_origen,
                       oi.jurisdiccion_aplicacion,
                       CAST(oi.vigente_desde AS TEXT) AS vigente_desde,
                       CAST(oi.vigente_hasta AS TEXT) AS vigente_hasta,
                       oi.descripcion, oi.estado,
                       CAST(oi.creado_en AS TEXT) AS creado_en,
                       CAST(oi.actualizado_en AS TEXT) AS actualizado_en,
                       sr.dgt_url AS source_url,
                       sr.worker_name AS source_worker,
                       CAST(sr.fetched_at AS TEXT) AS source_fetched_at
                FROM obligacion_internacional oi
                LEFT JOIN source_revision sr
                  ON sr.worker_name = 'official-regulatory-references'
                 AND sr.source_entity_tipo = 'obligacion_internacional'
                 AND sr.source_entity_id = oi.codigo
                WHERE oi.codigo = :codigo
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
