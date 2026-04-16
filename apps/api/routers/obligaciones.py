from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import ObligacionDetail, ObligacionesListResponse

router = APIRouter(prefix="/v1/obligaciones", tags=["obligaciones"])


@router.get("", response_model=ObligacionesListResponse, operation_id="listar_obligaciones")
async def listar_obligaciones(
    fuente: str | None = Query(None, description="Filtrar por fuente principal"),
    ambito: str | None = Query(None, description="Filtrar por ámbito"),
    sujeto_obligado: str | None = Query(None, description="Filtrar por sujeto obligado"),
):
    filters = ["1=1"]
    params: dict[str, str] = {}

    if fuente:
        filters.append("o.fuente = :fuente")
        params["fuente"] = fuente

    if ambito:
        filters.append("o.ambito = :ambito")
        params["ambito"] = ambito

    if sujeto_obligado:
        filters.append("o.sujeto_obligado = :sujeto_obligado")
        params["sujeto_obligado"] = sujeto_obligado

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                       sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia
                FROM obligacion_regulatoria o
                WHERE {where_clause}
                ORDER BY fuente ASC, codigo ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {"obligaciones": [dict(row) for row in rows]}


@router.get("/{codigo}", response_model=ObligacionDetail, operation_id="get_obligacion")
async def get_obligacion(codigo: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                           sujeto_obligado, periodicidad, reporte_modelo, ambito,
                           estado_vigencia, documento_origen_tipo, documento_origen_ref,
                           seccion_origen, anexo_origen, nota
                    FROM obligacion_regulatoria
                    WHERE codigo = :codigo
                    LIMIT 1
                    """
                ),
                {"codigo": codigo},
            )
            .mappings()
            .first()
        )

        if not row:
            raise HTTPException(status_code=404, detail={"error": "Obligación no encontrada"})

        documentos = list(
            db.execute(
                text(
                    """
                    SELECT d.referencia, d.organismo_emisor, d.tipo_fuente, d.tipo_documento, od.tipo_relacion
                    FROM obligacion_documento od
                    JOIN obligacion_regulatoria o ON o.id = od.obligacion_id
                    JOIN documento_interpretativo d ON d.id = od.documento_id
                    WHERE o.codigo = :codigo
                    ORDER BY d.referencia ASC
                    """
                ),
                {"codigo": codigo},
            ).mappings()
        )

        return {
            **dict(row),
            "documentos": [dict(item) for item in documentos],
        }
