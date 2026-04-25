"""Shared MCP tool catalog — single source of truth for stdio and HTTP transports."""

from __future__ import annotations

from typing import Any


def get_stdio_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "consulta_fiscal",
            "description": (
                "Consulta fiscal inteligente en lenguaje natural. Responde preguntas sobre modelos AEAT, "
                "obligaciones fiscales, plazos de presentación, normativa aplicable y doctrina DGT/TEAC. "
                "Ejemplos: 'necesito comunicar facta cliente EEUU', 'irpf dividendos', 'iva entregas intracomunitarias', "
                "'retenciones no residente', 'modelo 216 como rellenar'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Pregunta fiscal en lenguaje natural (ej: 'facta no residente', 'irpf dividendos ue')",
                    },
                    "sujeto": {
                        "type": "string",
                        "enum": ["contribuyente", "no_residente", "empresa", "retenedor", "sociedad_contribuyente", "empresario_intracomunitario"],
                        "description": "Tipo de sujeto fiscal",
                    },
                    "pais": {
                        "type": "string",
                        "description": "País/territorio (ej: 'eeuu', 'ue', 'intracomunitario', 'fuera_ue')",
                    },
                    "tipo_operacion": {
                        "type": "string",
                        "description": "Tipo de operación (ej: 'entrega_bienes', 'prestacion_servicios', 'dividendos', 'retencion')",
                    },
                },
                "required": ["q"],
            },
        },
        {
            "name": "listar_obligaciones_operativas",
            "description": (
                "Listar obligaciones regulatorias con datos operativos estructurados: plazos, sanciones, "
                "triggers, frecuencia de presentación, canales. Devuelve datos accionables para el LLM "
                "en lugar de texto libre. Ejemplos de uso: 'qué sanciones aplica el modelo 349', "
                "'obligaciones CNMV para sociedad de valores', 'plazos presentación IVA trimestral'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ambito": {
                        "type": "string",
                        "description": "Filtrar por ámbito (ej: 'tributario_internacional', 'aml_cft_reporting', 'mercado_valores')",
                    },
                    "frecuencia": {
                        "type": "string",
                        "enum": ["mensual", "trimestral", "anual", "eventual"],
                        "description": "Filtrar por frecuencia de presentación",
                    },
                    "con_sancion": {
                        "type": "boolean",
                        "description": "Solo obligaciones con sanciones definidas",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de resultados (1-200)",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "listar_obligaciones_aplicables",
            "description": (
                "Listar obligaciones regulatorias aplicables a un perfil base de sociedad de valores. "
                "Sirve como primer paso de aplicabilidad regulatoria antes del workflow interno."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tipo_entidad": {
                        "type": "string",
                        "description": "Tipo de entidad regulada, por defecto sociedad_valores",
                    },
                    "reporting_reservado": {
                        "type": "boolean",
                        "description": "Si aplica reporting reservado CNMV",
                    },
                    "aml_cft_reforzado": {
                        "type": "boolean",
                        "description": "Si la entidad esta sujeta a obligaciones AML/CFT operativas",
                    },
                    "cross_border_ue": {
                        "type": "boolean",
                        "description": "Si presta servicios cross-border UE",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "listar_deadlines",
            "description": (
                "Listar obligaciones próximas a vencer o presentar. Devuelve obligaciones ordenadas "
                "por frecuencia, útil para responder 'qué tengo que presentar pronto' o 'plazos próximos'. "
                "No calcula fechas exactas (depende de la fecha actual), pero filtra por frecuencia y ordena."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dias_proximo": {
                        "type": "integer",
                        "description": "Mostrar obligaciones en los próximos N días (1-365)",
                    },
                    "frecuencia": {
                        "type": "string",
                        "enum": ["mensual", "trimestral", "anual"],
                        "description": "Filtrar por frecuencia",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_obligacion_completa",
            "description": (
                "Obtener detalle completo de una obligación regulatoria incluyendo datos operativos "
                "(plazos, sanciones, recargos, interés de demora, prescripción, depósito previo). "
                "Usar cuando se necesiten datos concretos de cumplimiento: multas, plazos, requisitos."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código de la obligación (ej: 'IRNR_FACTA', 'CNMV-IR-RESERVADA', 'SEPBLAC-INDICIO-M19')",
                    },
                },
                "required": ["codigo"],
            },
        },
        {
            "name": "agente_consulta",
            "description": (
                "Consulta fiscal/regulatoria con contexto de entidad obligada. "
                "Expande la consulta basandose en el tipo de entidad y devuelve "
                "modelos AEAT, obligaciones y normativa aplicable. "
                "Ejemplos: 'que obligaciones tengo como sociedad de valores', "
                "'modelo 349 sanciones para intracomunitario'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Pregunta en lenguaje natural",
                    },
                    "tipo_entidad": {
                        "type": "string",
                        "enum": ["sociedad_valores", "entidad_dinero_electronico", "retenedor", "no_residente"],
                        "description": "Tipo de entidad obligada (opcional, default: sociedad_valores)",
                    },
                },
                "required": ["q"],
            },
        },
        {
            "name": "agente_monitoreo_status",
            "description": (
                "Estado actual del servicio de monitoreo interno de cambios regulatorios. "
                "Devuelve si el monitor esta activo, ultimo escaneo, proximo escaneo, "
                "y configuracion actual. No requiere parametros."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "agente_compliance_resumen",
            "description": (
                "Resumen del workflow de compliance con estados y prioridades. "
                "Devuelve casos de workflow filtrados por estado y limite. "
                "Ejemplos: 'resumen de compliance', 'casos pendientes', 'alertas de alta prioridad'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "description": "Filtrar por estado del caso (ej: 'pendiente', 'en_revision', 'completado', 'urgente')",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Numero maximo de resultados (1-200, default: 20)",
                    },
                },
                "required": [],
            },
        },
    ]
