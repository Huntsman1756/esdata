from fastapi import APIRouter, Query

from change_impact_data import list_seed_changes

router = APIRouter(prefix="/v1/cambios", tags=["cambios"])


@router.get("", operation_id="listar_cambios_regulatorios")
async def listar_cambios_regulatorios(
    fuente: str | None = Query(None),
    estado: str | None = Query(None),
    prioridad: str | None = Query(None),
):
    cambios = list_seed_changes()

    if fuente:
        cambios = [cambio for cambio in cambios if cambio.get("fuente") == fuente]
    if estado:
        cambios = [cambio for cambio in cambios if cambio.get("estado") == estado]
    if prioridad:
        cambios = [cambio for cambio in cambios if cambio.get("prioridad") == prioridad]

    return cambios
