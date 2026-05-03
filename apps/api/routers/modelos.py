from db import db_session
from fastapi import APIRouter, HTTPException, Query, Request
from schemas import (
    AEATModeloDetail,
    AEATModeloListResponse,
    ModeloArtefactosResponse,
    ModeloCampanaOperativaResponse,
    ModeloFuentesOficialesResponse,
    ModeloResumenOperativoResponse,
    ModelosCampanasOperativasResponse,
    ModelosListResponse,
)
from schemas import (
    ModeloDetail as ModeloDetailSchema,
)
from services.modelos import (
    get_active_campaign,
    get_model_row,
    get_modelo_campana_operativa,
    get_modelo_resumen_operativo,
    list_campaign_casillas,
    list_campaign_claves,
    list_campaign_instructions,
    list_modelo_artefactos,
    list_modelo_articulos,
    list_modelo_campanas,
    list_modelo_fuentes_oficiales,
    list_modelo_normativa,
    list_modelos_campanas_operativas,
    list_modelos_summary,
    list_related_doctrina,
)
from services.query_audit import get_query_audit_service
from sqlalchemy import text

router = APIRouter(prefix="/v1/modelos", tags=["modelos"])


def _date_to_str(value):
    return str(value) if value is not None else None


def _record_modelo_query_audit(
    request: Request,
    *,
    path: str,
    query_text: str,
    tool_name: str,
    retrieved_chunks: list[dict],
    response_summary: str,
    confidence: dict,
    completeness: str,
    verified: bool,
):
    get_query_audit_service().record_query(
        request_id=request.headers.get("x-request-id")
        or request.headers.get("X-Request-ID")
        or "unknown",
        user_id=request.headers.get("x-user-id") or request.headers.get("X-User-ID"),
        path=path,
        query_text=query_text,
        retrieved_chunks=retrieved_chunks,
        response_summary=response_summary,
        tool_name=tool_name,
        confidence=confidence,
        completeness=completeness,
        verified=verified,
    )


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
                    WHERE (CAST(:campana AS TEXT) IS NULL OR campana = :campana)
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
               AND (CAST(:tipo_recurso AS TEXT) IS NULL OR mr.tipo_recurso = :tipo_recurso)
            WHERE (CAST(:codigo AS TEXT) IS NULL OR m.codigo = :codigo)
              AND (CAST(:impuesto AS TEXT) IS NULL OR m.impuesto = :impuesto)
              AND (CAST(:activo AS BOOLEAN) IS NULL OR COALESCE(m.activo, true) = :activo)
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
    where_clause = "WHERE modelo_id = :modelo_id"
    params: dict[str, object] = {"modelo_id": modelo_id}
    if campana:
        where_clause += " AND campana = :campana"
        params["campana"] = campana

    if include_history:
        query = text(
            f"""
            SELECT id, campana, activo, estado_publicacion, fecha_publicacion_portal, fecha_actualizacion_portal
            FROM modelo_campana
            {where_clause}
            ORDER BY campana DESC
            """
        )
    else:
        query = text(
            f"""
            SELECT id, campana, activo, estado_publicacion, fecha_publicacion_portal, fecha_actualizacion_portal
            FROM modelo_campana
            {where_clause}
            ORDER BY activo DESC, campana DESC
            LIMIT 1
            """
        )
    rows = db.execute(query, params).mappings().all()
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
    request: Request,
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
        verified = bool(instrucciones and casillas)

        payload = {
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
            "completeness": "completa" if verified else "parcial",
            "verified": verified,
        }
        _record_modelo_query_audit(
            request,
            path=f"/v1/modelos/{codigo}",
            query_text=codigo,
            tool_name="get_modelo",
            retrieved_chunks=[
                {
                    "title": payload["nombre"],
                    "source_url": payload.get("url_info"),
                },
                *[
                    {
                        "norma": item["norma"],
                        "numero": item["numero"],
                        "source_url": item.get("url_fuente"),
                        "title": item.get("titulo"),
                    }
                    for item in articulos
                ],
                *[
                    {
                        "referencia": item.get("boe_id"),
                        "source_url": item.get("url_boe"),
                        "title": item.get("titulo"),
                    }
                    for item in normativa
                ],
            ],
            response_summary=(
                f"campanas={len(campanas)};articulos={len(articulos)};casillas={len(casillas)};"
                f"instrucciones={len(instrucciones)}"
            ),
            confidence={"score": 0.9 if verified else 0.5, "label": "alta" if verified else "media"},
            completeness=payload["completeness"],
            verified=payload["verified"],
        )
        return payload


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
    request: Request,
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    """Lista todas las casillas de un modelo para una campaña."""
    with db_session() as db:
        model_row = get_model_row(db, codigo)
        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        camp_row = get_active_campaign(db, codigo, campana)

        if not camp_row:
            payload = {"codigo": codigo, "casillas": []}
            _record_modelo_query_audit(
                request,
                path=f"/v1/modelos/{codigo}/casillas",
                query_text=codigo,
                tool_name="get_modelo_casillas",
                retrieved_chunks=[],
                response_summary="casillas=0",
                confidence={"score": 0.0, "label": "baja"},
                completeness="parcial",
                verified=False,
            )
            return payload

        campana_id = camp_row["id"]
        rows = list_campaign_casillas(db, campana_id)

        payload = {
            "codigo": codigo,
            "casillas": [dict(r) for r in rows],
        }
        _record_modelo_query_audit(
            request,
            path=f"/v1/modelos/{codigo}/casillas",
            query_text=codigo,
            tool_name="get_modelo_casillas",
            retrieved_chunks=[
                {
                    "title": item["etiqueta"],
                    "numero": item["codigo"],
                }
                for item in payload["casillas"]
            ],
            response_summary=f"casillas={len(payload['casillas'])}",
            confidence={"score": 0.9 if payload["casillas"] else 0.0, "label": "alta" if payload["casillas"] else "baja"},
            completeness="completa" if payload["casillas"] else "parcial",
            verified=bool(payload["casillas"]),
        )
        return payload


