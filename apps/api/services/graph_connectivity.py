"""Unified graph connectivity layer using recursive SQL traversal.

Replaces the 3 separate connectivity functions (get_article_connectivity,
get_document_connectivity, get_obligation_connectivity) with a single
graph traversal API that explores entity relationships as a connected graph.

Uses recursive CTEs over the existing PostgreSQL schema — no external graph
database required. This approach works with both SQLite (testing) and
PostgreSQL (production).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text


@dataclass
class GraphNode:
    """A node in the connectivity graph."""

    node_type: str
    node_id: str
    label: str
    properties: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge in the connectivity graph."""

    edge_type: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    properties: dict = field(default_factory=dict)


@dataclass
class GraphResult:
    """Result of a graph traversal."""

    root: GraphNode
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    depth: int = 0
    max_depth: int = 2


# ---------------------------------------------------------------------------
# Recursive CTE templates per node type
# ---------------------------------------------------------------------------

# The graph schema maps entity types to their table/column identity and
# relationship queries. Each entry defines:
# - table + unique identifier columns
# - outbound relationships (edge_type -> target_table + join conditions)
# - properties to include

_NODE_SCHEMA: dict[str, dict[str, Any]] = {
    "articulo": {
        "table": "articulo",
        "id_cols": "a.id",
        "identity": "n.codigo || '/' || a.numero",
        "join": "JOIN norma n ON n.id = a.norma_id",
        "properties": "n.codigo AS norma_codigo, a.numero, a.titulo",
        "edges": {
            "modelos": {
                "target_table": "aeat_modelo",
                "join": "JOIN modelo_articulo ma ON ma.articulo_id = a.id JOIN aeat_modelo m ON m.id = ma.modelo_id",
                "target_id": "m.codigo",
                "properties": "m.nombre, m.impuesto, ma.fuente",
            },
            "doctrina": {
                "target_table": "documento_interpretativo",
                "join": "JOIN documento_articulo da ON da.articulo_id = a.id JOIN documento_interpretativo d ON d.id = da.documento_id",
                "target_id": "d.referencia",
                "properties": "d.organismo_emisor, d.tipo_documento, da.confianza_enlace, da.metodo_enlace",
            },
            "materias": {
                "target_table": "materia",
                "join": "JOIN articulo_materia am ON am.articulo_id = a.id JOIN materia m ON m.id = am.materia_id",
                "target_id": "m.codigo",
                "properties": "m.descripcion",
            },
        },
    },
    "documento": {
        "table": "documento_interpretativo",
        "id_cols": "d.id",
        "identity": "d.referencia",
        "join": "",
        "properties": "d.organismo_emisor, d.tipo_documento, d.referencia",
        "edges": {
            "articulos": {
                "target_table": "articulo",
                "join": "JOIN documento_articulo da ON da.documento_id = d.id JOIN articulo a ON a.id = da.articulo_id JOIN norma n ON n.id = a.norma_id",
                "target_id": "n.codigo || '/' || a.numero",
                "properties": "a.titulo, da.confianza_enlace, da.metodo_enlace",
            },
            "obligaciones": {
                "target_table": "obligacion_regulatoria",
                "join": "JOIN obligacion_documento od ON od.documento_id = d.id JOIN obligacion_regulatoria o ON o.id = od.obligacion_id",
                "target_id": "o.codigo",
                "properties": "o.nombre, o.fuente, od.tipo_relacion",
            },
        },
    },
    "obligacion": {
        "table": "obligacion_regulatoria",
        "id_cols": "o.id",
        "identity": "o.codigo",
        "join": "",
        "properties": "o.nombre, o.fuente",
        "edges": {
            "documentos": {
                "target_table": "documento_interpretativo",
                "join": "JOIN obligacion_documento od ON od.obligacion_id = o.id JOIN documento_interpretativo d ON d.id = od.documento_id",
                "target_id": "d.referencia",
                "properties": "d.organismo_emisor, d.tipo_documento, od.tipo_relacion",
            },
            "articulos": {
                "target_table": "articulo",
                "join": "JOIN obligacion_documento od ON od.obligacion_id = o.id JOIN documento_articulo da ON da.documento_id = od.documento_id JOIN articulo a ON a.id = da.articulo_id JOIN norma n ON n.id = a.norma_id",
                "target_id": "n.codigo || '/' || a.numero",
                "properties": "a.titulo, da.confianza_enlace, da.metodo_enlace",
            },
        },
    },
    "norma": {
        "table": "norma",
        "id_cols": "n.id",
        "identity": "n.codigo",
        "join": "",
        "properties": "n.codigo, n.titulo",
        "edges": {
            "articulos": {
                "target_table": "articulo",
                "join": "JOIN articulo a ON a.norma_id = n.id",
                "target_id": "n.codigo || '/' || a.numero",
                "properties": "a.titulo",
            },
        },
    },
    "modelo": {
        "table": "aeat_modelo",
        "id_cols": "m.id",
        "identity": "m.codigo",
        "join": "",
        "properties": "m.codigo, m.nombre, m.impuesto",
        "edges": {
            "articulos": {
                "target_table": "articulo",
                "join": "JOIN modelo_articulo ma ON ma.modelo_id = m.id JOIN articulo a ON a.id = ma.articulo_id JOIN norma n ON n.id = a.norma_id",
                "target_id": "n.codigo || '/' || a.numero",
                "properties": "a.titulo, ma.fuente",
            },
        },
    },
    "empresa": {
        "table": "empresa",
        "id_cols": "e.id",
        "identity": "e.nif || COALESCE(e.nombre, '')",
        "join": "",
        "properties": "e.nif, e.nombre, e.pais",
        "edges": {
            "screening_matches": {
                "target_table": "screening_entries",
                "join": "JOIN screening_matches sm ON sm.empresa_id = e.id JOIN screening_entries se ON se.id = sm.screening_entry_id",
                "target_id": "se.nombre || '/' || se.id",
                "properties": "sm.confianza, sm.fecha_match, sm.estado",
            },
            "ownership": {
                "target_table": "empresa",
                "join": "JOIN ownership_relation orel ON orel.empresa_padre_id = e.id",
                "target_id": "e2.nif || COALESCE(e2.nombre, '')",
                "properties": "orel.porcentaje, orel.tipo_relacion",
                "alias_table": "empresa e2 ON e2.id = orel.empresa_hija_id",
            },
        },
    },
    "screening_entry": {
        "table": "screening_entries",
        "id_cols": "se.id",
        "identity": "se.nombre || '/' || se.id",
        "join": "",
        "properties": "se.nombre, se.tipo, se.lista_origen",
        "edges": {
            "matches": {
                "target_table": "empresa",
                "join": "JOIN screening_matches sm ON sm.screening_entry_id = se.id",
                "target_id": "e.nif || COALESCE(e.nombre, '')",
                "properties": "sm.confianza, sm.fecha_match, sm.estado",
            },
            "lists": {
                "target_table": "screening_lists",
                "join": "JOIN screening_lists sl ON sl.id = se.lista_id",
                "target_id": "sl.nombre",
                "properties": "sl.descripcion, sl.agencia",
            },
        },
    },
}


