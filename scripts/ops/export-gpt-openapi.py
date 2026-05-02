#!/usr/bin/env python
"""Export a curated OpenAPI spec for Custom GPT Actions.

Produces a spec containing only the 7 endpoints relevant for the GPT,
with clean descriptions and (optionally) OpenAPI 3.0.x compatibility.

Usage:
    python scripts/ops/export-gpt-openapi.py                  # default: 3.1.0
    python scripts/ops/export-gpt-openapi.py --openapi 3.0.3  # force 3.0.x
    python scripts/ops/export-gpt-openapi.py --output docs/openapi-gpt.json
"""

import json
import argparse
from pathlib import Path
import sys
from copy import deepcopy

# Allow importing from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from main import app

# ---------------------------------------------------------------------------
# Curated list of paths to expose to the GPT
# ---------------------------------------------------------------------------
INCLUDE_PATHS = {
    "/v1/legislacion/buscar",
    "/v1/legislacion/{codigo}",
    "/v1/legislacion/{codigo}/articulos/{numero}",
    "/v1/doctrina/buscar",
    "/v1/doctrina/{referencia}",
    "/v1/modelos",
    "/v1/modelos/{codigo}",
}

# Schemas referenced by the curated endpoints
INCLUDE_SCHEMAS = {
    "LegislacionSearchResponse",
    "SearchResult",
    "ConfianzaInfo",
    "Norma",
    "ArticuloDetail",
    "DoctrinaSearchResponse",
    "DoctrinaSearchResult",
    "DoctrinaDetail",
    "ArticuloRelacionado",
    "ModelosListResponse",
    "ModeloSummary",
    "ModeloDetail",
    "ModeloArticulo",
    "ModeloCasilla",
    "ModeloClave",
    "ModeloInstruccion",
    "ModeloNormativa",
    "ModeloCampana",
    "DoctrinaRelacionada",
    "DoctrinaViaArticulo",
    "HTTPValidationError",
    "ValidationError",
}

# Override descriptions for GPT clarity
OPERATION_OVERRIDES = {
    "buscar_legislacion": {
        "summary": "Search Spanish legislation by text",
        "description": (
            "Search consolidated Spanish laws (LIVA, LIRPF, LIS, etc.) by keyword. "
            "Returns matching articles with snippets and relevance scores. "
            "Filter by norma (e.g. LIVA, LIRPF), ambito, tipo, fuente, or vigencia."
        ),
    },
    "get_norma": {
        "summary": "Get law details",
        "description": (
            "Get metadata for a Spanish law by code (e.g. LIVA, LIRPF, LIS). "
            "Returns title, jurisdiction, document type, and coverage status."
        ),
    },
    "get_articulo": {
        "summary": "Get article text",
        "description": (
            "Get the full text of a specific article from a law. "
            "Optionally filter by vigencia_en (YYYY-MM-DD) for historical versions. "
            "Returns the article text, validity dates, and confidence info."
        ),
    },
    "buscar_doctrina": {
        "summary": "Search interpretative doctrine",
        "description": (
            "Search interpretative doctrine from DGT (binding queries) or TEAC (resolutions). "
            "Returns doctrine documents with linked articles and confidence scores. "
            "Filter by tipo (consulta_vinculante, resolucion_teac), organismo_emisor, or fecha."
        ),
    },
    "get_doctrina": {
        "summary": "Get doctrine document",
        "description": (
            "Get a specific doctrine document by reference (e.g. V0000-26, 00/1234/2024). "
            "Returns full text, linked articles, and confidence information."
        ),
    },
    "list_modelos": {
        "summary": "List AEAT tax models",
        "description": (
            "List all AEAT tax form models (100, 303, 111, etc.) with their "
            "linked article counts and active campaign box counts."
        ),
    },
    "get_modelo": {
        "summary": "Get AEAT model details",
        "description": (
            "Get full details for a specific AEAT tax model including linked legislation articles, "
            "active campaign boxes (casillas), key codes (claves), step-by-step instructions, "
            "regulatory framework (normativa), and related doctrine."
        ),
    },
}


