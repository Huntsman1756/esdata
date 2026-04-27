"""Micro-obligaciones regulatorias (Fase 20).

Endpoints para consultar la taxonomia de micro-obligaciones MiFID/CNMV/SEPBLAC/LECR/SOCIMI/CSDR/ECR/Doctrina DGT
y su mapeo con obligaciones regulatorias.
"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    MicroObligacionByObligacionResponse,
    MicroObligacionDetail,
    MicroObligacionListResponse,
)

router = APIRouter(prefix="/v1/micro-obligaciones", tags=["micro-obligaciones"])


@router.get("", response_model=MicroObligacionListResponse, operation_id="listar_micro_obligaciones")
async def listar_micro_obligaciones(
    regulacion: str | None = Query(None, description="Filtrar por regulacion: mifid_ii, mifir, mar, cnmv_lmcv, pblcft"),
    ambito: str | None = Query(None, description="Filtrar por ambito operativo"),
    severidad: str | None = Query(None, description="Filtrar por criticidad: baja, media, alta"),
    owner_rol: str | None = Query(None, description="Filtrar por rol responsable"),
    activo: bool = Query(True, description="Solo micro-obligaciones activas"),
):
    filters = ["1=1"]
    params: dict = {}

    if regulacion:
        filters.append("regulacion_relacionada = :regulacion")
        params["regulacion"] = regulacion

    if ambito:
        filters.append("ambito = :ambito")
        params["ambito"] = ambito

    if severidad:
        filters.append("severidad = :severidad")
        params["severidad"] = severidad

    if owner_rol:
        filters.append("owner_rol = :owner_rol")
        params["owner_rol"] = owner_rol

    if activo:
        filters.append("activo = :activo")
        params["activo"] = True

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, nombre, descripcion, regulacion_relacionada,
                       ambito, trigger_evento, frecuencia, owner_rol, severidad, activo
                FROM micro_obligacion
                WHERE {where_clause}
                ORDER BY regulacion_relacionada ASC, codigo ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        micro_obligaciones = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM micro_obligacion
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {"micro_obligaciones": micro_obligaciones, "total": total}


@router.get("/{codigo}", response_model=MicroObligacionDetail, operation_id="get_micro_obligacion")
async def get_micro_obligacion(codigo: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, nombre, descripcion, regulacion_relacionada,
                       ambito, trigger_evento, frecuencia, owner_rol, severidad, activo
                FROM micro_obligacion
                WHERE codigo = :codigo
                LIMIT 1
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Micro-obligacion no encontrada"})

        obligacion_ids = db.execute(
            text(
                """
                SELECT omo.obligacion_id
                FROM obligacion_micro_obligacion omo
                JOIN obligacion_regulatoria oblg ON oblg.id = omo.obligacion_id
                WHERE omo.micro_obligacion_id = :micro_id
                ORDER BY omo.orden ASC
                """
            ),
            {"micro_id": row["id"]},
        ).mappings()

        obligaciones_relacionadas = [dict(r) for r in obligacion_ids]

        result = dict(row)
        result["obligaciones_relacionadas"] = obligaciones_relacionadas
        return result


@router.get(
    "/by-obligacion/{obligacion_codigo}",
    response_model=MicroObligacionByObligacionResponse,
    operation_id="micro_obligaciones_por_obligacion",
)
async def get_micro_obligaciones_by_obligacion(obligacion_codigo: str):
    with db_session() as db:
        obligacion_row = db.execute(
            text(
                """
                SELECT id, codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                       sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia,
                       plazo_dias, frecuencia_presentacion, ventana_presentacion,
                       trigger_presentacion, sancion_min, sancion_max, prescripcion_anos
                FROM obligacion_regulatoria
                WHERE codigo = :codigo
                LIMIT 1
                """
            ),
            {"codigo": obligacion_codigo},
        ).mappings().first()

        if not obligacion_row:
            raise HTTPException(status_code=404, detail={"error": "Obligacion regulatoria no encontrada"})

        rows = db.execute(
            text(
                """
                SELECT m.codigo, m.nombre, m.descripcion, m.regulacion_relacionada,
                       m.ambito, m.trigger_evento, m.frecuencia, m.owner_rol,
                       m.severidad, m.activo
                FROM micro_obligacion m
                JOIN obligacion_micro_obligacion omo ON omo.micro_obligacion_id = m.id
                WHERE omo.obligacion_id = :obligacion_id
                ORDER BY omo.orden ASC, m.codigo ASC
                """
            ),
            {"obligacion_id": obligacion_row["id"]},
        ).mappings()

        micro_obligaciones = [dict(row) for row in rows]

        return {"obligacion": dict(obligacion_row), "micro_obligaciones": micro_obligaciones}
