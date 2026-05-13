#!/usr/bin/env python
"""Export a curated OpenAPI spec for Custom GPT Actions.

Produces a spec containing only the endpoints relevant for GPT Actions,
with clean descriptions and (optionally) OpenAPI 3.0.x compatibility.

Usage:
    python scripts/ops/export-gpt-openapi.py                  # default: 3.1.0
    python scripts/ops/export-gpt-openapi.py --openapi 3.0.3  # force 3.0.x
    python scripts/ops/export-gpt-openapi.py --output docs/openapi-gpt.json
    python scripts/ops/export-gpt-openapi.py --profile actions30 --output docs/openapi-gpt-actions-30.json
"""

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

# Allow importing from apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from main import app
from mcp_catalog import HTTP_MCP_OPERATIONS

# ---------------------------------------------------------------------------
# Curated list of paths to expose to the GPT
# ---------------------------------------------------------------------------
INCLUDE_PATHS = {
    "/status",
    "/v1/consulta",
    "/v1/domain-availability",
    "/v1/domain-availability/{table}",
    "/v1/sources/freshness",
    "/v1/legislacion/buscar",
    "/v1/legislacion/{codigo}",
    "/v1/legislacion/{codigo}/articulos/{numero}",
    "/v1/doctrina/buscar",
    "/v1/doctrina/{referencia}",
    "/v1/boe-diario",
    "/v1/boe-diario/{referencia}",
    "/v1/aepd",
    "/v1/aepd/buscar",
    "/v1/aepd/{referencia}",
    "/v1/cnmv/buscar",
    "/v1/cnmv/{referencia}",
    "/v1/mica/casp/buscar",
    "/v1/modelos",
    "/v1/modelos/{codigo}",
    "/v1/modelos/{codigo}/casillas",
    "/v1/modelos/por-supuesto",
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
    "ModeloCasillasResponse",
    "ModeloClave",
    "ModeloInstruccion",
    "ModeloNormativa",
    "ModeloCampana",
    "DoctrinaRelacionada",
    "DoctrinaViaArticulo",
    "BOEDiarioListResponse",
    "BOEDiarioListItem",
    "BOEDiarioDetail",
    "DocInterpretativoListResponse",
    "DocInterpretativoListItem",
    "DocInterpretativoDetail",
    "CASPListResponse",
    "CASPSummary",
    "HTTPValidationError",
    "ValidationError",
}