def _build_traversal_sql(
    node_type: str,
    identifier: str,
    max_depth: int = 2,
) -> tuple[str, dict[str, Any]]:
    """Build a recursive CTE SQL query for graph traversal.

    Args:
        node_type: One of 'articulo', 'documento', 'obligacion', 'norma', 'modelo', 'empresa', 'screening_entry'.
        identifier: The unique identifier value for the root node.
        max_depth: Maximum traversal depth.

    Returns:
        (sql_query, params_dict) ready for db.execute(text(sql), params).
    """
    schema = _NODE_SCHEMA.get(node_type)
    if schema is None:
        raise ValueError(f"Unknown node type: {node_type}. Valid: {list(_NODE_SCHEMA.keys())}")

    # Build root CTE
    root_where = _build_root_where(node_type, identifier)

    # Build recursive CTE for each edge type
    cte_parts = [
        f"""
        WITH RECURSIVE visited AS (
            SELECT
                '{node_type}' AS node_type,
                {schema['identity']} AS node_id,
                {schema['properties']} AS properties,
                0 AS depth
            FROM {schema['table']}
            {schema['join']}
            WHERE {root_where}
            UNION ALL
        """
    ]

    # Build union parts for each edge type
    union_clauses = []
    for edge_schema in schema["edges"].values():
        extra_join = edge_schema.get("alias_table", "")
        union_clauses.append(
            f"""
            SELECT
                '{edge_schema['target_table']}' AS node_type,
                {edge_schema['target_id']} AS node_id,
                {edge_schema['properties']} AS properties,
                v.depth + 1 AS depth
            FROM visited v
            JOIN {edge_schema['target_table']} ON {edge_schema['join']}
            {extra_join}
            WHERE v.depth < {max_depth}
              AND NOT EXISTS (
                  SELECT 1 FROM visited v2
                  WHERE v2.node_type = '{edge_schema['target_table']}'
                    AND v2.node_id = {edge_schema['target_id']}
              )
        """
        )

    cte_parts.append(" UNION ALL ".join(union_clauses))
    cte_parts.append(" )\nSELECT * FROM visited ORDER BY depth, node_type, node_id")

    sql = "\n".join(cte_parts)
    return sql, {"identifier": identifier}


