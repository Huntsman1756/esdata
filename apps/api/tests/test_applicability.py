from applicability import build_sociedad_valores_profile, obligation_applies


def test_reporting_reservado_applies_to_sociedad_valores_profile():
    profile = build_sociedad_valores_profile(reporting_reservado=True)
    obligation = {
        "codigo": "CNMV-IR-RESERVADA",
        "sujeto_obligado": "empresa_servicios_inversion",
        "ambito": "reporting_regulatorio",
    }

    assert obligation_applies(profile, obligation) is True


def test_unknown_entity_type_does_not_apply():
    profile = {
        "tipo_entidad": "otra_entidad",
        "reporting_reservado": True,
        "aml_cft_reforzado": True,
    }
    obligation = {
        "codigo": "CNMV-IR-RESERVADA",
        "sujeto_obligado": "empresa_servicios_inversion",
        "ambito": "reporting_regulatorio",
    }

    assert obligation_applies(profile, obligation) is False
