from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db import db_session
from schemas import (
    ModeloDetail as ModeloDetailSchema,
    ModelosListResponse,
)

router = APIRouter(prefix="/v1/modelos", tags=["modelos"])


def _get_active_campaign(db, codigo: str, campana: str = None):
    """Get active or specified campaign for a model.

    Works with both Postgres (modelo_campana_activa function) and SQLite
    (direct query fallback).
    """
    if campana:
        row = db.execute(
            text(
                """
                SELECT id, campana, url_instrucciones, url_normativa, url_formato
                FROM modelo_campana
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                  AND campana = :campana
                LIMIT 1
                """
            ),
            {"codigo": codigo, "campana": campana},
        ).mappings().first()
    else:
        # Try the Postgres function first; fall back to raw query on SQLite
        try:
            row = db.execute(
                text(
                    "SELECT id, campana, url_instrucciones, url_normativa, url_formato FROM modelo_campana_activa((SELECT id FROM aeat_modelo WHERE codigo = :codigo))"
                ),
                {"codigo": codigo},
            ).mappings().first()
        except Exception:
            # SQLite fallback: direct query
            row = db.execute(
                text(
                    """
                    SELECT id, campana, url_instrucciones, url_normativa, url_formato
                    FROM modelo_campana
                    WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                      AND activo = true
                    ORDER BY campana DESC
                    LIMIT 1
                    """
                ),
                {"codigo": codigo},
            ).mappings().first()
    return row


@router.get("", operation_id="list_modelos", response_model=ModelosListResponse)
async def list_modelos():
    """Lista todos los modelos AEAT disponibles."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    m.codigo,
                    m.nombre,
                    m.periodo,
                    m.impuesto,
                    COUNT(DISTINCT ma.articulo_id) AS articulos_count,
                    COUNT(DISTINCT mc.id) AS casillas_count
                FROM aeat_modelo m
                LEFT JOIN modelo_articulo ma ON ma.modelo_id = m.id
                LEFT JOIN modelo_campana mcam ON mcam.modelo_id = m.id AND mcam.activo = true
                LEFT JOIN modelo_casilla mc ON mc.campana_id = mcam.id AND mc.activa = true
                GROUP BY m.id, m.codigo, m.nombre, m.periodo, m.impuesto
                ORDER BY m.codigo
                """
            )
        ).mappings()

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


@router.get("/{codigo}", operation_id="get_modelo", response_model=ModeloDetailSchema,
            summary="Detalle de un modelo AEAT")
