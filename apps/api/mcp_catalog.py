from __future__ import annotations

from typing import Any


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
]


def get_stdio_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "consulta_fiscal",
            "description": "Consulta fiscal inteligente en lenguaje natural.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "sujeto": {"type": "string"},
                    "pais": {"type": "string"},
                    "tipo_operacion": {"type": "string"},
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
            "description": "Consulta guiada para el agente operativo.",
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
