from __future__ import annotations

from typing import Any

DEFAULT_MCP_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "description": (
        "JSON object returned by the underlying ESData read-only endpoint. "
        "Tool calls may serialize this object in text content depending on transport."
    ),
}

DEFAULT_MCP_READ_ONLY_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    # Every retrieval is semantically read-only, but audit logging means repeated
    # calls are not strictly side-effect-free at infrastructure level.
    "idempotentHint": False,
    "openWorldHint": False,
}


HTTP_MCP_OPERATIONS = [
    # Legislacion
    "list_legislacion",
    "get_norma",
    "list_articulos",
    "get_articulo",
    "get_articulo_historial",
    "buscar",
    "buscar_legislacion",
    # Materias
    "list_materias",
    "get_materia",
    # Doctrina
    "buscar_doctrina",
    "get_doctrina",
    # Modelos AEAT
    "list_modelos",
    "list_modelos_campanas_operativas",
    "get_modelo",
    "get_modelo_articulos",
    "get_modelo_casillas",
    "get_modelo_claves",
    "get_modelo_instrucciones",
    "get_modelo_normativa",
    "get_modelo_artefactos",
    "get_modelo_campana_operativa",
    "get_modelo_resumen_operativo",
    "get_modelo_fuentes_oficiales",
    "list_modelos_por_supuesto",
    # Disponibilidad de dominios/tablas
    "list_domain_availability",
    "get_domain_availability",
    # Fuentes oficiales no-AEAT expuestas para consulta directa
    "listar_borme",
    "get_borme",
    "listar_boe_diario",
    "get_boe_diario",
    "listar_cnmv",
    "get_cnmv",
    "get_cnmv_versions",
    "get_cnmv_regulation_links",
    "get_cnmv_obligation_links",
    "listar_eurlex",
    "get_eurlex",
    "listar_obligaciones_internacionales",
    "detalle_obligacion_internacional",
    "listar_registros_giin",
    "detalle_registro_giin",
    "listar_normas_irs",
    "listar_formularios_w8",
    "listar_referencias_tin",
    "list_casp",
    "get_casp",
    "list_psd2_aspsp",
    "get_psd2_aspsp",
    "list_psd2_aisp",
    "get_psd2_aisp",
    "list_psd2_pisp",
    "get_psd2_pisp",
    "list_sepa_payment_rules",
    "get_sepa_payment_rule",
    "screening_entries",
    # DTA / Convenios Doble Imposicion
    "listar_convenios_dta_internacional",
    "detalle_convenio_dta_internacional",
    "listar_reglas_retencion_internacional",
    "calcular_retencion",
    # Bridged from stdio — tools that previously only worked via MCP stdio
    # transport are now callable via HTTP MCP too. Each maps to an existing
    # REST endpoint that the stdio handler already delegates to.
    "consulta_fiscal",                 # GET /v1/consulta
    "listar_obligaciones_operativas",  # GET /v1/obligaciones/operativas
    "listar_deadlines",                # GET /v1/obligaciones/deadlines
    "listar_obligaciones_aplicables",  # GET /v1/obligaciones/aplicables
    "get_obligacion",                  # GET /v1/obligaciones/{codigo}
    "listar_workflow_compliance",      # GET /v1/compliance/workflow
    # Note: agente_monitoreo_status remains stdio-only — it reads from
    # `agent_monitor.get_monitor_status()`, a Python-internal function without
    # a corresponding REST endpoint. Creating one is tracked in backlog.
]


def infer_query_audit_tool_name(path: str) -> str:
    """Map a router path to a tool name for audit logging."""
    if path.startswith("/mcp/tools/"):
        return path.split("/mcp/tools/")[-1] or "unknown"
    if path.startswith("/v1/consulta"):
        return "consulta_fiscal"
    if path.startswith("/v1/obligaciones/aplicables"):
        return "listar_obligaciones_aplicables"
    if path.startswith("/v1/obligaciones/deadlines"):
        return "listar_deadlines"
    if path.startswith("/v1/obligaciones/operativas"):
        return "listar_obligaciones_operativas"
    if path.startswith("/v1/obligaciones/"):
        return "get_obligacion"
    if path.startswith("/v1/legislacion/buscar"):
        return "buscar"
    if path.startswith("/v1/legislacion/"):
        return "list_legislacion"
    if path.startswith("/v1/modelos/"):
        return "list_modelos"
    if path.startswith("/v1/doctrina/"):
        return "buscar_doctrina"
    if path.startswith("/v1/domain-availability"):
        return "list_domain_availability"
    if path.startswith("/v1/borme"):
        return "listar_borme"
    if path.startswith("/v1/boe-diario"):
        return "listar_boe_diario"
    if path.startswith("/v1/cnmv"):
        return "listar_cnmv"
    if path.startswith("/v1/eurlex"):
        return "listar_eurlex"
    if path.startswith("/v1/internacional/obligaciones"):
        return "listar_obligaciones_internacionales"
    if path.startswith("/v1/irs-fiscal/giin"):
        return "listar_registros_giin"
    if path.startswith("/v1/irs-fiscal"):
        return "listar_normas_irs"
    if path.startswith("/v1/mica/casp"):
        return "list_casp"
    if path.startswith("/v1/psd2"):
        return "list_psd2_aspsp"
    if path.startswith("/v1/screening/entries"):
        return "screening_entries"
    return "http_request"