@router.get(
    "/{codigo}/claves", operation_id="get_modelo_claves", summary="Claves de un modelo"
)
async def get_modelo_claves(
    request: Request,
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    """Lista todas las claves de un modelo para una campaña."""
    with db_session() as db:
        model_row = get_model_row(db, codigo)
        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        camp_row = get_active_campaign(db, codigo, campana)

        if not camp_row:
            payload = {"codigo": codigo, "claves": []}
            _record_modelo_query_audit(
                request,
                path=f"/v1/modelos/{codigo}/claves",
                query_text=codigo,
                tool_name="get_modelo_claves",
                retrieved_chunks=[],
                response_summary="claves=0",
                confidence={"score": 0.0, "label": "baja"},
                completeness="parcial",
                verified=False,
            )
            return payload

        campana_id = camp_row["id"]
        rows = list_campaign_claves(db, campana_id)

        payload = {
            "codigo": codigo,
            "claves": [dict(r) for r in rows],
        }
        _record_modelo_query_audit(
            request,
            path=f"/v1/modelos/{codigo}/claves",
            query_text=codigo,
            tool_name="get_modelo_claves",
            retrieved_chunks=[
                {
                    "title": item["etiqueta"],
                    "numero": item["codigo"],
                }
                for item in payload["claves"]
            ],
            response_summary=f"claves={len(payload['claves'])}",
            confidence={"score": 0.9 if payload["claves"] else 0.0, "label": "alta" if payload["claves"] else "baja"},
            completeness="completa" if payload["claves"] else "parcial",
            verified=bool(payload["claves"]),
        )
        return payload


@router.get(
    "/{codigo}/instrucciones",
    operation_id="get_modelo_instrucciones",
    summary="Instrucciones de un modelo",
)
async def get_modelo_instrucciones(
    request: Request,
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    """Lista las instrucciones de un modelo para una campaña."""
    with db_session() as db:
        model_row = get_model_row(db, codigo)
        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        camp_row = get_active_campaign(db, codigo, campana)

        if not camp_row:
            payload = {"codigo": codigo, "instrucciones": []}
            _record_modelo_query_audit(
                request,
                path=f"/v1/modelos/{codigo}/instrucciones",
                query_text=codigo,
                tool_name="get_modelo_instrucciones",
                retrieved_chunks=[],
                response_summary="instrucciones=0",
                confidence={"score": 0.0, "label": "baja"},
                completeness="parcial",
                verified=False,
            )
            return payload

        campana_id = camp_row["id"]
        rows = list_campaign_instructions(db, campana_id)

        payload = {
            "codigo": codigo,
            "instrucciones": [dict(r) for r in rows],
        }
        _record_modelo_query_audit(
            request,
            path=f"/v1/modelos/{codigo}/instrucciones",
            query_text=codigo,
            tool_name="get_modelo_instrucciones",
            retrieved_chunks=[
                {
                    "title": item["titulo"],
                    "content_preview": item["contenido"][:220],
                }
                for item in payload["instrucciones"]
            ],
            response_summary=f"instrucciones={len(payload['instrucciones'])}",
            confidence={"score": 0.9 if payload["instrucciones"] else 0.0, "label": "alta" if payload["instrucciones"] else "baja"},
            completeness="completa" if payload["instrucciones"] else "parcial",
            verified=bool(payload["instrucciones"]),
        )
        return payload


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
    request: Request,
    codigo: str, campana: str = Query(None, description="Campana especifica")
):
    with db_session() as db:
        payload = list_modelo_fuentes_oficiales(db, codigo, campana)
        if not payload:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )
        _record_modelo_query_audit(
            request,
            path=f"/v1/modelos/{codigo}/fuentes-oficiales",
            query_text=codigo,
            tool_name="get_modelo_fuentes_oficiales",
            retrieved_chunks=[
                {
                    "title": item["titulo"],
                    "source_url": item["url"],
                    "referencia": item.get("boe_id"),
                }
                for item in payload.get("fuentes_oficiales", [])
            ],
            response_summary=f"fuentes_oficiales={len(payload.get('fuentes_oficiales', []))}",
            confidence={"score": 0.9 if payload.get("fuentes_oficiales") else 0.0, "label": "alta" if payload.get("fuentes_oficiales") else "baja"},
            completeness="completa" if payload.get("fuentes_oficiales") else "parcial",
            verified=bool(payload.get("fuentes_oficiales")),
        )
        return payload
