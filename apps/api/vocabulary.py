"""Controlled vocabulary for regulatory classification fields.

This module is the single source of truth for allowed values in:
- tipo_fuente
- tipo_documento
- ambito
- estado_vigencia
- tipo_obligacion
- tipo_micro_obligacion
- organismo_emisor
- estado_cobertura
- jurisdiccion
- regulacion_relacionada

All workers, routers, and seeds must use only these values.
New values require updating this file and adding tests in test_vocabulary.py.

Legacy: apps/api/taxonomies.py is deprecated. Use this module instead.
"""

# ---------------------------------------------------------------------------
# tipo_fuente — 11 values
# ---------------------------------------------------------------------------

TIPOS_FUENTE: frozenset[str] = frozenset({
    "boe",
    "eurlex",
    "dgt",
    "teac",
    "cnmv",
    "sepblac",
    "cendoj",
    "bde",
    "aepd",
    "bdns",
    "borme",
})

# ---------------------------------------------------------------------------
# tipo_documento — 44 values
# ---------------------------------------------------------------------------

TIPOS_DOCUMENTO_LEGISLACION: frozenset[str] = frozenset({
    "ley",
    "real_decreto_legislativo",
    "real_decreto",
    "reglamento",
    "convenio",
})

TIPOS_DOCUMENTO_UE: frozenset[str] = frozenset({
    "directiva_ue",
    "directiva",
    "reglamento",
    "decision",
    "directive",
    "regulation",
    "recommendation",
    "documento_ue",
})

TIPOS_DOCUMENTO_DOCTRINA: frozenset[str] = frozenset({
    "consulta_vinculante",
    "resolucion_teac",
})

TIPOS_DOCUMENTO_JURISPRUDENCIA: frozenset[str] = frozenset({
    "sentencia",
    "auto",
    "providencia",
    "resolucion",
})

TIPOS_DOCUMENTO_CNMV: frozenset[str] = frozenset({
    "circular_cnmv",
    "manual_cnmv",
    "guia_cnmv",
    "guia_tecnica_cnmv",
    "documento_cnmv",
    "documento_consulta_cnmv",
    "normativa_esi_cnmv",
    "modelo_esi_cnmv",
    "resolucion_cnmv",
    "codigo_autoregulacion_cnmv",
    "informe_anual_cnmv",
    "instruccion_tecnica_cnmv",
    "dictamen_cnmv",
    "modelo_comunicacion_cnmv",
    "decision_supervision_cnmv",
    "estadistica_mercado_cnmv",
    "codigo_conducta_cnmv",
    "circ_asesoramiento_cnmv",
    "informe_cnmv",
    "reglamento_cnmv",
})

TIPOS_DOCUMENTO_SEPBLAC: frozenset[str] = frozenset({
    "formulario_sepblac",
    "manual_sepblac",
    "guia_operativa_sepblac",
    "obligacion_sepblac",
    "normativa_sepblac",
    "documento_sepblac",
})

TIPOS_DOCUMENTO_AEPD: frozenset[str] = frozenset({
    "resolucion_aepd",
    "guia_aepd",
    "informe_aepd",
    "instruccion_aepd",
    "acuerdo_aepd",
    "documento_aepd",
})

TIPOS_DOCUMENTO_BDE: frozenset[str] = frozenset({
    "informe_bde",
    "comunicacion_bde",
    "publicacion_bde",
    "guia_bde",
    "documento_bde",
})

TIPOS_DOCUMENTO_BORME: frozenset[str] = frozenset({
    "nombramiento",
    "cese",
    "constitucion",
    "cambio_domicilio",
    "ampliacion_capital",
    "reduccion_capital",
    "disolucion",
    "concurso",
})

TIPOS_DOCUMENTO_OTROS: frozenset[str] = frozenset({
    "convocatoria_bdns",
    "convocatoria_subvencion",
})

# Union of all tipo_documento values
TIPOS_DOCUMENTO: frozenset[str] = frozenset({
    *TIPOS_DOCUMENTO_LEGISLACION,
    *TIPOS_DOCUMENTO_UE,
    *TIPOS_DOCUMENTO_DOCTRINA,
    *TIPOS_DOCUMENTO_JURISPRUDENCIA,
    *TIPOS_DOCUMENTO_CNMV,
    *TIPOS_DOCUMENTO_SEPBLAC,
    *TIPOS_DOCUMENTO_AEPD,
    *TIPOS_DOCUMENTO_BDE,
    *TIPOS_DOCUMENTO_BORME,
    *TIPOS_DOCUMENTO_OTROS,
})

# ---------------------------------------------------------------------------
# ambito — 37 values
# ---------------------------------------------------------------------------

