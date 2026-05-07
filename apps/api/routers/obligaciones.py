from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from applicability import build_sociedad_valores_profile, obligation_applies
from db import db_session
from obligaciones_metadata import enrich_obligacion_metadata
from schemas import ObligacionDetail, ObligacionesAplicablesResponse, ObligacionesListResponse

router = APIRouter(prefix="/v1/obligaciones", tags=["obligaciones"])


@router.get("", response_model=ObligacionesListResponse, operation_id="listar_obligaciones")
async def listar_obligaciones(
    fuente: str | None = Query(None, description="Filtrar por fuente principal"),
    ambito: str | None = Query(None, description="Filtrar por ámbito"),
    sujeto_obligado: str | None = Query(None, description="Filtrar por sujeto obligado"),
    frecuencia: str | None = Query(None, description="Filtrar por frecuencia de presentación"),
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

    if frecuencia:
        filters.append("o.frecuencia_presentacion = :frecuencia")
        params["frecuencia"] = frecuencia

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                       sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia,
                       plazo_dias, frecuencia_presentacion, ventana_presentacion,
                       trigger_presentacion, sancion_min, sancion_max, prescripcion_anos
                FROM obligacion_regulatoria o
                WHERE {where_clause}
                ORDER BY fuente ASC, codigo ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return {"obligaciones": [enrich_obligacion_metadata(dict(row)) for row in rows]}


@router.get("/aplicables", response_model=ObligacionesAplicablesResponse, operation_id="listar_obligaciones_aplicables")
async def listar_obligaciones_aplicables(
    tipo_entidad: str = Query("sociedad_valores", description="Tipo de entidad regulada"),
    reporting_reservado: bool = Query(True, description="Si aplica reporting reservado CNMV"),
    aml_cft_reforzado: bool = Query(True, description="Si la entidad esta sujeta a obligaciones AML/CFT operativas"),
    cross_border_ue: bool = Query(False, description="Si la entidad presta servicios cross-border UE"),
):
    profile = build_sociedad_valores_profile(
        reporting_reservado=reporting_reservado,
        aml_cft_reforzado=aml_cft_reforzado,
        cross_border_ue=cross_border_ue,
    )
    profile["tipo_entidad"] = tipo_entidad

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                       sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia,
                       plazo_dias, frecuencia_presentacion, ventana_presentacion,
                       trigger_presentacion, sancion_min, sancion_max, prescripcion_anos
                FROM obligacion_regulatoria
                ORDER BY fuente ASC, codigo ASC
                """
            )
        ).mappings()

        obligaciones = [dict(row) for row in rows]
        aplicables = [enrich_obligacion_metadata(item) for item in obligaciones if obligation_applies(profile, item)]
        return {"perfil": profile, "obligaciones": aplicables}


@router.get("/operativas", response_model=list[dict], operation_id="listar_obligaciones_operativas")
async def listar_obligaciones_operativas(
    ambito: str | None = Query(None, description="Filtrar por ámbito"),
    frecuencia: str | None = Query(None, description="Filtrar por frecuencia: mensual, trimestral, anual, eventual"),
    con_sancion: bool = Query(True, description="Solo obligaciones con sanciones definidas"),
    limite: int = Query(50, ge=1, le=200, description="Número máximo de resultados"),
):
    """Listar obligaciones con datos operativos completos (plazos, sanciones, triggers).
    
    Diseñado para que el LLM consumidor del MCP pueda responder preguntas de
    cumplimiento con datos estructurados en lugar de texto libre.
    """
    filters = ["1=1"]
    params: dict[str, str] = {}

    if ambito:
        filters.append("o.ambito = :ambito")
        params["ambito"] = ambito

    if frecuencia:
        filters.append("o.frecuencia_presentacion = :frecuencia")
        params["frecuencia"] = frecuencia

    if con_sancion:
        filters.append("o.sancion_max IS NOT NULL")

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                       sujeto_obligado, periodicidad, reporte_modelo, ambito, estado_vigencia,
                       plazo_dias, frecuencia_presentacion, ventana_presentacion,
                       trigger_presentacion, canal_presentacion, obligados_resumen,
                       sancion_min, sancion_max, recargo_voluntario,
                       recargo_involuntario, interes_demora, prescripcion_anos,
                       deposito_previo, origen_metadato, estado_metadato
                FROM obligacion_regulatoria o
                WHERE {where_clause}
                ORDER BY
                    CASE WHEN estado_metadato = 'curado' THEN 0 ELSE 1 END,
                    fuente ASC, codigo ASC
                LIMIT :limite
                """.format(where_clause=" AND ".join(filters))
            ),
            {**params, "limite": limite},
        ).mappings()

        return [enrich_obligacion_metadata(dict(row)) for row in rows]


@router.get("/deadlines", response_model=list[dict], operation_id="listar_deadlines")
async def listar_deadlines(
    dias_proximo: int = Query(30, ge=1, le=365, description="Mostrar obligaciones en los próximos N días"),
    frecuencia: str | None = Query(None, description="Filtrar por frecuencia"),
):
    """Listar obligaciones próximas a vencer o presentar.
    
    Devuelve obligaciones ordenadas por frecuencia y ventana de presentación,
    útil para que el LLM responda "qué tengo que presentar pronto".
    """
    filters = ["1=1"]
    params: dict[str, str | int] = {"dias": dias_proximo}

    if frecuencia:
        filters.append("frecuencia_presentacion = :frecuencia")

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, nombre, fuente, organismo_emisor,
                       frecuencia_presentacion, ventana_presentacion,
                       plazo_dias, trigger_presentacion, estado_vigencia,
                       estado_metadato
                FROM obligacion_regulatoria
                WHERE {where_clause}
                  AND frecuencia_presentacion IS NOT NULL
                  AND frecuencia_presentacion != 'eventual'
                ORDER BY
                    CASE frecuencia_presentacion
                        WHEN 'mensual' THEN 1
                        WHEN 'trimestral' THEN 2
                        WHEN 'anual' THEN 3
                        ELSE 4
                    END,
                    codigo ASC
                LIMIT :dias
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        return [enrich_obligacion_metadata(dict(row)) for row in rows]


@router.get("/{codigo}", response_model=ObligacionDetail, operation_id="get_obligacion")
async def get_obligacion(codigo: str):
    with db_session() as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT id, codigo, nombre, fuente, organismo_emisor, tipo_obligacion,
                           sujeto_obligado, periodicidad, reporte_modelo, ambito,
                           estado_vigencia, documento_origen_tipo, documento_origen_ref,
                           seccion_origen, anexo_origen, nota,
                           plazo_dias, frecuencia_presentacion, ventana_presentacion,
                           trigger_presentacion, canal_presentacion, obligados_resumen,
                           sancion_min, sancion_max, recargo_voluntario,
                           recargo_involuntario, interes_demora, prescripcion_anos,
                           deposito_previo, fuentes_operativas, ultima_actualizacion,
                           origen_metadato, estado_metadato
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

        result = dict(row)
        if result.get("fuentes_operativas") and isinstance(result["fuentes_operativas"], str):
            import json

            result["fuentes_operativas"] = json.loads(result["fuentes_operativas"])

        result["documentos"] = [dict(item) for item in documentos]
        return enrich_obligacion_metadata(result)
