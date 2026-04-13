from fastapi import APIRouter, Query

from services.search import search_legislacion
from schemas import LegislacionSearchResponse

router = APIRouter(tags=["buscar"])


@router.get("/v1/buscar", operation_id="buscar", response_model=LegislacionSearchResponse,
            summary="Buscar en legislacion consolidada")
async def buscar(
    q: str = Query(..., min_length=1, description="Termino de busqueda"),
    fuente: str | None = Query(None, description="Filtrar por fuente (boe, autonomica, etc.)"),
    ambito: str | None = Query(None, description="Filtrar por ambito (tributario, etc.)"),
    tipo: str | None = Query(None, description="Filtrar por tipo de articulo"),
    norma: str | None = Query(None, description="Filtrar por codigo de norma (LIVA, LIRPF, etc.)"),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    return search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)


@router.get("/v1/legislacion/buscar", operation_id="buscar_legislacion", response_model=LegislacionSearchResponse,
            summary="Buscar en legislacion consolidada (alias)")
async def buscar_legislacion(
    q: str = Query(..., min_length=1, description="Termino de busqueda"),
    norma: str | None = Query(None, description="Filtrar por codigo de norma"),
    fuente: str | None = Query(None, description="Filtrar por fuente"),
    ambito: str | None = Query(None, description="Filtrar por ambito"),
    tipo: str | None = Query(None, description="Filtrar por tipo de articulo"),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    return search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)
