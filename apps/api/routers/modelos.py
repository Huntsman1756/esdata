from fastapi import APIRouter, HTTPException, Query

from db import db_session
from schemas import (
    ModeloCampanaOperativaResponse,
    ModeloArtefactosResponse,
    ModeloDetail as ModeloDetailSchema,
    ModeloFuentesOficialesResponse,
    ModeloResumenOperativoResponse,
    ModelosCampanasOperativasResponse,
    ModelosListResponse,
)
from services.modelos import (
    get_active_campaign,
    get_modelo_campana_operativa,
    get_model_row,
    get_modelo_resumen_operativo,
    list_campaign_casillas,
    list_campaign_claves,
    list_campaign_instructions,
    list_modelo_artefactos,
    list_modelo_articulos,
    list_modelo_campanas,
    list_modelos_campanas_operativas,
    list_modelo_fuentes_oficiales,
    list_modelo_normativa,
    list_modelos_summary,
    list_related_doctrina,
)

router = APIRouter(prefix="/v1/modelos", tags=["modelos"])


@router.get(
    "/campanas-operativas",
    operation_id="list_modelos_campanas_operativas",
    response_model=ModelosCampanasOperativasResponse,
    summary="Vista operativa agregada de varios modelos",
    openapi_extra={"x-beta": True},
)
async def get_campanas_operativas_modelos(
    codigos: str = Query(..., description="Codigos separados por comas, ej: 124,216,296"),
    campana: str = Query(None, description="Campana especifica"),
):
    lista_codigos = [item.strip() for item in codigos.split(",")]
    with db_session() as db:
        return {
            "modelos": list_modelos_campanas_operativas(db, lista_codigos, campana)
        }


@router.get("", operation_id="list_modelos", response_model=ModelosListResponse)
async def list_modelos():
    """Lista todos los modelos AEAT disponibles."""
    with db_session() as db:
        rows = list_modelos_summary(db)

        return {
            "modelos": [
                {
                    "codigo": row["codigo"],
                    "nombre": row["nombre"],
                    "periodo": row["periodo"],
                    "impuesto": row["impuesto"],
                    "articulos_count": row["articulos_count"],
                    "casillas_count": row["casillas_count"],
                }
                for row in rows
            ]
        }


@router.get(
    "/{codigo}",
    operation_id="get_modelo",
    response_model=ModeloDetailSchema,
    summary="Detalle de un modelo AEAT",
)
async def get_modelo(
    codigo: str,
    campana: str = Query(
        None,
        description="Campana especifica (ej: 2025). Si no se indica, usa la activa.",
    ),
):
    """
    Detalle de un modelo con artículos, casillas, claves, instrucciones,
    normativa y doctrina relacionada.

    Query params:
    - campana: filtra por campaña específica (ej: '2025'). Si no se indica,
      usa la campaña activa más reciente.
    """
    with db_session() as db:
        model_row = get_model_row(db, codigo)

        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        camp_row = get_active_campaign(db, codigo, campana)
        campana_id = camp_row["id"] if camp_row else None
        campana_activa = camp_row["campana"] if camp_row else None

        art_rows = list_modelo_articulos(db, codigo)

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

        casillas = []
        if campana_id:
            cas_rows = list_campaign_casillas(db, campana_id)
            casillas = [dict(r) for r in cas_rows]

        claves = []
        if campana_id:
            clav_rows = list_campaign_claves(db, campana_id)
            claves = [dict(r) for r in clav_rows]

        instrucciones = []
        if campana_id:
            instr_rows = list_campaign_instructions(db, campana_id)
            instrucciones = [dict(r) for r in instr_rows]

        norm_rows = list_modelo_normativa(db, codigo)
        normativa = [
            {
                **dict(r),
                "fecha": str(r["fecha"]) if r["fecha"] else None,
            }
            for r in norm_rows
        ]

        camp_rows = list_modelo_campanas(db, codigo)
        campanas = [dict(r) for r in camp_rows]
        doctrina_relacionada = list_related_doctrina(db, articulos)

        return {
            "codigo": model_row["codigo"],
            "nombre": model_row["nombre"],
            "periodo": model_row["periodo"],
            "impuesto": model_row["impuesto"],
            "url_info": model_row["url_info"],
            "campana_activa": campana_activa,
            "campanas": campanas,
            "articulos": articulos,
            "casillas": casillas,
            "claves": claves,
            "instrucciones": instrucciones,
            "normativa": normativa,
            "doctrina_relacionada": doctrina_relacionada,
        }


