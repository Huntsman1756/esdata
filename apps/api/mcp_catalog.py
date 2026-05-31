from __future__ import annotations

from typing import Any

from mcp_tools_aeat_catalogo import AEAT_CATALOGO_MCP_TOOL_CONTRACTS
from mcp_tools_eu import EU_MCP_TOOL_CONTRACTS
from mcp_tools_perfil import PERFIL_MCP_TOOL_CONTRACTS

MCP_TOOL_ROUTING_POLICY = """
POLITICA DE SELECCION DE HERRAMIENTAS ESDATA:

1. Para obligaciones de una entidad supervisada → SIEMPRE obtener_obligaciones_perfil
   Si el modelo no aparece en la respuesta: NO tiene obligacion verificada.
   NO buscar en catalogo AEAT como alternativa.
   NO suplementar con buscar_modelos_aeat_catalogo.

2. Para que presentar en un trimestre/mes/periodo → SIEMPRE calendario_obligaciones_perfil
   Usar parametro quarter (ej: "2026-Q3") para filtrar por periodo.
   Trigger: "este trimestre", "Q3", "qué vence", "agenda", "este mes",
   "qué presento en julio/octubre/enero/abril".
   NO usar busqueda semantica ni catalogo para responder preguntas de calendario.

3. Para informacion sobre un modelo AEAT (que es, como se rellena) → buscar_modelos_aeat_catalogo
   Esta herramienta NO indica obligatoriedad. Solo describe el formulario.
   NO combinar su resultado con obligaciones de perfil sin separacion explicita.

4. Para normas UE (MiFIR, EMIR, DORA, CRR, UCITS, MiCA) → buscar_norma_eu

5. Para listar tipos de entidad → listar_perfiles_entidad

6. Para circulares CNMV, guias tecnicas o modelos ESI aplicables a un perfil
   -> obtener_documentos_cnmv_perfil
   Trigger: "que circulares aplican", "guias tecnicas CNMV",
   "modelos normalizados ESI", "supervision CNMV".
   NO usar obtener_obligaciones_perfil para documentos supervisores.

7. Para CASP, criptoactivos, MiCA, activos virtuales, exchange cripto, wallet, PSAV:
   -> usar obtener_obligaciones_perfil con perfil_codigo='casp'.
   Para emisores de ART o EMT, white paper de criptoactivos, ficha referenciada,
   ficha de dinero electronico o token emisor:
   -> usar obtener_obligaciones_perfil con perfil_codigo='emisor_token'.
   Las tablas de token/wallet/white-paper pueden estar vacias y esto es esperado.
   AVISO: corpus documental supervisor ART/EMT vacio; obtener_documentos_cnmv_perfil('emisor_token')
   puede devolver 0 documentos y esto es esperado, no es un error.
   Responder siempre desde obtener_obligaciones_perfil e identificar gaps explicitamente.
   NO inventar obligaciones cripto no verificadas.
   Trigger: "casp", "criptoactivos", "MiCA", "activos virtuales", "exchange cripto",
   "wallet", "PSAV", "crypto", "token", "blockchain", "ART", "EMT",
   "white paper", "ficha referenciada", "ficha de dinero electronico", "token emisor".

REGLA DE ORO: si obtener_obligaciones_perfil no devuelve un modelo,
la respuesta correcta es "no consta como obligacion verificada para este perfil",
no "lo busco en otro sitio".

REGLA DE VERIFICABILIDAD: una respuesta accionable debe citar las fuentes que
permiten comprobarla dentro del propio JSON devuelto por ESData. Usar
source_url, source_hash, cited_chunks, claim_citations y
result_metadata.source_verification. Si no hay fuente verificable, la respuesta
debe tratarse como evidencia limitada aunque haya resultados, y no debe
presentarse como conclusion fiscal/legal segura.
"""