def _build_root_where(node_type: str, identifier: str) -> str:
    """Build WHERE clause for the root node lookup."""
    if node_type == "articulo":
        # identifier format: "LIVA/1"
        parts = identifier.split("/", 1)
        if len(parts) == 2:
            return "n.codigo = :norma AND a.numero = :articulo"
        return "a.id = :id"
    if node_type == "documento":
        return "d.referencia = :identifier"
    if node_type == "obligacion":
        return "o.codigo = :identifier"
    if node_type == "norma":
        return "n.codigo = :identifier"
    if node_type == "modelo":
        return "m.codigo = :identifier"
    if node_type == "empresa":
        return "e.nif = :identifier"
    if node_type == "screening_entry":
        return "se.id = :identifier"
    return "1=0"


def traverse_graph(
    db,
    node_type: str,
    identifier: str,
    max_depth: int = 2,
) -> GraphResult:
    """Traverse the entity connectivity graph starting from a root node.

    Walks the graph using recursive CTEs, returning all reachable nodes
    and their relationships up to the specified depth.

    Args:
        db: SQLAlchemy database connection.
        node_type: Entity type to start from.
        identifier: Unique identifier for the root entity.
        max_depth: Maximum traversal depth (default 2).

    Returns:
        GraphResult with root node, all discovered nodes and edges.

    Examples:
        traverse_graph(db, "articulo", "LIVA/1")
        traverse_graph(db, "documento", "DGT/2023/001")
        traverse_graph(db, "obligacion", "IVA-001")
    """
    sql, params = _build_traversal_sql(node_type, identifier, max_depth)
    rows = list(db.execute(text(sql), params).mappings())

    if not rows:
        raise ValueError(f"Node not found: {node_type}/{identifier}")

    # Build graph from flat rows
    nodes_by_id: dict[tuple[str, str], GraphNode] = {}
    edges: list[GraphEdge] = []

    for row in rows:
        n_type = row["node_type"]
        n_id = row["node_id"]
        props = dict(row)
        props.pop("node_type", None)
        props.pop("node_id", None)
        props.pop("depth", None)

        key = (n_type, n_id)
        if key not in nodes_by_id:
            nodes_by_id[key] = GraphNode(
                node_type=n_type,
                node_id=n_id,
                label=_format_label(n_type, props),
                properties=props,
            )

    # Build edges from adjacency (parent -> child by depth)
    depth_rows = sorted(rows, key=lambda r: r["depth"])
    root_depth = depth_rows[0]["depth"]
    for row in depth_rows:
        if row["depth"] == root_depth:
            continue
        n_type = row["node_type"]
        n_id = row["node_id"]
        # Find parent at depth - 1 (simplified: assume single parent)
        for prev in reversed(depth_rows):
            if prev["depth"] == row["depth"] - 1:
                # Check if this parent could be the source
                parent_key = (prev["node_type"], prev["node_id"])
                if parent_key in nodes_by_id:
                    parent = nodes_by_id[parent_key]
                    edges.append(GraphEdge(
                        edge_type=_infer_edge_type(n_type),
                        source_type=parent.node_type,
                        source_id=parent.node_id,
                        target_type=n_type,
                        target_id=n_id,
                        properties=dict(row),
                    ))
                break

    root_key = (depth_rows[0]["node_type"], depth_rows[0]["node_id"])
    root = nodes_by_id[root_key]
    nodes = [n for k, n in nodes_by_id.items() if k != root_key]

    return GraphResult(
        root=root,
        nodes=nodes,
        edges=edges,
        depth=max_depth,
        max_depth=max_depth,
    )


def _format_label(node_type: str, properties: dict) -> str:
    """Format a human-readable label for a graph node."""
    if node_type == "articulo":
        return f"{properties.get('norma_codigo', '')}/{properties.get('numero', '')}"
    if node_type == "documento":
        return properties.get("referencia", node_type)
    if node_type == "obligacion":
        return properties.get("codigo", node_type)
    if node_type == "norma":
        return properties.get("codigo", node_type)
    if node_type == "modelo":
        return properties.get("codigo", node_type)
    if node_type == "empresa":
        return properties.get("nif", properties.get("nombre", node_type))
    if node_type == "screening_entry":
        return properties.get("nombre", node_type)
    return str(properties)