@router.get("/{codigo}/articulos", operation_id="get_modelo_articulos")
async def get_modelo_articulos(codigo: str):
    """Solo artículos enlazados a un modelo (para filtros/paginación futura)."""
    with db_session() as db:
        model_row = get_model_row(db, codigo)

        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        rows = list_modelo_articulos(db, codigo)

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


@router.get(
    "/{codigo}/casillas",
    operation_id="get_modelo_casillas",
    response_model=None,
    summary="Casillas de un modelo",
)
async def get_modelo_casillas(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    """Lista todas las casillas de un modelo para una campaña."""
    with db_session() as db:
        camp_row = get_active_campaign(db, codigo, campana)

        if not camp_row:
            return {"codigo": codigo, "casillas": []}

        campana_id = camp_row["id"]
        rows = list_campaign_casillas(db, campana_id)

        return {
            "codigo": codigo,
            "casillas": [dict(r) for r in rows],
        }


@router.get(
    "/{codigo}/claves", operation_id="get_modelo_claves", summary="Claves de un modelo"
)
async def get_modelo_claves(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    """Lista todas las claves de un modelo para una campaña."""
    with db_session() as db:
        camp_row = get_active_campaign(db, codigo, campana)

        if not camp_row:
            return {"codigo": codigo, "claves": []}

        campana_id = camp_row["id"]
        rows = list_campaign_claves(db, campana_id)

        return {
            "codigo": codigo,
            "claves": [dict(r) for r in rows],
        }


@router.get(
    "/{codigo}/instrucciones",
    operation_id="get_modelo_instrucciones",
    summary="Instrucciones de un modelo",
)
async def get_modelo_instrucciones(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    """Lista las instrucciones de un modelo para una campaña."""
    with db_session() as db:
        camp_row = get_active_campaign(db, codigo, campana)

        if not camp_row:
            return {"codigo": codigo, "instrucciones": []}

        campana_id = camp_row["id"]
        rows = list_campaign_instructions(db, campana_id)

        return {
            "codigo": codigo,
            "instrucciones": [dict(r) for r in rows],
        }


@router.get("/{codigo}/normativa", operation_id="get_modelo_normativa")
async def get_modelo_normativa(codigo: str):
    """Lista la normativa (BOE) de un modelo."""
    with db_session() as db:
        rows = list_modelo_normativa(db, codigo)

        return {
            "codigo": codigo,
            "normativa": [dict(r) for r in rows],
        }


@router.get(
    "/{codigo}/artefactos",
    operation_id="get_modelo_artefactos",
    response_model=ModeloArtefactosResponse,
    summary="Artefactos técnicos disponibles para un modelo",
    openapi_extra={"x-beta": True},
)
async def get_modelo_artefactos(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    with db_session() as db:
        payload = list_modelo_artefactos(db, codigo, campana)
        if not payload:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )
        return payload


@router.get(
    "/{codigo}/resumen-operativo",
    operation_id="get_modelo_resumen_operativo",
    response_model=ModeloResumenOperativoResponse,
    summary="Resumen operativo para agentes sobre un modelo",
    openapi_extra={"x-beta": True},
)
async def get_resumen_operativo_modelo(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    with db_session() as db:
        payload = get_modelo_resumen_operativo(db, codigo, campana)
        if not payload:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )
        return payload


@router.get(
    "/{codigo}/campana-operativa",
    operation_id="get_modelo_campana_operativa",
    response_model=ModeloCampanaOperativaResponse,
    summary="Vista de campaña operativa para agentes",
    openapi_extra={"x-beta": True},
)
async def get_campana_operativa_modelo(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    with db_session() as db:
        payload = get_modelo_campana_operativa(db, codigo, campana)
        if not payload:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )
        return payload


@router.get(
    "/{codigo}/fuentes-oficiales",
    operation_id="get_modelo_fuentes_oficiales",
    response_model=ModeloFuentesOficialesResponse,
    summary="Fuentes oficiales recomendadas para trabajar un modelo",
    openapi_extra={"x-beta": True},
)
async def get_modelo_fuentes_oficiales(
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    with db_session() as db:
        payload = list_modelo_fuentes_oficiales(db, codigo, campana)
        if not payload:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )
        return payload
