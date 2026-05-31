"""DTA Conventions & Withholding Rules router (Fase 25.8).

Endpoints dedicados para convenios de doble tributacion y calculo de
retenciones aplicables cruzando reglas con convenios vigentes.
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    IrsDttaConventionDetail,
    IrsDttaConventionListResponse,
    IrsFiscalCheckRequest,
    IrsFiscalCheckResponse,
    IrsWithholdingRuleDetail,
    IrsWithholdingRuleListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/internacional/convenios", tags=["convenios-dta"])


# ---------------------------------------------------------------------------
# Withholding Rules — DEBE ir ANTES de /{codigo} para evitar conflicto
# ---------------------------------------------------------------------------


@router.get(
    "/retenciones",
    response_model=IrsWithholdingRuleListResponse,
    operation_id="listar_reglas_retencion_internacional",
    summary="Listar reglas de retencion",
    description="Lista reglas de retencion por tipo de renta y pais.",
)
async def listar_reglas_retencion(
    tipo_renta: str | None = Query(
        None,
        description="Tipo de renta: dividends, interest, royalties, capital_gains, other",
    ),
    pais: str | None = Query(None, description="Pais aplicable (codigo ISO)"),
    estado: str = Query("activo", description="Estado: activo, inactivo"),
    limit: int = Query(200, ge=1, le=500, description="Tamano de pagina aplicado"),
    offset: int = Query(0, ge=0, description="Offset de resultados"),
):
    filters = ["1=1"]
    params: dict = {}

    if tipo_renta:
        filters.append("tipo_renta = :tipo_renta")
        params["tipo_renta"] = tipo_renta

    if pais:
        filters.append("pais_aplicable = :pais")
        params["pais"] = pais

    filters.append("estado = :estado")
    params["estado"] = estado

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, tipo_renta, tipo_renta_espanol,
                       tipo_retencion_default, tipo_retencion_dta, pais_aplicable, estado
                FROM irs_withholding_rule
                WHERE {where_clause}
                ORDER BY tipo_renta ASC, pais_aplicable ASC NULLS LAST
                LIMIT :limit OFFSET :offset
                """.format(where_clause=" AND ".join(filters))
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()

        reglas = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM irs_withholding_rule
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        has_more = offset + len(reglas) < total
        return {
            "reglas": reglas,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + len(reglas) if has_more else None,
        }


@router.get(
    "/retenciones/{codigo}",
    response_model=IrsWithholdingRuleDetail,
    operation_id="detalle_regla_retencion_internacional",
    summary="Detalle regla de retencion",
    description="Detalle de una regla de retencion por codigo.",
)
async def detalle_regla_retencion(codigo: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, tipo_renta, tipo_renta_espanol,
                       tipo_retencion_default, tipo_retencion_dta, pais_aplicable,
                       descripcion, norma_referencia, articulo_referencia, estado,
                       creado_en, actualizado_en
                FROM irs_withholding_rule
                WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Regla de retencion no encontrada: {codigo}"
            )

        d = dict(row)
        for k in ("fecha_firma", "fecha_vigencia"):
            if d.get(k) is not None:
                d[k] = d[k].isoformat()
        return d


