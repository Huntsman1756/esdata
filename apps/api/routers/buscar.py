import re

from db import db_session
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from schemas import LegislacionSearchResponse
from services.query_audit import get_query_audit_service
from services.search import search_legislacion
from services.semantic_search import hybrid_search_legislacion
from sqlalchemy import text


def _buscar_comparacion_modelos_aeat(q: str) -> dict | None:
    lowered_query = q.lower()
    if "modelo" not in lowered_query:
        return None

    codigos = []
    for codigo in re.findall(r"\b\d{3}\b", q):
        if codigo not in codigos:
            codigos.append(codigo)

    if len(codigos) < 2:
        return None

    placeholders = ", ".join(f":codigo_{index}" for index, _ in enumerate(codigos))
    params = {f"codigo_{index}": codigo for index, codigo in enumerate(codigos)}

    with db_session() as db:
        rows = db.execute(
            text(
                """
                SELECT codigo, nombre, url_info
                FROM aeat_modelo
                WHERE codigo IN (""" + placeholders + """)
                ORDER BY codigo
                """
            ),
            params,
        ).mappings().all()

    if len(rows) < 2:
        return None

    return {
        "q": q,
        "resultados": [
            {
                "tipo": "modelo",
                "norma": "AEAT",
                "numero": row["codigo"],
                "texto": row["nombre"],
                "fragmento": row["nombre"],
                "vigente_desde": None,
                "vigente_hasta": None,
                "rank": 1.0,
                "confianza": {
                    "nivel": 2,
                    "fuentes": [row["url_info"]] if row.get("url_info") else [],
                    "aviso": None,
                },
            }
            for row in rows
        ],
    }

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


def _record_search_query_audit(
    request: Request,
    *,
    path: str,
    query_text: str,
    tool_name: str,
    result: dict,
):
    resultados = result.get("resultados", [])
    has_results = bool(resultados)
    get_query_audit_service().record_query(
        request_id=request.headers.get("x-request-id")
        or request.headers.get("X-Request-ID")
        or "unknown",
        user_id=request.headers.get("x-user-id") or request.headers.get("X-User-ID"),
        path=path,
        query_text=query_text,
        retrieved_chunks=_build_legislacion_audit_chunks(result),
        response_summary=f"resultados={len(resultados)}",
        tool_name=tool_name,
        confidence={"score": 0.9 if has_results else 0.0, "label": "alta" if has_results else "baja"},
        completeness="completa" if has_results else "parcial",
        verified=has_results,
    )


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
    result = _buscar_comparacion_modelos_aeat(q)
    if result is None:
        result = search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)
    _record_search_query_audit(
        request,
        path="/v1/buscar",
        query_text=q,
        tool_name="buscar",
        result=result,
    )
    return result


@router.get("/v1/legislacion/buscar", operation_id="buscar_legislacion",
            summary="Buscar en legislacion consolidada (alias)")
async def buscar_legislacion(
    request: Request,
    q: str = Query(..., min_length=1, description="Termino de busqueda"),
    norma: str | None = Query(None, description="Filtrar por codigo de norma"),
    fuente: str | None = Query(None, description="Filtrar por fuente"),
    ambito: str | None = Query(None, description="Filtrar por ambito"),
    tipo: str | None = Query(None, description="Filtrar por tipo de articulo"),
    vigente_en: str | None = Query(None, description="Fecha de vigencia (YYYY-MM-DD)"),
):
    result = search_legislacion(q, norma, fuente, ambito, tipo, vigente_en)
    _record_search_query_audit(
        request,
        path="/v1/legislacion/buscar",
        query_text=q,
        tool_name="buscar_legislacion",
        result=result,
    )
    # Return dict directly; FastAPI uses jsonable_encoder which handles Decimal.
    # Do NOT wrap in JSONResponse — its stdlib json.dumps does not know Decimal
    # and raises TypeError for any numeric column coming from SQL (e.g. ranking).
    return result


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
    return result