DEFAULT_MCP_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "description": (
        "JSON object returned by the underlying ESData read-only endpoint. "
        "Tool calls may serialize this object in text content depending on transport. "
        "Actionable answers must expose verifiable source URLs or hashes in the "
        "payload; otherwise safe_to_answer must be false or the client must abstain."
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
    "listar_lineas_criterio",
    "detalle_linea_criterio",
    "buscar_lineas_criterio",
    "detalle_linea_criterio_doctrina",
    "criterio_relacionado_con_modelo",
    "doctrina_coverage",
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
    "buscar_modelos_aeat_catalogo",
    # Disponibilidad de dominios/tablas
    "list_domain_availability",
    "get_domain_availability",
    # Fuentes oficiales no-AEAT expuestas para consulta directa
    "listar_borme",
    "get_borme",
    "listar_boe_diario",
    "get_boe_diario",
    "listar_aepd",
    "buscar_aepd",
    "get_aepd",
    "listar_bde",
    "get_bde",
    "listar_bdns",
    "get_bdns",
    "listar_cendoj",
    "get_cendoj",
    "listar_cnmv",
    "buscar_cnmv",
    "obtener_documentos_cnmv_perfil",
    "get_cnmv",
    "get_cnmv_versions",
    "get_cnmv_regulation_links",
    "get_cnmv_obligation_links",
    "listar_eurlex",
    "get_eurlex",
    "listar_sepblac",
    "get_sepblac",
    "listar_obligaciones_internacionales",
    "detalle_obligacion_internacional",
    "listar_registros_giin",
    "detalle_registro_giin",
    "listar_normas_irs",
    "listar_formularios_w8",
    "listar_referencias_tin",
    "list_casp",
    "buscar_casp",
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
    # Aplicabilidad por perfil
    "listar_perfiles_entidad",
    "get_perfil_entidad",
    "obtener_obligaciones_perfil",
    "calendario_obligaciones_perfil",
    "buscar_norma_eu",
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
    if path.startswith("/v1/doctrina/lineas/coverage"):
        return "doctrina_coverage"
    if path.startswith("/v1/doctrina/lineas/") and path.endswith("/relaciones"):
        return "criterio_relacionado_con_modelo"
    if path.startswith("/v1/doctrina/lineas/"):
        return "detalle_linea_criterio_doctrina"
    if path.startswith("/v1/doctrina/lineas"):
        return "buscar_lineas_criterio"
    if path.startswith("/v1/doctrina/"):
        return "buscar_doctrina"
    if path.startswith("/v1/criterio/"):
        return "detalle_linea_criterio"
    if path.startswith("/v1/criterio"):
        return "listar_lineas_criterio"
    if path.startswith("/v1/domain-availability"):
        return "list_domain_availability"
    if path.startswith("/v1/borme"):
        return "listar_borme"
    if path.startswith("/v1/boe-diario"):
        return "listar_boe_diario"
    if path.startswith("/v1/aepd/buscar"):
        return "buscar_aepd"
    if path.startswith("/v1/aepd/"):
        return "get_aepd"
    if path.startswith("/v1/aepd"):
        return "listar_aepd"
    if path.startswith("/v1/bde/"):
        return "get_bde"
    if path.startswith("/v1/bde"):
        return "listar_bde"
    if path.startswith("/v1/bdns/"):
        return "get_bdns"
    if path.startswith("/v1/bdns"):
        return "listar_bdns"
    if path.startswith("/v1/cendoj/"):
        return "get_cendoj"
    if path.startswith("/v1/cendoj"):
        return "listar_cendoj"
    if path.startswith("/v1/cnmv/perfil"):
        return "obtener_documentos_cnmv_perfil"
    if path.startswith("/v1/cnmv"):
        return "listar_cnmv"
    if path.startswith("/v1/eurlex"):
        return "listar_eurlex"
    if path.startswith("/v1/sepblac/"):
        return "get_sepblac"
    if path.startswith("/v1/sepblac"):
        return "listar_sepblac"
    if path.startswith("/v1/internacional/obligaciones"):
        return "listar_obligaciones_internacionales"
    if path.startswith("/v1/irs-fiscal/giin"):
        return "listar_registros_giin"
    if path.startswith("/v1/irs-fiscal"):
        return "listar_normas_irs"
    if path.startswith("/v1/mica/registers"):
        return "list_mica_register_entries"
    if path.startswith("/v1/mica/casp/buscar"):
        return "buscar_casp"
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
    tool_definitions = [
        {
            "name": "consulta_fiscal",
            "description": (
                "Consulta fiscal/legal grounded sobre fuentes ESData. Usar solo la evidencia, "
                "citas y metadatos devueltos; si review_required/verified=false, abstenerse "
                "de afirmar obligatoriedad o certeza. Toda conclusion accionable debe poder "
                "verificarse en source_url, source_hash, cited_chunks, claim_citations o "
                "result_metadata.source_verification. No usar conocimiento externo."
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
            "description": "Obtiene el detalle disponible de una obligacion.",
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
                "evidencia devuelta por ESData, citar las fuentes verificables y respetar "
                "verified/review_required."
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
            "name": "obtener_documentos_cnmv_perfil",
            "description": (
                "Devuelve documentos CNMV (circulares, guias tecnicas, modelos "
                "normalizados ESI, normativa) aplicables a un perfil de entidad. "
                "Usar cuando el usuario pregunta que circulares CNMV aplican a una "
                "sociedad de valores, que guias tecnicas debe seguir una agencia de "
                "valores, o que modelos normalizados CNMV existen para un tipo de "
                "entidad. NO usar para obtener obligaciones de perfil (usar "
                "obtener_obligaciones_perfil). Este endpoint devuelve documentos "
                "supervisores, no obligaciones legales verificadas.\n\n"
                f"{MCP_TOOL_ROUTING_POLICY}"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "perfil_codigo": {"type": "string"},
                    "tipo_documento": {"type": "string"},
                    "vigente": {"type": "boolean", "default": True},
                },
                "required": ["perfil_codigo"],
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
    ]
    for contract in (
        *PERFIL_MCP_TOOL_CONTRACTS,
        *EU_MCP_TOOL_CONTRACTS,
        *AEAT_CATALOGO_MCP_TOOL_CONTRACTS,
    ):
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter_name, parameter_contract in contract.parameters.items():
            properties[parameter_name] = {
                key: value
                for key, value in parameter_contract.items()
                if key not in {"required", "default"}
            }
            if "default" in parameter_contract:
                properties[parameter_name]["default"] = parameter_contract["default"]
            if parameter_contract.get("required"):
                required.append(parameter_name)
        description = contract.description
        if contract.name in {
            "obtener_obligaciones_perfil",
            "calendario_obligaciones_perfil",
        }:
            description = f"{description}\n\n{MCP_TOOL_ROUTING_POLICY}"
        tool_definitions.append(
            {
                "name": contract.name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return enrich_stdio_tool_contract(tool_definitions)
