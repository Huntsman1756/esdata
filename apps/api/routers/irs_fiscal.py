"""IRS & international fiscal compliance (Fase 24).

Endpoints para consultar normas IRS, convenios DTA, reglas de retención,
formularios W-8, referencias TIN y registros GIIN/FFI.
"""

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from schemas import (
    GiinRegistryDetail,
    GiinRegistryListResponse,
    IrsDttaConventionDetail,
    IrsDttaConventionListResponse,
    IrsFiscalCheckRequest,
    IrsFiscalCheckResponse,
    IrsFiscalNormaDetail,
    IrsFiscalNormaListResponse,
    IrsTinReferenceDetail,
    IrsTinReferenceListResponse,
    IrsW8FormDetail,
    IrsW8FormListResponse,
    IrsWithholdingRuleDetail,
    IrsWithholdingRuleListResponse,
)
from sqlalchemy import text

router = APIRouter(prefix="/v1/irs-fiscal", tags=["irs-fiscal"])


# ---------------------------------------------------------------------------
# IRS Fiscal Norma
# ---------------------------------------------------------------------------


@router.get(
    "/normas",
    response_model=IrsFiscalNormaListResponse,
    operation_id="listar_normas_irs",
)
async def listar_normas_irs(
    tipo: str | None = Query(None, description="Filtrar por tipo: publicacion, forma, instruccion, ley, convenio"),
    estado: str = Query("activo", description="Estado: activo, inactivo, obsoleto"),
):
    filters = ["1=1"]
    params: dict = {}

    if tipo:
        filters.append("tipo = :tipo")
        params["tipo"] = tipo

    filters.append("estado = :estado")
    params["estado"] = estado

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, titulo, tipo, anio_vigencia, estado
                FROM irs_fiscal_norma
                WHERE {where_clause}
                ORDER BY anio_vigencia DESC NULLS LAST, codigo ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        normas = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM irs_fiscal_norma
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {"normas": normas, "total": total}


@router.get(
    "/normas/{codigo}",
    response_model=IrsFiscalNormaDetail,
    operation_id="detalle_norma_irs",
)
async def detalle_norma_irs(codigo: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, titulo, tipo, anio_vigencia, estado,
                       texto, url_fuente, creado_en, actualizado_en
                FROM irs_fiscal_norma
                WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail=f"Norma fiscal no encontrada: {codigo}")

        return dict(row)


# ---------------------------------------------------------------------------
# IRS DTA Convention
# ---------------------------------------------------------------------------


@router.get(
    "/convenios",
    response_model=IrsDttaConventionListResponse,
    operation_id="listar_convenios_dta",
)
async def listar_convenios_dta(
    pais: str | None = Query(None, description="Filtrar por pais (origen o destino)"),
    estado: str = Query("vigente", description="Estado: vigente, expirado, modificado"),
):
    filters = ["1=1"]
    params: dict = {}

    if pais:
        filters.append("(pais_origen = :pais OR pais_destino = :pais)")
        params["pais"] = pais

    filters.append("estado = :estado")
    params["estado"] = estado

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, pais_origen, pais_destino, titulo,
                       fecha_firma, fecha_vigencia, tipo_acuerdo, estado
                FROM irs_dta_convention
                WHERE {where_clause}
                ORDER BY pais_origen ASC, pais_destino ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        convenios = [dict(row) for row in rows]

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

        return {"convenios": convenios, "total": total}


