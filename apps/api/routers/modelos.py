from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    AEATModeloDetail,
    AEATModeloListResponse,
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


def _date_to_str(value):
    return str(value) if value is not None else None


def _list_aeat_modelos(db, codigo=None, campana=None, impuesto=None, tipo_recurso=None, activo=None):
    rows = db.execute(
        text(
            """
            WITH active_campaign AS (
                SELECT mc.*
                FROM modelo_campana mc
                JOIN (
                    SELECT modelo_id, MAX(campana) AS campana
                    FROM modelo_campana
                    WHERE (:campana IS NULL OR campana = :campana)
                    GROUP BY modelo_id
                ) latest ON latest.modelo_id = mc.modelo_id AND latest.campana = mc.campana
            )
            SELECT
                m.codigo,
                m.nombre,
                COALESCE(m.activo, true) AS activo,
                m.impuesto,
                ac.campana,
                ac.estado_publicacion,
                COUNT(mr.id) AS recursos_activos
            FROM aeat_modelo m
            LEFT JOIN active_campaign ac ON ac.modelo_id = m.id
            LEFT JOIN modelo_recurso mr
                ON mr.campana_id = ac.id
               AND mr.activa = true
               AND (:tipo_recurso IS NULL OR mr.tipo_recurso = :tipo_recurso)
            WHERE (:codigo IS NULL OR m.codigo = :codigo)
              AND (:impuesto IS NULL OR m.impuesto = :impuesto)
              AND (:activo IS NULL OR COALESCE(m.activo, true) = :activo)
            GROUP BY m.id, m.codigo, m.nombre, m.activo, m.impuesto, ac.campana, ac.estado_publicacion
            ORDER BY m.codigo
            """
        ),
        {
            "codigo": codigo,
            "campana": campana,
            "impuesto": impuesto,
            "tipo_recurso": tipo_recurso,
            "activo": activo,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def _get_aeat_model_row(db, codigo: str):
    row = db.execute(
        text(
            "SELECT id, codigo, nombre, COALESCE(activo, true) AS activo FROM aeat_modelo WHERE codigo = :codigo"
        ),
        {"codigo": codigo},
    ).mappings().first()
    return dict(row) if row else None


def _get_aeat_campanas(db, modelo_id: int, campana: str | None = None, include_history: bool = False):
    if include_history:
        query = text(
            """
            SELECT id, campana, activo, estado_publicacion, fecha_publicacion_portal, fecha_actualizacion_portal
            FROM modelo_campana
            WHERE modelo_id = :modelo_id
              AND (:campana IS NULL OR campana = :campana)
            ORDER BY campana DESC
            """
        )
    else:
        query = text(
            """
            SELECT id, campana, activo, estado_publicacion, fecha_publicacion_portal, fecha_actualizacion_portal
            FROM modelo_campana
            WHERE modelo_id = :modelo_id
              AND (:campana IS NULL OR campana = :campana)
            ORDER BY activo DESC, campana DESC
            LIMIT 1
            """
        )
    rows = db.execute(query, {"modelo_id": modelo_id, "campana": campana}).mappings().all()
    return [dict(row) for row in rows]


def _get_aeat_recursos(db, campana_id: int, include_history: bool = False):
    rows = db.execute(
        text(
            f"""
            SELECT tipo_recurso, formato, url_recurso, sha256_contenido,
                   fecha_publicacion_recurso, first_seen_at, last_seen_at, activa, id
            FROM modelo_recurso
            WHERE campana_id = :campana_id
            {'ORDER BY tipo_recurso, activa DESC, id DESC' if include_history else 'AND activa = true ORDER BY tipo_recurso'}
            """
        ),
        {"campana_id": campana_id},
    ).mappings().all()
    return [
        {
            **dict(row),
            "fecha_publicacion_recurso": _date_to_str(row["fecha_publicacion_recurso"]),
            "first_seen_at": _date_to_str(row["first_seen_at"]),
            "last_seen_at": _date_to_str(row["last_seen_at"]),
            "activa": bool(row["activa"]),
        }
        for row in rows
    ]


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
    "/aeat",
    operation_id="list_modelos_aeat",
    response_model=AEATModeloListResponse,
    summary="Lista modelos AEAT con campana y recursos activos",
)
async def list_modelos_aeat(
    codigo: str | None = Query(None, description="Filtrar por codigo de modelo"),
    campana: str | None = Query(None, description="Filtrar por campana"),
    impuesto: str | None = Query(None, description="Filtrar por impuesto"),
    tipo_recurso: str | None = Query(None, description="Filtrar por tipo de recurso"),
    activo: bool | None = Query(None, description="Filtrar por estado activo"),
):
    with db_session() as db:
        rows = _list_aeat_modelos(db, codigo, campana, impuesto, tipo_recurso, activo)
        return {"total": len(rows), "items": rows}


@router.get(
    "/aeat/{codigo}",
    operation_id="get_modelo_aeat",
    response_model=AEATModeloDetail,
    summary="Detalle AEAT con recursos activos e historial opcional",
)
async def get_modelo_aeat(
    codigo: str,
    campana: str | None = Query(None, description="Campana especifica"),
    include_history: bool = Query(False, description="Incluir historial de campanas y versiones"),
):
    with db_session() as db:
        model_row = _get_aeat_model_row(db, codigo)
        if not model_row:
            raise HTTPException(status_code=404, detail={"error": f"Modelo AEAT {codigo} no encontrado"})

        campanas = _get_aeat_campanas(db, model_row["id"], campana=campana, include_history=include_history)
        if not campanas:
            return {
                "codigo": model_row["codigo"],
                "nombre": model_row["nombre"],
                "activo": bool(model_row["activo"]),
                "campana_actual": None,
                "historial": [] if include_history else None,
            }

        campana_actual = campanas[0]
        campana_actual_payload = {
            "campana": campana_actual["campana"],
            "activo": bool(campana_actual["activo"]),
            "estado_publicacion": campana_actual["estado_publicacion"],
            "fecha_publicacion_portal": _date_to_str(campana_actual["fecha_publicacion_portal"]),
            "fecha_actualizacion_portal": _date_to_str(campana_actual["fecha_actualizacion_portal"]),
            "recursos": _get_aeat_recursos(db, campana_actual["id"], include_history=False),
        }

        historial_payload = None
        if include_history:
            historial_payload = []
            for camp_row in campanas:
                historial_payload.append(
                    {
                        "campana": camp_row["campana"],
                        "activo": bool(camp_row["activo"]),
                        "estado_publicacion": camp_row["estado_publicacion"],
                        "fecha_publicacion_portal": _date_to_str(camp_row["fecha_publicacion_portal"]),
                        "fecha_actualizacion_portal": _date_to_str(camp_row["fecha_actualizacion_portal"]),
                        "recursos": _get_aeat_recursos(db, camp_row["id"], include_history=True),
                    }
                )

        return {
            "codigo": model_row["codigo"],
            "nombre": model_row["nombre"],
            "activo": bool(model_row["activo"]),
            "campana_actual": campana_actual_payload,
            "historial": historial_payload,
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
