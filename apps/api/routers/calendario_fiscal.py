from db import db_session
from fastapi import APIRouter, Query
from services import calendario_fiscal as cf

router = APIRouter(prefix="/v1/modelos/calendario", tags=["calendario fiscal"])


@router.get(
    "",
    operation_id="list_calendario_fiscal",
    summary="Listar calendario fiscal",
    description="Consulta de periodos de presentacion de modelos fiscales con filtros por modelo, campana y rango de fechas.",
)
async def list_calendario(
    codigo: str | None = Query(None, description="Codigo del modelo AEAT (ej: 100, 303, 200)"),
    campana: str | None = Query(None, description="Campana especifica (ej: 2025, 2025-T1, 2026)"),
    desde: str | None = Query(
        None,
        description="Fecha inicio filtro (YYYY-MM-DD). Devuelve solo entradas cuya fecha_fin >= desde.",
    ),
    hasta: str | None = Query(
        None,
        description="Fecha fin filtro (YYYY-MM-DD). Devuelve solo entradas cuya fecha_inicio <= hasta.",
    ),
):
    with db_session() as db:
        rows = cf.list_calendario(db, codigo=codigo, campana=campana, desde=desde, hasta=hasta)
        return {"entries": rows, "total": len(rows)}


@router.get(
    "/proximo",
    operation_id="get_proximo_vencimiento",
    summary="Proximo vencimiento fiscal",
    description="Devuelve el vencimiento fiscal mas proximo (o vencido) entre todas las entradas activas.",
)
async def get_proximo_vencimiento():
    with db_session() as db:
        row = cf.get_proximo_vencimiento(db)
        if not row:
            return {"proximo": None}
        return {"proximo": row}


@router.get(
    "/{codigo}",
    operation_id="get_calendario_modelo",
    summary="Calendario de un modelo",
    description="Periodos de presentacion de un modelo fiscal con estado (vencido/proximo/pronto/futuro).",
)
async def get_calendario_modelo(
    codigo: str,
    campana: str | None = Query(None, description="Campana especifica (ej: 2025, 2025-T1)"),
):
    with db_session() as db:
        rows = cf.get_calendario_modelo(db, codigo, campana=campana)
        if not rows:
            return {"codigo": codigo, "calendario": [], "total": 0}
        return {"codigo": codigo, "calendario": rows, "total": len(rows)}