# Override descriptions for GPT clarity
OPERATION_OVERRIDES = {
    "status_status_get": {
        "summary": "Get API operational status",
        "description": (
            "Return API runtime status and operational metadata. Use this before relying "
            "on tax or legal answers if the integration needs to verify service health."
        ),
    },
    "consulta_fiscal": {
        "summary": "Ask a grounded Spanish tax/legal query",
        "description": (
            "Run a grounded ESData fiscal/legal retrieval query. Responses must be treated "
            "according to their confidence, relevance, citations, and review_required fields. "
            "Do not infer mandatory obligations when the response only returns low-relevance "
            "candidates or explicitly requires verification."
        ),
    },
    "list_domain_availability": {
        "summary": "List data availability by domain/table",
        "description": (
            "List ESData domain availability statuses, including workflow_empty, allowed_empty, "
            "configured_but_unavailable, and populated domains. Use this to explain explicitly "
            "when a domain has no current data instead of inventing an answer."
        ),
    },
    "get_domain_availability": {
        "summary": "Get one table/domain availability status",
        "description": (
            "Return the availability status for a specific ESData table or domain. Use this "
            "when a query depends on a table that may be empty, unavailable, or intentionally "
            "allowed to be empty."
        ),
    },
    "source_freshness_v1_sources_freshness_get": {
        "summary": "Check source freshness",
        "description": (
            "Return freshness and ingestion status for official source families. Use this "
            "before answering currency-sensitive questions about tax models, deadlines, "
            "legislation, doctrine, or regulatory updates."
        ),
    },
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
    "listar_aepd": {
        "summary": "List AEPD documents",
        "description": (
            "List official AEPD documents loaded by ESData. Responses include `items`, "
            "`total`, `url_aepd`, and pagination metadata. Do not treat missing "
            "sanctioning resolutions as loaded unless the response explicitly returns them."
        ),
    },
    "buscar_aepd": {
        "summary": "Search AEPD documents",
        "description": (
            "Search official AEPD documents by title or text. Use `url_aepd`/`url_fuente` "
            "as the cited official source and do not mix these guidance/document results "
            "with consolidated BOE legal articles."
        ),
    },
    "get_aepd": {
        "summary": "Get AEPD document detail",
        "description": "Return full text and official AEPD source URL for a loaded AEPD document.",
    },
    "buscar_casp": {
        "summary": "Search ESMA MiCA CASP register",
        "description": (
            "Search the loaded ESMA MiCA Crypto-Asset Service Providers register by "
            "provider name or registration number. Treat results as authoritative only "
            "when quality_signal is official_esma_register and availability_status is populated. "
            "If safe_to_answer is false, do not infer that a provider is absent from the real register."
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
            "Get details for a specific AEAT tax model including linked legislation articles, "
            "a paginated page of active campaign boxes (casillas), key codes (claves), "
            "step-by-step instructions, regulatory framework (normativa), and related doctrine. "
            "Use casillas_limit/casillas_offset or /v1/modelos/{codigo}/casillas when all boxes are needed. "
            "Use related_limit and articulos_offset for bounded related lists, and continue only when "
            "the returned metadata indicates more results."
        ),
    },
    "get_modelo_casillas": {
        "summary": "Get paginated AEAT model boxes",
        "description": (
            "Return a paginated list of official boxes/fields for an AEAT model campaign. "
            "Use limit/offset and continue only when has_more is true. A returned box "
            "confirms that the field exists in the model/campaign; it does not prove the "
            "box is mandatory for a concrete taxpayer scenario."
        ),
    },
    "list_modelos_por_supuesto": {
        "summary": "Classify AEAT model candidates for a fiscal scenario",
        "description": (
            "Return AEAT model candidates for a described fiscal scenario. Classifications are "
            "confirmed, candidate, or requires verification based only on ESData evidence. "
            "Do not present a model as mandatory unless the response explicitly supports that "
            "claim and the confidence/review fields allow it."
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
                else:
                    variant_types = {
                        item.get("type")
                        for item in non_null
                        if isinstance(item, dict) and isinstance(item.get("type"), str)
                    }
                    preserved = {
                        key: value
                        for key, value in node.items()
                        if key not in {"anyOf", "oneOf", "allOf"}
                    }
                    if "object" in variant_types:
                        preserved.setdefault("type", "object")
                        preserved.setdefault("additionalProperties", True)
                    elif "array" in variant_types:
                        preserved.setdefault("type", "array")
                        preserved.setdefault("items", {"type": "string"})
                    else:
                        preserved.setdefault("type", "string")
                    node.clear()
                    node.update(preserved)

        if node.get("type") == ["string", "null"]:
            node["type"] = "string"
        if node.get("type") == "null":
            node["type"] = "string"

        for key, value in list(node.items()):
            if key == "responses" and isinstance(value, dict):
                value.pop("422", None)
            else:
                _simplify_for_gpt(value)
    elif isinstance(node, list):
        for item in node:
            _simplify_for_gpt(item)


def export(
    openapi_version: str | None = None,
    output_path: str | None = None,
    profile: str = "full",
):
    spec = app.openapi()
    if profile not in {"full", "actions30"}:
        raise ValueError(f"Unsupported GPT OpenAPI profile: {profile}")

    included_operation_ids = set(HTTP_MCP_OPERATIONS) if profile == "full" else set()

    # Filter paths
    filtered_paths = {}
    for path, methods in spec.get("paths", {}).items():
        filtered_methods = {}
        for method, op in methods.items():
            op_id = op.get("operationId", "")
            if path not in INCLUDE_PATHS and op_id not in included_operation_ids:
                continue
            op = deepcopy(op)
            if op_id in OPERATION_OVERRIDES:
                override = OPERATION_OVERRIDES[op_id]
                if "summary" in override:
                    op["summary"] = override["summary"]
                if "description" in override:
                    op["description"] = override["description"]
            filtered_methods[method] = op
        if filtered_methods:
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
        "security": [
            {
                "ApiKeyAuth": [],
            }
        ],
        "components": {
            "schemas": filtered_schemas,
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "Dedicated ESData API key for GPT Actions.",
                }
            },
        },
    }

    _simplify_for_gpt(curated)

    if openapi_version and openapi_version.startswith("3.0"):
        curated = _downgrade_to_30(curated)

    operation_count = sum(len(methods) for methods in curated["paths"].values())
    if profile == "actions30" and operation_count > 30:
        raise RuntimeError(
            f"actions30 profile exported {operation_count} operations; maximum is 30"
        )

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(curated, f, indent=2, ensure_ascii=False)
        print(f"Written {output_path} ({curated['openapi']})")
        print(
            f"  {len(curated['paths'])} paths, {operation_count} operations, "
            f"{len(curated['components']['schemas'])} schemas"
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
    parser.add_argument(
        "--profile",
        choices=["full", "actions30"],
        default="full",
        help="Export profile: full MCP HTTP projection or <=30-operation GPT Actions core",
    )
    args = parser.parse_args()
    export(openapi_version=args.openapi, output_path=args.output, profile=args.profile)


if __name__ == "__main__":
    main()
