from fastapi import APIRouter, Query

from services.search import search_legislacion

router = APIRouter(tags=["buscar"])


@router.get("/v1/buscar", operation_id="buscar")
async def buscar(
    q: str = Query(..., min_length=1),
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    norma: str | None = None,
    vigente_en: str | None = None,
):
    return search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)


@router.get("/v1/legislacion/buscar", operation_id="buscar_legislacion")
async def buscar_legislacion(
    q: str = Query(..., min_length=1),
    norma: str | None = None,
    fuente: str | None = None,
    ambito: str | None = None,
    tipo: str | None = None,
    vigente_en: str | None = None,
):
    return search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)