@router.get(
    "/convenios/{codigo}",
    response_model=IrsDttaConventionDetail,
    operation_id="detalle_convenio_dta",
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
            raise HTTPException(status_code=404, detail=f"Convenio DTA no encontrado: {codigo}")

        return dict(row)


# ---------------------------------------------------------------------------
# IRS Withholding Rule
# ---------------------------------------------------------------------------


@router.get(
    "/retenciones",
    response_model=IrsWithholdingRuleListResponse,
    operation_id="listar_reglas_retencion",
)
async def listar_reglas_retencion(
    tipo_renta: str | None = Query(None, description="Filtrar por tipo de renta: dividends, interest, royalties, capital_gains"),
    pais: str | None = Query(None, description="Filtrar por pais aplicable"),
    estado: str = Query("activo", description="Estado: activo, inactivo"),
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
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
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

        return {"reglas": reglas, "total": total}


@router.get(
    "/retenciones/{codigo}",
    response_model=IrsWithholdingRuleDetail,
    operation_id="detalle_regla_retencion",
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
            raise HTTPException(status_code=404, detail=f"Regla de retencion no encontrada: {codigo}")

        return dict(row)


# ---------------------------------------------------------------------------
# IRS W-8 Form
# ---------------------------------------------------------------------------


@router.get(
    "/w8-formularios",
    response_model=IrsW8FormListResponse,
    operation_id="listar_formularios_w8",
)
async def listar_formularios_w8(
    tipo_sujeto: str | None = Query(None, description="Filtrar por tipo: persona_fisica, persona_juridica, exento"),
    estado: str = Query("activo", description="Estado: activo, inactivo"),
):
    filters = ["1=1"]
    params: dict = {}

    if tipo_sujeto:
        filters.append("tipo_sujeto = :tipo_sujeto")
        params["tipo_sujeto"] = tipo_sujeto

    filters.append("estado = :estado")
    params["estado"] = estado

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo, nombre, tipo_sujeto, validez_anios, estado
                FROM irs_w8_form
                WHERE {where_clause}
                ORDER BY codigo ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        formularios = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM irs_w8_form
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {"formularios": formularios, "total": total}


@router.get(
    "/w8-formularios/{codigo}",
    response_model=IrsW8FormDetail,
    operation_id="detalle_formulario_w8",
)
async def detalle_formulario_w8(codigo: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo, nombre, descripcion, tipo_sujeto, finalidad,
                       partes, validez_anios, obligacion_asociada, texto_detalle,
                       estado, creado_en, actualizado_en
                FROM irs_w8_form
                WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail=f"Formulario W-8 no encontrado: {codigo}")

        return dict(row)


# ---------------------------------------------------------------------------
# IRS TIN Reference
# ---------------------------------------------------------------------------


@router.get(
    "/tin-referencias",
    response_model=IrsTinReferenceListResponse,
    operation_id="listar_referencias_tin",
)
async def listar_referencias_tin(
    pais: str | None = Query(None, description="Filtrar por codigo de pais (ISO 3166-1 alpha-2)"),
    ocde: bool | None = Query(None, description="Filtrar por pais OCDE"),
    eu_vat: bool | None = Query(None, description="Filtrar por pais UE VAT"),
):
    filters = ["1=1"]
    params: dict = {}

    if pais:
        filters.append("codigo_pais = :pais")
        params["pais"] = pais

    if ocde is not None:
        filters.append("es_ocde = :ocde")
        params["ocde"] = ocde

    if eu_vat is not None:
        filters.append("es_eu_vat = :eu_vat")
        params["eu_vat"] = eu_vat

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, codigo_pais, pais_nombre, formato_tin, ejemplo_tin,
                       es_ocde, es_eu_vat
                FROM irs_tin_reference
                WHERE {where_clause}
                ORDER BY codigo_pais ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        referencias = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM irs_tin_reference
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {"referencias": referencias, "total": total}


@router.get(
    "/tin-referencias/{codigo_pais}",
    response_model=IrsTinReferenceDetail,
    operation_id="detalle_referencia_tin",
)
async def detalle_referencia_tin(codigo_pais: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, codigo_pais, pais_nombre, formato_tin, ejemplo_tin,
                       emisor_espana, emisor_pais, es_ocde, es_eu_vat, creado_en
                FROM irs_tin_reference
                WHERE codigo_pais = :codigo_pais
                """
            ),
            {"codigo_pais": codigo_pais},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail=f"Referencia TIN no encontrada: {codigo_pais}")

        return dict(row)


# ---------------------------------------------------------------------------
# GIIN Registry
# ---------------------------------------------------------------------------


@router.get(
    "/giin",
    response_model=GiinRegistryListResponse,
    operation_id="listar_registros_giin",
)
async def listar_registros_giin(
    estado: str | None = Query(None, description="Filtrar por estado FATCA: activo, inactivo, suspendido"),
    pais: str | None = Query(None, description="Filtrar por pais de la entidad"),
    tipo: str | None = Query(None, description="Filtrar por tipo: FFI, NFFE, Exempt Beneficial Owner"),
):
    filters = ["1=1"]
    params: dict = {}

    if estado:
        filters.append("estado_fatca = :estado")
        params["estado"] = estado

    if pais:
        filters.append("entidad_pais = :pais")
        params["pais"] = pais

    if tipo:
        filters.append("tipo_entidad = :tipo")
        params["tipo"] = tipo

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT id, giin, entidad_nombre, entidad_pais, tipo_entidad,
                       estado_fatca, fecha_expiracion
                FROM giin_registry
                WHERE {where_clause}
                ORDER BY giin ASC
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).mappings()

        registros = [dict(row) for row in rows]

        total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM giin_registry
                WHERE {where_clause}
                """.format(where_clause=" AND ".join(filters))
            ),
            params,
        ).scalar()

        return {"registros": registros, "total": total}


@router.get(
    "/giin/{giin}",
    response_model=GiinRegistryDetail,
    operation_id="detalle_registro_giin",
)
async def detalle_registro_giin(giin: str):
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT id, giin, entidad_nombre, entidad_pais, tipo_entidad,
                       estado_fatca, fecha_registro, fecha_expiracion,
                       es_exempt_beneficial_owner, es_sponsored_ffo, nota,
                       creado_en, actualizado_en
                FROM giin_registry
                WHERE giin = :giin
                """
            ),
            {"giin": giin},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail=f"Registro GIIN no encontrado: {giin}")

        return dict(row)


# ---------------------------------------------------------------------------
# IRS Fiscal Check — calculo de retencion
# ---------------------------------------------------------------------------


@router.post(
    "/check",
    response_model=IrsFiscalCheckResponse,
    operation_id="verificar_cumplimiento_irs",
)
async def verificar_cumplimiento_irs(request: IrsFiscalCheckRequest):
    """Calcula la retencion IRS aplicable segun pais de residencia y tipo de renta."""
    with db_session() as db:
        # Buscar regla de retencion por tipo de renta
        rule_row = db.execute(
            text(
                """
                SELECT id, codigo, tipo_renta, tipo_renta_espanol,
                       tipo_retencion_default, tipo_retencion_dta, pais_aplicable,
                       descripcion, norma_referencia, articulo_referencia, estado
                FROM irs_withholding_rule
                WHERE tipo_renta = :tipo_renta
                ORDER BY pais_aplicable ASC NULLS LAST
                LIMIT 1
                """
            ),
            {"tipo_renta": request.tipo_renta},
        ).mappings().first()

        if not rule_row:
            return IrsFiscalCheckResponse(
                pais_residencia=request.pais_residencia,
                tipo_renta=request.tipo_renta,
                tipo_retencion_aplicable=30.0,
                tiene_convenio_dta=False,
                codigo_convenio=None,
                requiere_w8=True,
                formulario_recomendado="W-8BEN-E",
                notas="No se encontro regla de retencion especifica. Se aplica tipo default IRS (30%).",
            )

        tipo_retencion = rule_row["tipo_retencion_default"]
        tiene_convenio = False
        codigo_convenio = None

        # Buscar DTA aplicable
        if request.pais_residencia:
            dta_row = db.execute(
                text(
                    """
                    SELECT dta.codigo, wr.tipo_retencion_dta
                    FROM irs_dta_convention dta
                    LEFT JOIN irs_withholding_rule wr
                        ON wr.tipo_renta = :tipo_renta
                    WHERE ((dta.pais_origen = :pais_residencia AND dta.pais_destino = :pais_us)
                       OR (dta.pais_origen = :pais_us AND dta.pais_destino = :pais_residencia))
                       AND dta.estado = 'vigente'
                    LIMIT 1
                    """
                ),
                {
                    "pais_residencia": request.pais_residencia,
                    "pais_us": "US",
                    "tipo_renta": request.tipo_renta,
                },
            ).mappings().first()

            if dta_row and dta_row["tipo_retencion_dta"] is not None:
                tipo_retencion = dta_row["tipo_retencion_dta"]
                tiene_convenio = True
                codigo_convenio = dta_row["codigo"]

        # Determinar formulario W-8 recomendado
        requiere_w8 = True
        formulario_recomendado = "W-8BEN-E"
        if request.tiene_formulario_w8:
            requiere_w8 = False

        notas = None
        if tiene_convenio:
            notas = f"Convenio DTA aplicable: {codigo_convenio}. Tipo reducido aplicado."
        elif rule_row.get("descripcion"):
            notas = rule_row["descripcion"]

        return IrsFiscalCheckResponse(
            pais_residencia=request.pais_residencia,
            tipo_renta=request.tipo_renta,
            tipo_retencion_aplicable=float(tipo_retencion),
            tiene_convenio_dta=tiene_convenio,
            codigo_convenio=codigo_convenio,
            requiere_w8=requiere_w8,
            formulario_recomendado=formulario_recomendado,
            notas=notas,
        )