AMBITOS_TRIBUTARIO: frozenset[str] = frozenset({
    "tributario",
    "tributario_local",
    "tributario_internacional",
    "tributario_ue",
    "tributario_canarias",
    "fiscal",  # legacy, being migrated to "tributario"
})

AMBITOS_MERCADOS: frozenset[str] = frozenset({
    "reporting_regulatorio",
    "reporting_financiero",
    "mercados",
    "infraestructuras_mercado",
})

AMBITOS_AML_CFT: frozenset[str] = frozenset({
    "aml_cft",
    "aml_cft_reporting",
    "supervision_sepblac",
})

AMBITOS_JURISPRUDENCIA: frozenset[str] = frozenset({
    "jurisprudencia",
    "jurisprudencia_tributaria",
    "jurisprudencia_pbcft",
    "jurisprudencia_mercantil_regulatoria",
})

AMBITOS_UE: frozenset[str] = frozenset({
    "fiscal_ue",
    "mercados_financieros_ue",
    "abuso_mercado_ue",
    "disclosure_ue",
    "resiliencia_digital_ue",
    "mercado_interior",
    "competencia_ue",
    "ue_general",
})

AMBITOS_PROTECCION_DATOS: frozenset[str] = frozenset({
    "proteccion_datos",
    "proteccion_datos_general",
    "derechos_ar",
    "ficheros_datos",
    "cookies",
})

AMBITOS_BDE: frozenset[str] = frozenset({
    "estabilidad_financiera",
    "politica_monetaria",
    "supervision_bancaria",
    "sistemas_pago",
    "economia_espanola",
})

AMBITOS_OTROS: frozenset[str] = frozenset({
    "mercantil",
    "subvenciones",
})

# Nuevos ambitos para LECR, SOCIMI, CSDR, CNMV ECR, Doctrina DGT
AMBITOS_ECR: frozenset[str] = frozenset({
    "ecr_regulatorio",
})

AMBITOS_SOCIMI: frozenset[str] = frozenset({
    "societario_fiscal",
})

AMBITOS_CSDR: frozenset[str] = frozenset({
    "infraestructuras_csd",
})

AMBITOS_CNMV_ECR: frozenset[str] = frozenset({
    "reporting_cnmv_ecr",
})

AMBITOS_CNMV_EXPANDIDOS: frozenset[str] = frozenset({
    "mifid_ii",
    "mifir",
    "mar",
    "dora",
    "priips",
    "pgc_cnmv",
    "niif_cnmv",
    "transparencia_emisores",
    "gobierno_corporativo",
    "reporting_regulatorio_cnmv",
    "reporting_financiero_cnmv",
    "mercados_cnmv",
    "infraestructuras_cnmv",
    "proteccion_inversor_cnmv",
    "sanciones_cnmv",
})

AMBITOS_DGT: frozenset[str] = frozenset({
    "doctrina_dgt",
})

# Union of all ambito values
AMBITOS: frozenset[str] = frozenset({
    *AMBITOS_TRIBUTARIO,
    *AMBITOS_MERCADOS,
    *AMBITOS_AML_CFT,
    *AMBITOS_JURISPRUDENCIA,
    *AMBITOS_UE,
    *AMBITOS_PROTECCION_DATOS,
    *AMBITOS_BDE,
    *AMBITOS_OTROS,
    *AMBITOS_ECR,
    *AMBITOS_SOCIMI,
    *AMBITOS_CSDR,
    *AMBITOS_CNMV_ECR,
    *AMBITOS_CNMV_EXPANDIDOS,
    *AMBITOS_DGT,
})

# ---------------------------------------------------------------------------
# estado_vigencia — 5 values
# ---------------------------------------------------------------------------

ESTADOS_VIGENCIA: frozenset[str] = frozenset({
    "vigente",
    "vigente_modificado",
    "historico",
    "derogado",
    "consulta_cerrada",
})

# ---------------------------------------------------------------------------
# tipo_obligacion — 5 values
# ---------------------------------------------------------------------------

TIPOS_OBLIGACION: frozenset[str] = frozenset({
    "presentacion_modelo",
    "remision_informacion",
    "comunicacion_indicio",
    "control_interno",
    "reporting_prudencial",
})

# ---------------------------------------------------------------------------
# organismo_emisor — 10 values
# ---------------------------------------------------------------------------

ORGANISMOS_EMISORES: frozenset[str] = frozenset({
    "DGT",
    "TEAC",
    "CNMV",
    "SEPBLAC",
    "AEPD",
    "Banco de Espana",
    "UE",
    "BDNS",
    "BORME",
    "Tribunal Supremo",
    "Audiencia Nacional",
    "CENDOJ",
})