def _downgrade_to_30(spec: dict) -> dict:
    """Best-effort downgrade from OpenAPI 3.1.x to 3.0.3."""
    spec["openapi"] = "3.0.3"

    def _clean_schema(schema):
        """Remove 3.1-only keys and convert type lists to first type."""
        if not isinstance(schema, dict):
            return
        # Remove 3.1 exclusiveMinimum/exclusiveMaximum (move to minimum with adjustment)
        for key in list(schema.keys()):
            if key == "const":
                schema["enum"] = [schema.pop("const")]
            if key == "$defs":
                schema.pop("$defs")
        # Recurse
        for v in schema.values():
            if isinstance(v, dict):
                _clean_schema(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _clean_schema(item)

    for comp_name, comp_schema in spec.get("components", {}).get("schemas", {}).items():
        _clean_schema(comp_schema)

    return spec


def _iter_refs(node):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for value in node.values():
            yield from _iter_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_refs(item)


def _collect_schema_refs(node, all_schemas: dict) -> set[str]:
    pending = []
    seen = set()
    for ref in _iter_refs(node):
        prefix = "#/components/schemas/"
        if ref.startswith(prefix):
            pending.append(ref[len(prefix) :])

    while pending:
        name = pending.pop()
        if name in seen or name not in all_schemas:
            continue
        seen.add(name)
        for ref in _iter_refs(all_schemas[name]):
            prefix = "#/components/schemas/"
            if ref.startswith(prefix):
                pending.append(ref[len(prefix) :])

    return seen


def _simplify_for_gpt(node):
    if isinstance(node, dict):
        if "anyOf" in node:
            variants = node["anyOf"]
            if isinstance(variants, list):
                non_null = [
                    item
                    for item in variants
                    if not (isinstance(item, dict) and item.get("type") == "null")
                ]
                if len(non_null) == 1:
                    replacement = deepcopy(non_null[0])
                    for key, value in list(node.items()):
                        if key != "anyOf" and key not in replacement:
                            replacement[key] = value
                    node.clear()
                    node.update(replacement)

        if node.get("type") == ["string", "null"]:
            node["type"] = "string"

        for key, value in list(node.items()):
            if key == "responses" and isinstance(value, dict):
                value.pop("422", None)
            else:
                _simplify_for_gpt(value)
    elif isinstance(node, list):
        for item in node:
            _simplify_for_gpt(item)


def export(openapi_version: str | None = None, output_path: str | None = None):
    spec = app.openapi()

    # Filter paths
    filtered_paths = {}
    for path, methods in spec.get("paths", {}).items():
        if path in INCLUDE_PATHS:
            filtered_methods = {}
            for method, op in methods.items():
                op = deepcopy(op)
                op_id = op.get("operationId", "")
                if op_id in OPERATION_OVERRIDES:
                    override = OPERATION_OVERRIDES[op_id]
                    if "summary" in override:
                        op["summary"] = override["summary"]
                    if "description" in override:
                        op["description"] = override["description"]
                filtered_methods[method] = op
            filtered_paths[path] = filtered_methods

    all_schemas = spec.get("components", {}).get("schemas", {})
    referenced_schemas = _collect_schema_refs(filtered_paths, all_schemas)
    filtered_schema_names = INCLUDE_SCHEMAS | referenced_schemas
    filtered_schemas = {}
    for name, schema in all_schemas.items():
        if name in filtered_schema_names:
            filtered_schemas[name] = deepcopy(schema)

    # Build final spec
    curated = {
        "openapi": openapi_version or spec.get("openapi", "3.1.0"),
        "info": spec.get("info", {}),
        "servers": [
            {
                "url": "https://api.desuscribir.es",
                "description": "Production API",
            }
        ],
        "paths": filtered_paths,
        "components": {
            "schemas": filtered_schemas,
        },
    }

    _simplify_for_gpt(curated)

    if openapi_version and openapi_version.startswith("3.0"):
        curated = _downgrade_to_30(curated)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(curated, f, indent=2, ensure_ascii=False)
        print(f"Written {output_path} ({curated['openapi']})")
        print(
            f"  {len(curated['paths'])} paths, {len(curated['components']['schemas'])} schemas"
        )
    else:
        print(json.dumps(curated, indent=2, ensure_ascii=False))

    return curated


def main():
    parser = argparse.ArgumentParser(
        description="Export curated OpenAPI spec for GPT Actions"
    )
    parser.add_argument("--openapi", default=None, help="OpenAPI version (e.g. 3.0.3)")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()
    export(openapi_version=args.openapi, output_path=args.output)


if __name__ == "__main__":
    main()
