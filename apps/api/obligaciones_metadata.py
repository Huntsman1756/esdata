def enrich_obligacion_metadata(obligacion: dict) -> dict:
    result = dict(obligacion)

    codigo = result.get("codigo")
    fuente = result.get("fuente")
    ambito = result.get("ambito")
    tipo_obligacion = result.get("tipo_obligacion")

    if codigo == "SEPBLAC-INDICIO-M19":
        result.setdefault(
            "evidencia_requerida",
            [
                "acuse_presentacion_modelo_19",
                "expediente_interno_indicio",
                "soporte_revision_compliance",
            ],
        )
        result.setdefault("owner_rol_sugerido", "compliance")
        result.setdefault("criticidad", "alta")
        result.setdefault("control_interno_sugerido", "escalado_indicios_y_validacion")
        result.setdefault("procedimiento_relacionado", "procedimiento_comunicacion_indicios_sepblac")
        return result

    if codigo == "CNMV-IR-RESERVADA":
        result.setdefault(
            "evidencia_requerida",
            [
                "acuse_remision_cnmv",
                "paquete_estados_reportados",
                "revision_interna_reporting",
            ],
        )
        result.setdefault("owner_rol_sugerido", "reporting_regulatorio")
        result.setdefault("criticidad", "alta")
        result.setdefault("control_interno_sugerido", "calendario_reporting_y_doble_revision")
        result.setdefault("procedimiento_relacionado", "procedimiento_reporting_reservado_cnmv")
        return result

    if ambito in {"aml_cft", "aml_cft_reporting"}:
        result.setdefault(
            "evidencia_requerida",
            ["registro_actuacion", "soporte_revision", "trazabilidad_decision"],
        )
        result.setdefault("owner_rol_sugerido", "compliance")
        result.setdefault("criticidad", "alta")
        result.setdefault("control_interno_sugerido", "control_prevencion_blanco_capitales")
        result.setdefault("procedimiento_relacionado", "procedimiento_pbcft")
        return result

    if ambito in {"reporting_regulatorio", "reporting_financiero"} or fuente == "cnmv":
        result.setdefault(
            "evidencia_requerida",
            ["acuse_presentacion", "copia_reporte", "revision_segundo_nivel"],
        )
        result.setdefault("owner_rol_sugerido", "reporting_regulatorio")
        result.setdefault("criticidad", "media")
        result.setdefault("control_interno_sugerido", "control_calendario_reporting")
        result.setdefault("procedimiento_relacionado", "procedimiento_reporting_regulatorio")
        return result

    if tipo_obligacion == "presentacion_modelo":
        result.setdefault(
            "evidencia_requerida",
            ["acuse_presentacion", "copia_modelo_presentado"],
        )
        result.setdefault("owner_rol_sugerido", "fiscal")
        result.setdefault("criticidad", "media")
        result.setdefault("control_interno_sugerido", "control_presentacion_modelos")
        result.setdefault("procedimiento_relacionado", "procedimiento_fiscal_periodico")
        return result

    result.setdefault("evidencia_requerida", ["evidencia_operativa_basica"])
    result.setdefault("owner_rol_sugerido", "operaciones")
    result.setdefault("criticidad", "media")
    result.setdefault("control_interno_sugerido", "control_operativo_general")
    result.setdefault("procedimiento_relacionado", "procedimiento_general_cumplimiento")
    return result
