from taxonomies import (
    ALLOWED_AMBITOS,
    ALLOWED_ESTADOS_VIGENCIA,
    ALLOWED_TIPOS_OBLIGACION,
    ALLOWED_TIPOS_FUENTE,
)


def test_regulatory_taxonomies_cover_current_seed_values():
    assert "cnmv" in ALLOWED_TIPOS_FUENTE
    assert "sepblac" in ALLOWED_TIPOS_FUENTE
    assert "aml_cft_reporting" in ALLOWED_AMBITOS
    assert "reporting_regulatorio" in ALLOWED_AMBITOS
    assert "vigente" in ALLOWED_ESTADOS_VIGENCIA
    assert "comunicacion_indicio" in ALLOWED_TIPOS_OBLIGACION
