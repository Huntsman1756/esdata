from entity_profiles import normalize_sociedad_valores_profile


def obligation_applies(profile: dict, obligation: dict) -> bool:
    normalized = normalize_sociedad_valores_profile(profile)

    if normalized.get("tipo_entidad") != "sociedad_valores":
        return False

    codigo = obligation.get("codigo")
    sujeto = obligation.get("sujeto_obligado")
    ambito = obligation.get("ambito")

    if codigo == "CNMV-IR-RESERVADA":
        return bool(normalized.get("reporting_reservado"))

    if codigo == "SEPBLAC-INDICIO-M19":
        return bool(normalized.get("aml_cft_reforzado"))

    if sujeto == "empresa_servicios_inversion":
        return True

    if ambito in {"reporting_regulatorio", "reporting_financiero", "aml_cft", "aml_cft_reporting"}:
        return True

    return False


def build_sociedad_valores_profile(
    reporting_reservado: bool = True,
    aml_cft_reforzado: bool = True,
    cross_border_ue: bool = False,
) -> dict:
    return normalize_sociedad_valores_profile(
        {
            "tipo_entidad": "sociedad_valores",
            "reporting_reservado": reporting_reservado,
            "aml_cft_reforzado": aml_cft_reforzado,
            "cross_border_ue": cross_border_ue,
        }
    )
