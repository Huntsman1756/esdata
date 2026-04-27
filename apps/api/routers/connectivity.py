from fastapi import APIRouter, HTTPException

from db import db_session
from schemas import (
    ConnectivityArticuloResponse,
    ConnectivityDocumentoResponse,
    ConnectivityObligacionResponse,
)
from services.connectivity import (
    get_article_connectivity,
    get_document_connectivity,
    get_obligation_connectivity,
)

router = APIRouter(prefix="/v1/connectivity", tags=["connectivity"])


@router.get(
    "/articulos/{norma_codigo}/{articulo_numero}",
    response_model=ConnectivityArticuloResponse,
    operation_id="get_connectivity_articulo",
)
async def get_connectivity_articulo(norma_codigo: str, articulo_numero: str):
    with db_session() as db:
        result = get_article_connectivity(db, norma_codigo, articulo_numero)

    if not result:
        raise HTTPException(status_code=404, detail={"error": "Articulo no encontrado"})

    return result


@router.get(
    "/documentos/{referencia}",
    response_model=ConnectivityDocumentoResponse,
    operation_id="get_connectivity_documento",
)
async def get_connectivity_documento(referencia: str):
    with db_session() as db:
        result = get_document_connectivity(db, referencia)

    if not result:
        raise HTTPException(status_code=404, detail={"error": "Documento no encontrado"})

    return result


@router.get(
    "/obligaciones/{codigo}",
    response_model=ConnectivityObligacionResponse,
    operation_id="get_connectivity_obligacion",
)
async def get_connectivity_obligacion(codigo: str):
    with db_session() as db:
        result = get_obligation_connectivity(db, codigo)

    if not result:
        raise HTTPException(status_code=404, detail={"error": "Obligacion no encontrada"})

    return result