# ---------------------------------------------------------------------------
# DTA Conventions — /{codigo} va DESPUES de /retenciones
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=IrsDttaConventionListResponse,
    operation_id="listar_convenios_dta_internacional",
    summary="Listar convenios DTA",
    description="Lista convenios de doble tributacion con filtros por pais y estado.",
)
async def listar_convenios_dta(
    pais_a: str | None = Query(None, description="Pais origen (codigo ISO)"),
    pais_b: str | None = Query(None, description="Pais destino (codigo ISO)"),
    estado: str = Query("vigente", description="Estado: vigente, expirado, modificado"),
    tipo_acuerdo: str | None = Query(None, description="Tipo: bilateral, multilateral"),
    limit: int = Query(200, ge=1, le=500, description="Tamano de pagina aplicado"),
    offset: int = Query(0, ge=0, description="Offset de resultados"),
):
    filters = ["1=1"]
    params: dict = {}

    if pais_a:
        filters.append("pais_origen = :pais_a")
        params["pais_a"] = pais_a

    if pais_b:
        filters.append("pais_destino = :pais_b")
        params["pais_b"] = pais_b

    filters.append("estado = :estado")
    params["estado"] = estado

    if tipo_acuerdo:
        filters.append("tipo_acuerdo = :tipo_acuerdo")
        params["tipo_acuerdo"] = tipo_acuerdo

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, pais_origen, pais_destino, titulo,
                       fecha_firma, fecha_vigencia, tipo_acuerdo, estado
                FROM irs_dta_convention
                WHERE {where_clause}
                ORDER BY pais_origen ASC, pais_destino ASC
                LIMIT :limit OFFSET :offset
                """.format(where_clause=" AND ".join(filters))
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings()

        convenios = []
        for row in rows:
            d = dict(row)
            for k in ("fecha_firma", "fecha_vigencia"):
                value = d.get(k)
                if value is not None and hasattr(value, "isoformat"):
                    d[k] = value.isoformat()
            convenios.append(d)

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM irs_dta_convention
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        has_more = offset + len(convenios) < total
        return {
            "convenios": convenios,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + len(convenios) if has_more else None,
        }


@router.get(
    "/{codigo}",
    response_model=IrsDttaConventionDetail,
    operation_id="detalle_convenio_dta_internacional",
    summary="Detalle convenio DTA",
    description="Detalle disponible de un convenio de doble tributacion.",
)
async def detalle_convenio_dta(codigo: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, pais_origen, pais_destino, titulo,
                       fecha_firma, fecha_vigencia, tipo_acuerdo, boe_referencia,
                       articulos, texto_completo, estado, creado_en, actualizado_en
                FROM irs_dta_convention
                WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Convenio DTA no encontrado: {codigo}"
            )

        return dict(row)


# ---------------------------------------------------------------------------
# Withholding Check — cruza DTA + withholding rules
# ---------------------------------------------------------------------------


@router.post(
    "/retencion",
    response_model=IrsFiscalCheckResponse,
    operation_id="calcular_retencion",
    summary="Calcular retencion aplicable",
    description=(
        "Calcula el tipo de retencion aplicable cruzando reglas de retencion "
        "con convenios DTA vigentes. Si existe un convenio DTA vigente entre "
        "el pais de residencia y el tipo de renta, devuelve la tasa reducida."
    ),
)
async def calcular_retencion(req: IrsFiscalCheckRequest):
    with db_session() as db:
        # 1. Buscar regla de retencion por tipo de renta
        rule_row = db.execute(
            text(
                """
                SELECT id, codigo, tipo_renta, tipo_renta_espanol,
                       tipo_retencion_default, tipo_retencion_dta, pais_aplicable
                FROM irs_withholding_rule
                WHERE tipo_renta = :tipo_renta AND estado = 'activo'
                ORDER BY pais_aplicable ASC NULLS LAST
                LIMIT 1
                """
            ),
            {"tipo_renta": req.tipo_renta},
        ).mappings().first()

        tipo_retencion_default = 30.0
        tipo_retencion_reducida = None
        codigo_convenio = None
        condiciones = None

        if rule_row:
            tipo_retencion_default = float(rule_row["tipo_retencion_default"])
            tipo_retencion_reducida = rule_row["tipo_retencion_dta"]

        # 2. Si hay pais de residencia, buscar convenio DTA vigente
        tiene_convenio = False
        formulario_recomendado = None
        notas = None

        if req.pais_residencia:
            convenio_row = db.execute(
                text(
                    """
                    SELECT id, codigo, pais_origen, pais_destino, titulo,
                           fecha_vigencia
                    FROM irs_dta_convention
                    WHERE ((pais_origen = :pais AND pais_destino = :pais_fuente)
                       OR (pais_origen = :pais_fuente AND pais_destino = :pais))
                      AND estado = 'vigente'
                    ORDER BY codigo DESC, fecha_vigencia DESC
                    LIMIT 1
                    """
                ),
                {"pais": req.pais_residencia, "pais_fuente": "ES"},
            ).mappings().first()

            if convenio_row:
                tiene_convenio = True
                codigo_convenio = convenio_row["codigo"]

                # Si hay regla con DTA, aplicar tasa reducida
                if tipo_retencion_reducida is not None:
                    tipo_retencion_aplicable = float(tipo_retencion_reducida)
                    condiciones = (
                        f"Convenio {codigo_convenio} vigente — "
                        f"tasa reducida desde {tipo_retencion_default}% a "
                        f"{tipo_retencion_aplicable}%"
                    )
                else:
                    tipo_retencion_aplicable = tipo_retencion_default
                    condiciones = (
                        f"Convenio {codigo_convenio} vigente — "
                        f"sin tasa reducida especificada para {req.tipo_renta}"
                    )
            else:
                tipo_retencion_aplicable = tipo_retencion_default
                condiciones = "Sin convenio DTA vigente — tasa default"
        else:
            tipo_retencion_aplicable = tipo_retencion_default
            condiciones = "Sin pais de residencia — tasa default"

        # 3. Determinar formulario W-8 recomendado
        requiere_w8 = True
        if req.entidad_giin:
            giin_row = db.execute(
                text(
                    """
                    SELECT id, giin, tipo_entidad
                    FROM giin_registry
                    WHERE giin = :giin AND estado_fatca = 'activo'
                    LIMIT 1
                    """
                ),
                {"giin": req.entidad_giin},
            ).mappings().first()

            if giin_row:
                if giin_row["tipo_entidad"] == "NFFE":
                    formulario_recomendado = "W-8BEN-E"
                else:
                    formulario_recomendado = "W-8BEN-E"
            else:
                formulario_recomendado = "W-8BEN-E"
        else:
            formulario_recomendado = "W-8BEN"

        notas = condiciones
        safe_to_answer = False
        evidence_notice = (
            "EVIDENCIA LIMITADA: el calculo DTA es exploratorio. "
            "No hay contrato CDI completo con hash/captura, articulo por tipo de renta, "
            "protocolo y certificado de residencia; no usar como tasa definitiva."
        )

        return {
            "pais_residencia": req.pais_residencia,
            "tipo_renta": req.tipo_renta,
            "tipo_retencion_aplicable": tipo_retencion_aplicable,
            "tiene_convenio_dta": tiene_convenio,
            "codigo_convenio": codigo_convenio,
            "requiere_w8": requiere_w8,
            "formulario_recomendado": formulario_recomendado,
            "notas": notas,
            "verified": False,
            "completeness": "partial",
            "safe_to_answer": safe_to_answer,
            "evidence_notice": evidence_notice,
            "review_required": True,
        }
