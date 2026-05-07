"""Tests for graph connectivity layer."""

from __future__ import annotations

import pytest
from services.graph_connectivity import (
    _NODE_SCHEMA,
    GraphEdge,
    GraphNode,
    GraphResult,
    _build_root_where,
    _build_traversal_sql,
)


class TestNodeSchema:
    """Verify the node schema covers all expected entity types."""

    def test_all_expected_node_types_present(self):
        expected = {"articulo", "documento", "obligacion", "norma", "modelo", "empresa", "screening_entry"}
        assert expected.issubset(set(_NODE_SCHEMA.keys()))

    def test_each_node_type_has_required_fields(self):
        required = {"table", "id_cols", "identity", "join", "properties", "edges"}
        for node_type, schema in _NODE_SCHEMA.items():
            assert required.issubset(set(schema.keys())), f"{node_type} missing fields"

    def test_each_edge_has_required_fields(self):
        required = {"target_table", "join", "target_id", "properties"}
        for node_type, schema in _NODE_SCHEMA.items():
            for edge_type, edge_schema in schema["edges"].items():
                assert required.issubset(set(edge_schema.keys())), \
                    f"{node_type}.{edge_type} missing fields"

    def test_documento_edge_properties_keep_metodo_enlace_and_confianza_enlace(self):
        doctrina_props = _NODE_SCHEMA["documento"]["edges"]["articulos"]["properties"]

        assert "da.metodo_enlace" in doctrina_props
        assert "da.confianza_enlace" in doctrina_props

    def test_articulo_edge_properties_keep_doctrina_link_semantics(self):
        doctrina_props = _NODE_SCHEMA["articulo"]["edges"]["doctrina"]["properties"]

        assert "da.metodo_enlace" in doctrina_props
        assert "da.confianza_enlace" in doctrina_props


class TestRootWhere:
    """Test root WHERE clause generation."""

    def test_documento_where(self):
        assert _build_root_where("documento", "DGT/2023/001") == "d.referencia = :identifier"

    def test_obligacion_where(self):
        assert _build_root_where("obligacion", "IVA-001") == "o.codigo = :identifier"

    def test_norma_where(self):
        assert _build_root_where("norma", "LIVA") == "n.codigo = :identifier"

    def test_articulo_where_with_slash(self):
        result = _build_root_where("articulo", "LIVA/1")
        assert "n.codigo = :norma" in result
        assert "a.numero = :articulo" in result

    def test_articulo_where_without_slash(self):
        result = _build_root_where("articulo", "999")
        assert "a.id = :id" in result


class TestTraversalSQL:
    """Test recursive CTE SQL generation."""

    def test_build_traversal_sql_articulo(self):
        sql, params = _build_traversal_sql("articulo", "LIVA/1", max_depth=2)
        assert "WITH RECURSIVE" in sql
        assert "visited" in sql
        assert "UNION ALL" in sql
        assert ":norma" in sql
        assert ":articulo" in sql
        assert params == {"identifier": "LIVA/1"}

    def test_build_traversal_sql_documento(self):
        sql, _ = _build_traversal_sql("documento", "DGT/2023/001")
        assert "d.referencia = :identifier" in sql

    def test_build_traversal_sql_invalid_type(self):
        with pytest.raises(ValueError, match="Unknown node type"):
            _build_traversal_sql("invalid_type", "x")

    def test_max_depth_in_query(self):
        sql, _ = _build_traversal_sql("norma", "LIVA", max_depth=3)
        assert "v.depth < 3" in sql


class TestGraphResult:
    """Test graph result dataclasses."""

    def test_graph_node_defaults(self):
        node = GraphNode(node_type="test", node_id="1", label="Test")
        assert node.properties == {}

    def test_graph_edge_defaults(self):
        edge = GraphEdge(
            edge_type="related",
            source_type="a",
            source_id="1",
            target_type="b",
            target_id="2",
        )
        assert edge.properties == {}

    def test_graph_result_defaults(self):
        result = GraphResult(root=GraphNode(node_type="a", node_id="1", label="A"))
        assert result.nodes == []
        assert result.edges == []
        assert result.depth == 0
        assert result.max_depth == 2