def _infer_edge_type(target_type: str) -> str:
    """Infer edge type from target node type."""
    mapping = {
        "articulo": "references",
        "documento_interpretativo": "cites",
        "obligacion_regulatoria": "relates_to",
        "norma": "belongs_to",
        "aeat_modelo": "references",
        "empresa": "owns",
        "screening_entries": "matches",
        "screening_lists": "belongs_to",
        "materia": "classified_under",
    }
    return mapping.get(target_type, "related_to")


# Legacy compatibility — thin wrappers around the unified traversal

def get_article_connectivity(db, norma_codigo: str, articulo_numero: str):
    """Legacy wrapper: get connectivity for a specific article."""
    result = traverse_graph(db, "articulo", f"{norma_codigo}/{articulo_numero}")
    articulo_props = result.root.properties
    return {
        "articulo": {
            "norma": articulo_props.get("norma_codigo", ""),
            "numero": articulo_props.get("numero", ""),
            "titulo": articulo_props.get("titulo", ""),
        },
        "modelos": [
            {
                "codigo": n.node_id,
                "nombre": n.properties.get("nombre", ""),
                "impuesto": n.properties.get("impuesto", ""),
                "fuente": n.properties.get("fuente", ""),
            }
            for n in result.nodes
            if n.node_type == "aeat_modelo"
        ],
        "doctrina": [
            {
                "referencia": n.node_id,
                "organismo_emisor": n.properties.get("organismo_emisor", ""),
                "tipo_documento": n.properties.get("tipo_documento", ""),
                "confianza_enlace": float(n.properties.get("confianza_enlace", 0)),
            }
            for n in result.nodes
            if n.node_type == "documento_interpretativo"
        ],
        "obligaciones": [
            {
                "codigo": n.node_id,
                "nombre": n.properties.get("nombre", ""),
                "fuente": n.properties.get("fuente", ""),
            }
            for n in result.nodes
            if n.node_type == "obligacion_regulatoria"
        ],
        "totales": {
            "modelos": len([n for n in result.nodes if n.node_type == "aeat_modelo"]),
            "doctrina": len([n for n in result.nodes if n.node_type == "documento_interpretativo"]),
            "obligaciones": len([n for n in result.nodes if n.node_type == "obligacion_regulatoria"]),
        },
    }


def get_document_connectivity(db, referencia: str):
    """Legacy wrapper: get connectivity for a specific document."""
    result = traverse_graph(db, "documento", referencia)
    return {
        "documento": {
            "referencia": result.root.properties.get("referencia", ""),
            "organismo_emisor": result.root.properties.get("organismo_emisor", ""),
            "tipo_documento": result.root.properties.get("tipo_documento", ""),
        },
        "articulos": [
            {
                "norma": n.properties.get("norma_codigo", ""),
                "numero": n.node_id.split("/")[-1] if "/" in n.node_id else "",
                "confianza_enlace": float(n.properties.get("confianza_enlace", 0)),
            }
            for n in result.nodes
            if n.node_type == "articulo"
        ],
        "obligaciones": [
            {
                "codigo": n.node_id,
                "nombre": n.properties.get("nombre", ""),
                "fuente": n.properties.get("fuente", ""),
            }
            for n in result.nodes
            if n.node_type == "obligacion_regulatoria"
        ],
        "totales": {
            "articulos": len([n for n in result.nodes if n.node_type == "articulo"]),
            "obligaciones": len([n for n in result.nodes if n.node_type == "obligacion_regulatoria"]),
        },
    }


def get_obligation_connectivity(db, codigo: str):
    """Legacy wrapper: get connectivity for a specific obligation."""
    result = traverse_graph(db, "obligacion", codigo)
    return {
        "obligacion": {
            "codigo": result.root.properties.get("codigo", ""),
            "nombre": result.root.properties.get("nombre", ""),
            "fuente": result.root.properties.get("fuente", ""),
        },
        "documentos": [
            {
                "referencia": n.node_id,
                "organismo_emisor": n.properties.get("organismo_emisor", ""),
                "tipo_documento": n.properties.get("tipo_documento", ""),
            }
            for n in result.nodes
            if n.node_type == "documento_interpretativo"
        ],
        "articulos": [
            {
                "norma": n.properties.get("norma_codigo", ""),
                "numero": n.node_id.split("/")[-1] if "/" in n.node_id else "",
                "confianza_enlace": float(n.properties.get("confianza_enlace", 0)),
            }
            for n in result.nodes
            if n.node_type == "articulo"
        ],
        "totales": {
            "documentos": len([n for n in result.nodes if n.node_type == "documento_interpretativo"]),
            "articulos": len([n for n in result.nodes if n.node_type == "articulo"]),
        },
    }
