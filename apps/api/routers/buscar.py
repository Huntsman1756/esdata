from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from services.search import search_legislacion
from services.semantic_search import hybrid_search_legislacion
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


@router.get("/v1/legislacion/buscar", operation_id="buscar_legislacion",
            summary="Buscar en legislacion consolidada (alias)")
async def buscar_legislacion(
    q: str = Query(..., min_length=1, description="Termino de busqueda"),
    norma: str | None = Query(None, description="Filtrar por codigo de norma"),
    fuente: str | None = Query(None, description="Filtrar por fuente"),
    ambito: str | None = Query(None, description="Filtrar por ambito"),
    tipo: str | None = Query(None, description="Filtrar por tipo de articulo"),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    result = search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)
    return JSONResponse(content=result)


@router.get("/v1/legislacion/buscar/hybrid", operation_id="buscar_legislacion_hybrid")
async def buscar_legislacion_hybrid(
    q: str = Query(..., min_length=1, description="Termino de busqueda"),
    norma: str | None = Query(None, description="Filtrar por codigo de norma"),
    fuente: str | None = Query(None, description="Filtrar por fuente"),
    ambito: str | None = Query(None, description="Filtrar por ambito"),
    tipo: str | None = Query(None, description="Filtrar por tipo de articulo"),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
    hybrid_weight: float = Query(0.3, ge=0.0, le=1.0, description="Peso de busqueda vectorial (0.0=fulltext, 0.3=optimo, 1.0=vectorial)"),
    limit: int = Query(10, ge=1, le=50, description="Numero maximo de resultados"),
):
    result = hybrid_search_legislacion(
        q, norma, fuente, ambito, tipo, vigente_en, hybrid_weight, limit
    )
    return JSONResponse(content=result)