# ---------------------------------------------------------------------------
# estado_cobertura — 2 values
# ---------------------------------------------------------------------------

ESTADOS_COBERTURA: frozenset[str] = frozenset({
    "ingestada",
    "referenciada",
})

# ---------------------------------------------------------------------------
# jurisdiccion — 2 values
# ---------------------------------------------------------------------------

JURISDICCIONES: frozenset[str] = frozenset({
    "es",
    "ue",
})

# ---------------------------------------------------------------------------
# tipo_micro_obligacion — 28 values (Fase 20)
# ---------------------------------------------------------------------------

TIPOS_MICRO_OBLIGACION: frozenset[str] = frozenset({
    "suitability",
    "appropriateness",
    "best_execution",
    "conflicts_of_interest",
    "inducements",
    "product_governance",
    "mifir_reporting",
    "insider_list",
    "order_recording",
    "client_categorization",
    "compensation_policy",
    "market_abuse_detection",
    "cnmv_reporting_reserved",
    "transparency",
    "corporate_governance",
    "own_instruments_ops",
    "material_events_communication",
    "insider_ops_registration",
    "financial_reconciliation",
    "information_documents",
    "kyc_due_diligence",
    "continuous_monitoring",
    "suspicious_transaction_reporting",
    "operation_suspension",
    "pep_screening",
    "document_retention",
    "aml_training",
    "internal_aml_controls",
    "risk_mitigation_policy",
    "annual_sepblac_reporting",
    "ecr_registration",
    "ecr_sgeic",
    "ecr_diversification",
    "ecr_miid_diversification",
    "ecr_conduct_rules",
    "ecr_fiscal_non_resident",
    "socimi_asset_composition",
    "socimi_distribution",
    "socimi_tax_undistributed",
    "socimi_tax_regime",
    "socimi_tributary_regime",
    "csdr_settlement",
    "csdr_reporting",
    "csdr_settlement_failure",
    "cnmv_ecr_reporting",
    "cnmv_ecr_xml_format",
    "cnmv_ecr_active_list",
    "cnmv_ecr_faqs",
    "dgt_socimi_gravamenes",
    "dgt_socimi_distribucion",
    "dgt_eti_emisores",
    "dgt_fcr_exenciones",
    "socimi_80_20_rule",
})

# ---------------------------------------------------------------------------
# regulacion_relacionada — 5 values (Fase 20)
# ---------------------------------------------------------------------------

REGULACIONES_RELACIONADAS: frozenset[str] = frozenset({
    "mifid_ii",
    "mifir",
    "mar",
    "cnmv_lmcv",
    "pblcft",
    "lecr",
    "socimi",
    "csdr",
    "doctrina_dgt",
    "cnmv_ecr",
})

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

# All vocabulary sets grouped by field name
VOCABULARY: dict[str, frozenset[str]] = {
    "tipo_fuente": TIPOS_FUENTE,
    "tipo_documento": TIPOS_DOCUMENTO,
    "ambito": AMBITOS,
    "estado_vigencia": ESTADOS_VIGENCIA,
    "tipo_obligacion": TIPOS_OBLIGACION,
    "tipo_micro_obligacion": TIPOS_MICRO_OBLIGACION,
    "organismo_emisor": ORGANISMOS_EMISORES,
    "estado_cobertura": ESTADOS_COBERTURA,
    "jurisdiccion": JURISDICCIONES,
    "regulacion_relacionada": REGULACIONES_RELACIONADAS,
}

# Total count
TOTAL_VALUES: int = sum(len(s) for s in VOCABULARY.values())

# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def validate_field(field_name: str, value: str) -> bool:
    """Return True if `value` is in the allowed set for `field_name`."""
    allowed = VOCABULARY.get(field_name)
    if allowed is None:
        return False
    return value in allowed


def validate_payload(payload: dict, allowed_fields: frozenset[str] | None = None) -> list[str]:
    """Validate a payload dict against the controlled vocabulary.

    Returns a list of error strings. Empty list means all valid.
    """
    errors: list[str] = []
    check_fields = allowed_fields if allowed_fields else set(VOCABULARY.keys())
    for field, value in payload.items():
        if field not in check_fields:
            continue
        if not isinstance(value, str):
            continue
        if not validate_field(field, value):
            errors.append(f"Invalid {field}: {value!r}")
    return errors


def validate_payload_strict(payload: dict, required_fields: frozenset[str]) -> list[str]:
    """Validate payload, also checking that required fields are present."""
    errors: list[str] = []
    missing = required_fields - set(payload.keys())
    for field in sorted(missing):
        errors.append(f"Missing required field: {field!r}")
    errors.extend(validate_payload(payload, required_fields))
    return errors