def enrich_dict_tool_contract(tool: dict[str, Any]) -> dict[str, Any]:
    """Add MCP contract metadata to a dict-based tool definition."""
    enriched = dict(tool)
    enriched.setdefault("outputSchema", DEFAULT_MCP_OUTPUT_SCHEMA)
    annotations = dict(DEFAULT_MCP_READ_ONLY_ANNOTATIONS)
    annotations.update(enriched.get("annotations") or {})
    enriched["annotations"] = annotations
    return enriched


def enrich_stdio_tool_contract(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add output schema and read-only annotations to stdio tool definitions."""
    return [enrich_dict_tool_contract(tool) for tool in tools]


def apply_http_tool_contract(tools: list[Any]) -> None:
    """Mutate FastApiMCP Tool objects with ESData's read-only contract."""
    from mcp import types

    annotations = types.ToolAnnotations(**DEFAULT_MCP_READ_ONLY_ANNOTATIONS)
    for tool in tools:
        if getattr(tool, "outputSchema", None) is None:
            tool.outputSchema = DEFAULT_MCP_OUTPUT_SCHEMA
        if getattr(tool, "annotations", None) is None:
            tool.annotations = annotations


def get_stdio_tool_definitions() -> list[dict[str, Any]]:
    return enrich_stdio_tool_contract([
        {
            "name": "consulta_fiscal",
            "description": (
                "Consulta fiscal/legal grounded sobre fuentes ESData. Usar solo la evidencia, "
                "citas y metadatos devueltos; si review_required/verified=false, abstenerse "
                "de afirmar obligatoriedad o certeza. No usar conocimiento externo."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "sujeto": {"type": "string"},
                    "pais": {"type": "string"},
                    "tipo_operacion": {"type": "string"},
                    "vigente_en": {"type": "string", "description": "Fecha YYYY-MM-DD para consulta temporal."},
                    "sources": {"type": "string", "description": "Fuentes separadas por coma cuando se quiera limitar retrieval."},
                    "hybrid_weight": {"type": "number", "description": "Peso del ranking hibrido si se usan sources."},
                },
                "required": ["q"],
            },
        },
        {
            "name": "listar_obligaciones_operativas",
            "description": "Lista obligaciones operativas estructuradas.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ambito": {"type": "string"},
                    "frecuencia": {"type": "string"},
                    "con_sancion": {"type": "boolean"},
                    "limite": {"type": "integer"},
                },
                "required": [],
            },
        },
        {
            "name": "listar_deadlines",
            "description": "Lista obligaciones proximas a vencer.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dias_proximo": {"type": "integer"},
                    "frecuencia": {"type": "string"},
                },
                "required": [],
            },
        },
        {
            "name": "listar_obligaciones_aplicables",
            "description": "Lista obligaciones aplicables segun perfil de entidad.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tipo_entidad": {"type": "string"},
                    "reporting_reservado": {"type": "boolean"},
                    "aml_cft_reforzado": {"type": "boolean"},
                    "cross_border_ue": {"type": "boolean"},
                    "limite": {
                        "type": "integer",
                        "description": "Maximo de obligaciones devueltas (1-200).",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset para continuar una pagina previa.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_obligacion_completa",
            "description": "Obtiene detalle completo de una obligacion.",
            "inputSchema": {
                "type": "object",
                "properties": {"codigo": {"type": "string"}},
                "required": ["codigo"],
            },
        },
        {
            "name": "agente_consulta",
            "description": (
                "Wrapper stdio para consultas de agente con contexto de entidad regulada; "
                "mapea tipo_entidad a sujeto y llama a consulta_fiscal. Responder solo con "
                "evidencia devuelta por ESData y respetar verified/review_required."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "sujeto": {"type": "string"},
                    "tipo_entidad": {
                        "type": "string",
                        "enum": [
                            "sociedad_valores",
                            "retenedor",
                            "no_residente",
                            "entidad_dinero_electronico",
                        ],
                    },
                },
                "required": ["q"],
            },
        },
        {
            "name": "list_modelos_por_supuesto",
            "description": (
                "Clasifica modelos AEAT candidatos por supuesto fiscal. "
                "No afirma obligatoriedad sin evidencia explicita; clasificacion candidato "
                "o requiere_verificacion exige revision y no permite decir 'debe presentar'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tipo_entidad": {"type": "string"},
                    "clientes_residentes": {"type": "boolean"},
                    "clientes_no_residentes": {"type": "boolean"},
                    "tipo_renta": {"type": "string"},
                    "tipo_operacion": {"type": "string"},
                    "incluir_obligacion_sociedad": {"type": "boolean"},
                },
                "required": ["tipo_entidad"],
            },
        },
        {
            "name": "agente_monitoreo_status",
            "description": "Devuelve el estado del monitor de cambios regulatorios.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "agente_compliance_resumen",
            "description": "Resume workflows de compliance pendientes o filtrados.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "estado": {"type": "string"},
                    "limite": {"type": "integer"},
                },
                "required": [],
            },
        },
    ])
