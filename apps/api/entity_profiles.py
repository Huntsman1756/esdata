DEFAULT_SOCIEDAD_VALORES_SERVICIOS = (
    "recepcion_transmision_ordenes",
    "ejecucion_ordenes",
    "asesoramiento_inversion",
    "gestion_discrecional",
    "colocacion",
    "aseguramiento",
    "custodia",
)


def build_default_sociedad_valores_profile() -> dict:
    return {
        "tipo_entidad": "sociedad_valores",
        "jurisdiccion": "es",
        "supervision_principal": "CNMV",
        "servicios_inversion": [],
        "tipos_cliente": [],
        "cross_border_ue": False,
        "cross_border_fuera_ue": False,
        "outsourcing_critico": False,
        "reporting_reservado": True,
        "comercializacion_priips": False,
        "aml_cft_reforzado": True,
    }


def normalize_sociedad_valores_profile(profile: dict | None) -> dict:
    base = build_default_sociedad_valores_profile()
    if not profile:
        return base

    normalized = {**base, **profile}

    servicios = normalized.get("servicios_inversion") or []
    normalized["servicios_inversion"] = [
        servicio for servicio in servicios if servicio in DEFAULT_SOCIEDAD_VALORES_SERVICIOS
    ]

    tipos_cliente = normalized.get("tipos_cliente") or []
    normalized["tipos_cliente"] = sorted({cliente for cliente in tipos_cliente if cliente})

    return normalized
