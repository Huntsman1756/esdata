from entity_profiles import build_default_sociedad_valores_profile, normalize_sociedad_valores_profile


def test_default_sociedad_valores_profile_contains_core_flags():
    profile = build_default_sociedad_valores_profile()

    assert profile["tipo_entidad"] == "sociedad_valores"
    assert profile["supervision_principal"] == "CNMV"
    assert "servicios_inversion" in profile
    assert "reporting_reservado" in profile
    assert "cross_border_ue" in profile


def test_normalize_sociedad_valores_profile_filters_unknown_services():
    profile = normalize_sociedad_valores_profile(
        {
            "servicios_inversion": ["custodia", "inventado"],
            "tipos_cliente": ["retail", "retail", "profesional"],
        }
    )

    assert profile["servicios_inversion"] == ["custodia"]
    assert profile["tipos_cliente"] == ["profesional", "retail"]
