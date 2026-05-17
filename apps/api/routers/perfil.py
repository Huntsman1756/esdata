from __future__ import annotations

from collections import Counter

from db import db_session
from fastapi import APIRouter, HTTPException, Query
from mcp_tools_perfil import (
    DominioPerfil,
    ObligacionesResponse,
    PerfilNotFoundError,
    calendario_obligaciones_perfil,
    listar_perfiles_entidad,
    obtener_obligaciones_perfil,
)


router = APIRouter(prefix="/v1/perfil", tags=["perfil", "aplicabilidad"])


@router.get("", operation_id="listar_perfiles_entidad")
async def listar_perfiles():
    with db_session() as db:
        return [perfil.model_dump(mode="json") for perfil in listar_perfiles_entidad(db)]


@router.get("/{codigo}", operation_id="get_perfil_entidad")
async def get_perfil(codigo: str):
    try:
        with db_session() as db:
            response = obtener_obligaciones_perfil(db, codigo, "ALL")
    except PerfilNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    counts = Counter(item.obligacion_tipo for item in response.obligaciones)
    return {
        **response.perfil.model_dump(mode="json"),
        "obligaciones_total": response.total,
        "obligaciones_por_tipo": dict(sorted(counts.items())),
    }


@router.get("/{codigo}/obligaciones", operation_id="obtener_obligaciones_perfil")
async def get_obligaciones_perfil(
    codigo: str,
    dominio: DominioPerfil = Query("ALL"),
    verified: bool | None = Query(None),
):
    try:
        with db_session() as db:
            response = obtener_obligaciones_perfil(db, codigo, dominio)
    except PerfilNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if verified is not None:
        response = ObligacionesResponse(
            perfil=response.perfil,
            dominio_filtrado=response.dominio_filtrado,
            obligaciones=[item for item in response.obligaciones if item.verified is verified],
        )
    return response.model_dump(mode="json")


@router.get(
    "/{codigo}/obligaciones/calendario",
    operation_id="calendario_obligaciones_perfil",
    summary="Calendario de obligaciones por perfil",
    description=(
        "Devuelve el calendario operativo agrupado por periodicidad. Si se proporciona "
        "el parametro quarter (ej: 2026-Q3), devuelve solo las obligaciones con "
        "vencimiento en ese trimestre segun periodicidad y plazo_descripcion "
        "estructurados."
    ),
)
async def get_calendario_obligaciones_perfil(
    codigo: str,
    quarter: str | None = Query(None, description="Trimestre: Q1, Q2, Q3, Q4 o YYYY-QN"),
):
    try:
        with db_session() as db:
            response = calendario_obligaciones_perfil(db, codigo, quarter=quarter)
    except PerfilNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if quarter:
        return [item.model_dump(mode="json") for item in response.obligaciones]
    return response.model_dump(mode="json")


@router.get(
    "/{codigo}/obligaciones/calendario/{quarter}",
    operation_id="calendario_obligaciones_perfil_quarter",
)
async def get_calendario_obligaciones_perfil_quarter(codigo: str, quarter: str):
    try:
        with db_session() as db:
            response = calendario_obligaciones_perfil(db, codigo, quarter=quarter)
    except PerfilNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [item.model_dump(mode="json") for item in response.obligaciones]