async def get_modelo(codigo: str, campana: str = Query(None, description="Campana especifica (ej: 2025). Si no se indica, usa la activa.")):
    """
    Detalle de un modelo con artículos, casillas, claves, instrucciones,
    normativa y doctrina relacionada.
    
    Query params:
    - campana: filtra por campaña específica (ej: '2025'). Si no se indica,
      usa la campaña activa más reciente.
    """
    with db_session() as db:
        model_row = db.execute(
            text(
                """
                SELECT codigo, nombre, periodo, impuesto, url_info
                FROM aeat_modelo
                WHERE codigo = :codigo
                LIMIT 1
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        camp_row = _get_active_campaign(db, codigo, campana)
        campana_id = camp_row["id"] if camp_row else None
        campana_activa = camp_row["campana"] if camp_row else None

        art_rows = db.execute(
            text(
                """
                SELECT
                    n.codigo AS norma,
                    a.numero,
                    a.titulo,
                    ma.casilla,
                    ma.nota,
                    ma.fuente,
                    ma.url_fuente
                FROM modelo_articulo ma
                JOIN articulo a ON a.id = ma.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE ma.modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                ORDER BY n.codigo, a.numero
                """
            ),
            {"codigo": codigo},
        ).mappings()

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
            cas_rows = db.execute(
                text(
                    """
                    SELECT codigo, etiqueta, descripcion, tipo_casilla, pagina, orden
                    FROM modelo_casilla
                    WHERE campana_id = :campana_id AND activa = true
                    ORDER BY orden
                    """
                ),
                {"campana_id": campana_id},
            ).mappings()
            casillas = [dict(r) for r in cas_rows]

        claves = []
        if campana_id:
            clav_rows = db.execute(
                text(
                    """
                    SELECT codigo, etiqueta, descripcion, tipo_clave
                    FROM modelo_clave
                    WHERE campana_id = :campana_id AND activa = true
                    ORDER BY codigo
                    """
                ),
                {"campana_id": campana_id},
            ).mappings()
            claves = [dict(r) for r in clav_rows]

        instrucciones = []
        if campana_id:
            instr_rows = db.execute(
                text(
                    """
                    SELECT seccion, titulo, contenido, orden
                    FROM modelo_instruccion
                    WHERE campana_id = :campana_id
                    ORDER BY orden
                    """
                ),
                {"campana_id": campana_id},
            ).mappings()
            instrucciones = [dict(r) for r in instr_rows]

        norm_rows = db.execute(
            text(
                """
                SELECT boe_id, titulo, fecha, url_boe, resumen
                FROM modelo_normativa
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                ORDER BY fecha DESC
                """
            ),
            {"codigo": codigo},
        ).mappings()
        normativa = [dict(r) for r in norm_rows]

        camp_rows = db.execute(
            text(
                """
                SELECT campana, activo
                FROM modelo_campana
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                ORDER BY campana DESC
                """
            ),
            {"codigo": codigo},
        ).mappings()
        campanas = [dict(r) for r in camp_rows]

        if articulos:
            conditions = []
            params = {}
            for i, art in enumerate(articulos):
                conditions.append(f"n.codigo = :n{i} AND a.numero = :a{i}")
                params[f"n{i}"] = art["norma"]
                params[f"a{i}"] = art["numero"]

            where_clause = " OR ".join(conditions)

            doc_rows = db.execute(
                text(
                    f"""
                    SELECT DISTINCT
                        di.referencia,
                        di.organismo_emisor,
                        di.fecha,
                        n.codigo AS norma,
                        a.numero
                    FROM documento_articulo da
                    JOIN documento_interpretativo di ON di.id = da.documento_id
                    JOIN articulo a ON a.id = da.articulo_id
                    JOIN norma n ON n.id = a.norma_id
                    WHERE {where_clause}
                    ORDER BY di.fecha DESC
                    LIMIT 50
                    """
                ),
                params,
            ).mappings()

            doctrina_map = {}
            for row in doc_rows:
                ref = row["referencia"]
                if ref not in doctrina_map:
                    doctrina_map[ref] = {
                        "referencia": ref,
                        "organismo_emisor": row["organismo_emisor"],
                        "fecha": str(row["fecha"]) if row["fecha"] else None,
                        "via_articulos": [],
                    }
                doctrina_map[ref]["via_articulos"].append(
                    {"norma": row["norma"], "numero": row["numero"]}
                )

            doctrina_relacionada = list(doctrina_map.values())
        else:
            doctrina_relacionada = []

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
        model_row = db.execute(
            text(
                """
                SELECT codigo FROM aeat_modelo WHERE codigo = :codigo LIMIT 1
                """
            ),
            {"codigo": codigo},
        ).mappings().first()

        if not model_row:
            raise HTTPException(
                status_code=404, detail={"error": f"Modelo {codigo} no encontrado"}
            )

        rows = db.execute(
            text(
                """
                SELECT
                    n.codigo AS norma,
                    a.numero,
                    a.titulo,
                    ma.casilla,
                    ma.nota,
                    ma.fuente,
                    ma.url_fuente
                FROM modelo_articulo ma
                JOIN articulo a ON a.id = ma.articulo_id
                JOIN norma n ON n.id = a.norma_id
                WHERE ma.modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                ORDER BY n.codigo, a.numero
                """
            ),
            {"codigo": codigo},
        ).mappings()

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


@router.get("/{codigo}/casillas", operation_id="get_modelo_casillas", response_model=None,
            summary="Casillas de un modelo")
async def get_modelo_casillas(codigo: str, campana: str = Query(None, description="Campana especifica")):
    """Lista todas las casillas de un modelo para una campaña."""
    with db_session() as db:
        camp_row = _get_active_campaign(db, codigo, campana)

        if not camp_row:
            return {"codigo": codigo, "casillas": []}

        campana_id = camp_row["id"]

        rows = db.execute(
            text(
                """
                SELECT codigo, etiqueta, descripcion, tipo_casilla, pagina, orden
                FROM modelo_casilla
                WHERE campana_id = :campana_id AND activa = true
                ORDER BY orden
                """
            ),
            {"campana_id": campana_id},
        ).mappings()

        return {
            "codigo": codigo,
            "casillas": [dict(r) for r in rows],
        }


@router.get("/{codigo}/claves", operation_id="get_modelo_claves",
            summary="Claves de un modelo")
async def get_modelo_claves(codigo: str, campana: str = Query(None, description="Campana especifica")):
    """Lista todas las claves de un modelo para una campaña."""
    with db_session() as db:
        camp_row = _get_active_campaign(db, codigo, campana)

        if not camp_row:
            return {"codigo": codigo, "claves": []}

        campana_id = camp_row["id"]

        rows = db.execute(
            text(
                """
                SELECT codigo, etiqueta, descripcion, tipo_clave
                FROM modelo_clave
                WHERE campana_id = :campana_id AND activa = true
                ORDER BY codigo
                """
            ),
            {"campana_id": campana_id},
        ).mappings()

        return {
            "codigo": codigo,
            "claves": [dict(r) for r in rows],
        }


@router.get("/{codigo}/instrucciones", operation_id="get_modelo_instrucciones",
            summary="Instrucciones de un modelo")
async def get_modelo_instrucciones(codigo: str, campana: str = Query(None, description="Campana especifica")):
    """Lista las instrucciones de un modelo para una campaña."""
    with db_session() as db:
        camp_row = _get_active_campaign(db, codigo, campana)

        if not camp_row:
            return {"codigo": codigo, "instrucciones": []}

        campana_id = camp_row["id"]

        rows = db.execute(
            text(
                """
                SELECT seccion, titulo, contenido, orden
                FROM modelo_instruccion
                WHERE campana_id = :campana_id
                ORDER BY orden
                """
            ),
            {"campana_id": campana_id},
        ).mappings()

        return {
            "codigo": codigo,
            "instrucciones": [dict(r) for r in rows],
        }


@router.get("/{codigo}/normativa", operation_id="get_modelo_normativa")
async def get_modelo_normativa(codigo: str):
    """Lista la normativa (BOE) de un modelo."""
    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT boe_id, titulo, fecha, url_boe, resumen
                FROM modelo_normativa
                WHERE modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
                ORDER BY fecha DESC
                """
            ),
            {"codigo": codigo},
        ).mappings()

        return {
            "codigo": codigo,
            "normativa": [dict(r) for r in rows],
        }
