from db import db_session
from fastapi import APIRouter, HTTPException
from schemas import (
    ConnectivityArticuloResponse,
    ConnectivityDocumentoResponse,
    ConnectivityGraphResponse,
    ConnectivityObligacionResponse,
)
from services.connectivity import (
    get_article_connectivity,
    get_document_connectivity,
    get_obligation_connectivity,
)
from services.graph_connectivity import traverse_graph

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


@router.get(
    "/graph/{node_type}/{identifier}",
    response_model=ConnectivityGraphResponse,
    operation_id="get_graph_connectivity",
)
async def get_graph_connectivity(
    node_type: str,
    identifier: str,
    max_depth: int = 2,
):
    """Traverse the entity connectivity graph from any root node.

    Unified graph traversal endpoint that explores relationships across
    all entity types (articulos, documentos, obligaciones, normas,
    modelos, empresas, screening_entries).
    """
    valid_types = {"articulo", "documento", "obligacion", "norma", "modelo", "empresa", "screening_entry"}
    if node_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail={"error": f"node_type must be one of: {', '.join(sorted(valid_types))}"},
        )

    with db_session() as db:
        try:
            result = traverse_graph(db, node_type, identifier, max_depth=max_depth)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc

    return {
        "root": {
            "type": result.root.node_type,
            "id": result.root.node_id,
            "label": result.root.label,
            "properties": result.root.properties,
        },
        "nodes": [
            {
                "type": n.node_type,
                "id": n.node_id,
                "label": n.label,
                "properties": n.properties,
            }
            for n in result.nodes
        ],
        "edges": [
            {
                "type": e.edge_type,
                "source": f"{e.source_type}/{e.source_id}",
                "target": f"{e.target_type}/{e.target_id}",
                "properties": e.properties,
            }
            for e in result.edges
        ],
        "depth": result.depth,
        "max_depth": result.max_depth,
        "stats": {
            "total_nodes": len(result.nodes) + 1,
            "total_edges": len(result.edges),
        },
    }
