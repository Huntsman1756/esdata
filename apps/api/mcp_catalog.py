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
        {
            "name": "list_sfdr_products",
            "description": (
                "Listar productos de inversiòn SFDR (Sustainable Finance Disclosure Regulation). "
                "Filtra por tipo de artìculo (6, 8, 9), estado o busca por nombre. "
                "Ejemplos: 'productos Art. 8 sostenibles', 'fondos Art. 9 clima'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_type": {
                        "type": "string",
                        "enum": ["art-6", "art-8", "art-9", "other"],
                        "description": "Filtrar por tipo de artìculo SFDR",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado",
                    },
                    "search": {
                        "type": "string",
                        "description": "Buscar por nombre de producto",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_sfdr_product",
            "description": (
                "Obtener detalle completo de un producto SFDR por ID, incluyendo "
                "PACI agregado y distribuciòn por paìs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del producto SFDR",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_sfdr_pacai_indicators",
            "description": (
                "Listar indicadores PCAI (Principal Adverse Impact) SFDR Art. 4. "
                "Filtra por producto, còdigo o estado."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de producto",
                    },
                    "indicator_code": {
                        "type": "string",
                        "description": "Filtrar por còdigo del indicador",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_sfdr_pacai_indicator",
            "description": (
                "Obtener detalle de un indicador PCAI SFDR por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del indicador PCAI",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_sfdr_entity_paci",
            "description": (
                "Listar datos PCAI a nivel de entidad (SFDR Art. 4). "
                "Filtra por entidad, ano de reporte o estado."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                    "reporting_year": {
                        "type": "integer",
                        "description": "Filtrar por ano de reporte",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_sfdr_entity_paci",
            "description": (
                "Obtener detalle de PCAI entidad SFDR por ID, incluyendo "
                "desinversion sectorial descarbonizaciòn."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del registro PCAI entidad",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_sfdr_pre_contractual",
            "description": (
                "Listar documentos precontractuales SFDR (KID, PPI, prospectus). "
                "Filtra por producto, tipo o estado."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de producto",
                    },
                    "document_type": {
                        "type": "string",
                        "enum": ["KID", "PPI", "prospectus"],
                        "description": "Filtrar por tipo de documento",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_sfdr_pre_contractual",
            "description": (
                "Obtener detalle de un documento precontractual SFDR por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del documento precontractual",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_sfdr_annual_reports",
            "description": (
                "Listar informes anuales SFDR. Filtra por entidad, ano o estado."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                    "reporting_year": {
                        "type": "integer",
                        "description": "Filtrar por ano de reporte",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_sfdr_annual_report",
            "description": (
                "Obtener detalle de un informe anual SFDR por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del informe anual",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_csrd_entity_reports",
            "description": (
                "Listar informes de sostenibilidad de entidades (CSRD). "
                "Filtra por entidad, ano, estado de aseguramiento."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                    "reporting_year": {
                        "type": "integer",
                        "description": "Filtrar por ano de reporte",
                    },
                    "assurance_status": {
                        "type": "string",
                        "description": "Filtrar por estado de aseguramiento",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_csrd_entity_report",
            "description": (
                "Obtener detalle completo de un informe CSRD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del informe CSRD",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_csrd_esg_data_points",
            "description": (
                "Listar indicadores ESG (puntos de datos) de informes CSRD. "
                "Filtra por reporte, tema o còdigo."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de reporte",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Filtrar por tema (ej: 'emisiones', 'social', 'gobernanza')",
                    },
                    "indicator_code": {
                        "type": "string",
                        "description": "Filtrar por còdigo del indicador",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_csrd_esg_data_point",
            "description": (
                "Obtener detalle de un punto de datos ESG CSRD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del punto de datos ESG",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_csrd_ess",
            "description": (
                "Listar Estàndares Europeos de Informaciòn de Sostenibilidad (ESRS). "
                "Filtra por tema o ano de aplicaciòn."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Filtrar por tema (ej: 'EA-1', 'ES1', 'environmental')",
                    },
                    "applicable_from_year": {
                        "type": "integer",
                        "description": "Filtrar por ano de aplicaciòn",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_csrd_ess",
            "description": (
                "Obtener detalle de un estàndar ESRS CSRD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del estàndar ESRS",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_csrd_double_materiality",
            "description": (
                "Listar evaluaciones de doble materialidad CSRD. "
                "Filtra por entidad o fecha."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_csrd_double_materiality",
            "description": (
                "Obtener detalle de evaluaciòn de doble materialidad CSRD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID de la evaluaciòn",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_aifmd_funds",
            "description": (
                "Listar fondos AIFMD (Alternative Investment Fund). "
                "Filtra por tipo, estado o pais de origen."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fund_type": {
                        "type": "string",
                        "enum": ["alternative", "real-estate", "pfaf", "securitization"],
                        "description": "Filtrar por tipo de fondo",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive"],
                        "description": "Filtrar por estado",
                    },
                    "home_member_state": {
                        "type": "string",
                        "description": "Filtrar por pais de origen",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_aifmd_fund",
            "description": (
                "Obtener detalle completo de un fondo AIFMD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del fondo AIFMD",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_aifmd_regulatory_reports",
            "description": (
                "Listar informes regulatorios AIFMD. Filtra por fondo, tipo o periodo."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fund_id": {
                        "type": "integer",
                        "description": "Filtrar por ID del fondo",
                    },
                    "report_type": {
                        "type": "string",
                        "enum": ["annual", "semi-annual", "ad-hoc"],
                        "description": "Filtrar por tipo de informe",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_aifmd_regulatory_report",
            "description": (
                "Obtener detalle de un informe regulatorio AIFMD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del informe regulatorio",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_aifmd_liquidity_management",
            "description": (
                "Listar datos de gestiòn de liquidez AIFMD. "
                "Filtra por fondo o suspensiòn de canje."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fund_id": {
                        "type": "integer",
                        "description": "Filtrar por ID del fondo",
                    },
                    "redemption_suspended": {
                        "type": "boolean",
                        "description": "Solo fondos con canje suspendido",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_aifmd_liquidity_management",
            "description": (
                "Obtener detalle de gestiòn de liquidez AIFMD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del registro de liquidez",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_ucits_funds",
            "description": (
                "Listar fondos UCITS (Undertakings for Collective Investment in Transferable Securities). "
                "Filtra por compaòia gestora, estado o pais."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "management_company": {
                        "type": "string",
                        "description": "Filtrar por compaòia gestora",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive"],
                        "description": "Filtrar por estado",
                    },
                    "home_member_state": {
                        "type": "string",
                        "description": "Filtrar por pais de origen",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_ucits_fund",
            "description": (
                "Obtener detalle completo de un fondo UCITS por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del fondo UCITS",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_ucits_regulatory_reports",
            "description": (
                "Listar informes regulatorios UCITS. Filtra por fondo o tipo."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fund_id": {
                        "type": "integer",
                        "description": "Filtrar por ID del fondo",
                    },
                    "report_type": {
                        "type": "string",
                        "enum": ["annual", "semi-annual", "ad-hoc"],
                        "description": "Filtrar por tipo de informe",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_ucits_regulatory_report",
            "description": (
                "Obtener detalle de un informe regulatorio UCITS por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del informe regulatorio",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_crd_capital_positions",
            "description": (
                "Listar posiciones de capital CRD/CRR para entidades crediticias. "
                "Filtra por entidad, fecha o estado."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                    "reporting_date": {
                        "type": "string",
                        "description": "Filtrar por fecha de reporte (YYYY-MM-DD)",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_crd_capital_position",
            "description": (
                "Obtener detalle completo de una posiciòn de capital CRD/CRR por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID de la posiciòn de capital",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_crd_stress_tests",
            "description": (
                "Listar resultados de pruebas de estrès CRD. "
                "Filtra por entidad, fecha o escenario."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                    "test_date": {
                        "type": "string",
                        "description": "Filtrar por fecha de prueba (YYYY-MM-DD)",
                    },
                    "scenario_name": {
                        "type": "string",
                        "description": "Filtrar por nombre de escenario",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_crd_stress_test",
            "description": (
                "Obtener detalle de una prueba de estrès CRD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID de la prueba de estrès",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_brrd_bail_in",
            "description": (
                "Listar datos de bail-in y MREL BRRD. "
                "Filtra por entidad."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Filtrar por ID de entidad",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_brrd_bail_in",
            "description": (
                "Obtener detalle de datos de bail-in MREL BRRD por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del registro bail-in",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_emir_trade_reports",
            "description": (
                "Listar reportes de operaciones EMIR. "
                "Filtra por clase de activo, instrumento o obligaciòn de liquidaciòn."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "asset_class": {
                        "type": "string",
                        "description": "Filtrar por clase de activo (ej: 'equity', 'fixed-income', 'fx', 'commodity')",
                    },
                    "instrument_class": {
                        "type": "string",
                        "description": "Filtrar por clase de instrumento (ej: 'swap', 'forward', 'option')",
                    },
                    "clearing_obligation_applied": {
                        "type": "boolean",
                        "description": "Solo con obligaciòn de liquidaciòn aplicada",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_emir_trade_report",
            "description": (
                "Obtener detalle de un reporte de operaciòn EMIR por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del reporte de operaciòn",
                    },
                },
                "required": ["item_id"],
            },
        },
        {
            "name": "list_emir_clearing_members",
            "description": (
                "Listar miembros de liquidaciòn EMIR. Filtra por tipo o estado."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "clearing_type": {
                        "type": "string",
                        "enum": ["central", "otc"],
                        "description": "Filtrar por tipo de liquidaciòn",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_emir_clearing_member",
            "description": (
                "Obtener detalle de un miembro de liquidaciòn EMIR por ID."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "ID del miembro de liquidaciòn",
                    },
                },
                "required": ["item_id"],
            },
        },
    ]
