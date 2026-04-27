from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from services.search import search_legislacion
from services.semantic_search import hybrid_search_legislacion
from services.query_audit import get_query_audit_service
from schemas import LegislacionSearchResponse

def _build_legislacion_audit_chunks(result: dict) -> list[dict]:
    chunks: list[dict] = []
    for item in result.get("resultados", []):
        chunk_id = item.get("chunk_id")
        source_hash = item.get("source_hash")
        source_url = item.get("source_url")
        if not any([chunk_id, source_hash, source_url]):
            continue
        chunks.append(
            {
                "norma": item.get("norma"),
                "numero": item.get("numero"),
                "chunk_id": chunk_id,
                "source_hash": source_hash,
                "source_url": source_url,
                "motivo_ranking": item.get("motivo_ranking"),
                "rank": item.get("rank"),
            }
        )
    return chunks


router = APIRouter(tags=["buscar"])


@router.get("/v1/buscar", operation_id="buscar", response_model=LegislacionSearchResponse,
            summary="Buscar en legislacion consolidada")
async def buscar(
    request: Request,
    q: str = Query(..., min_length=1, description="Termino de busqueda"),
    fuente: str | None = Query(None, description="Filtrar por fuente (boe, autonomica, etc.)"),
    ambito: str | None = Query(None, description="Filtrar por ambito (tributario, etc.)"),
    tipo: str | None = Query(None, description="Filtrar por tipo de articulo"),
    norma: str | None = Query(None, description="Filtrar por codigo de norma (LIVA, LIRPF, etc.)"),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    result = search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)
    get_query_audit_service().record_query(
        request_id=request.headers.get("x-request-id") or request.headers.get("X-Request-ID") or "unknown",
        user_id=request.headers.get("x-user-id") or request.headers.get("X-User-ID"),
        path="/v1/buscar",
        query_text=q,
        retrieved_chunks=_build_legislacion_audit_chunks(result),
        response_summary=f"resultados={len(result.get('resultados', []))}",
    )
    return result


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
