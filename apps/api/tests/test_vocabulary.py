"""Tests for the controlled vocabulary module.

Verifies:
- All current seed/test values are covered by the vocabulary
- No unexpected values exist in workers
- Validation functions work correctly
"""

import importlib.util
import sys
from pathlib import Path

# Explicitly load apps/api/vocabulary to avoid collision with apps/workers/vocabulary
API_DIR = Path(__file__).resolve().parents[1]
vocab_path = API_DIR / "vocabulary.py"
_spec = importlib.util.spec_from_file_location("vocabulary", vocab_path)
api_vocabulary = importlib.util.module_from_spec(_spec)
sys.modules["vocabulary"] = api_vocabulary
_spec.loader.exec_module(api_vocabulary)

from vocabulary import (
    AMBITOS,
    ESTADOS_COBERTURA,
    ESTADOS_VIGENCIA,
    JURISDICCIONES,
    ORGANISMOS_EMISORES,
    REGULACIONES_RELACIONADAS,
    TIPOS_DOCUMENTO,
    TIPOS_FUENTE,
    TIPOS_MICRO_OBLIGACION,
    TIPOS_OBLIGACION,
    TOTAL_VALUES,
    VOCABULARY,
    validate_field,
    validate_payload,
    validate_payload_strict,
)

# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


def test_total_value_count():
    """Vocabulary should cover all known values."""
    assert TOTAL_VALUES == 224, f"Expected 224 total values, got {TOTAL_VALUES}"


def test_vocabulary_has_all_fields():
    """VOCABULARY dict should have exactly 10 fields."""
    expected_fields = {
        "tipo_fuente",
        "tipo_documento",
        "ambito",
        "estado_vigencia",
        "tipo_obligacion",
        "tipo_micro_obligacion",
        "organismo_emisor",
        "estado_cobertura",
        "jurisdiccion",
        "regulacion_relacionada",
    }
    assert set(VOCABULARY.keys()) == expected_fields


def test_tipo_fuente_count():
    assert len(TIPOS_FUENTE) == 11


def test_tipo_documento_count():
    assert len(TIPOS_DOCUMENTO) == 67


def test_ambitos_count():
    assert len(AMBITOS) == 57


def test_estado_vigencia_count():
    assert len(ESTADOS_VIGENCIA) == 5


def test_tipo_obligacion_count():
    assert len(TIPOS_OBLIGACION) == 5


def test_organismo_emisor_count():
    assert len(ORGANISMOS_EMISORES) == 12


def test_estado_cobertura_count():
    assert len(ESTADOS_COBERTURA) == 2


def test_jurisdiccion_count():
    assert len(JURISDICCIONES) == 2


def test_tipo_micro_obligacion_count():
    assert len(TIPOS_MICRO_OBLIGACION) == 53


def test_regulaciones_relacionadas_count():
    assert len(REGULACIONES_RELACIONADAS) == 10


# ---------------------------------------------------------------------------
# Current seed values must be covered
# ---------------------------------------------------------------------------


def test_all_tipo_fuente_seed_values_covered():
    """All tipo_fuente values used in seeds/tests must be in vocabulary."""
    for fuente in ("boe", "eurlex", "dgt", "teac", "cnmv", "sepblac", "cendoj", "bde", "aepd", "bdns", "borme"):
        assert fuente in TIPOS_FUENTE, f"{fuente} not in TIPOS_FUENTE"


def test_all_tipo_documento_seed_values_covered():
    """All tipo_documento values used in seeds/tests must be in vocabulary."""
    values = {
        "ley", "real_decreto_legislativo", "real_decreto", "reglamento", "convenio",
        "directiva_ue", "directiva", "decision", "directive", "regulation", "recommendation", "documento_ue",
        "consulta_vinculante", "resolucion_teac",
        "sentencia", "auto", "providencia", "resolucion",
        "circular_cnmv", "manual_cnmv", "guia_cnmv", "guia_tecnica_cnmv",
        "documento_cnmv", "documento_consulta_cnmv", "normativa_esi_cnmv", "modelo_esi_cnmv",
        "sancion_cnmv",
        "formulario_sepblac", "manual_sepblac", "guia_operativa_sepblac", "obligacion_sepblac", "normativa_sepblac", "documento_sepblac",
        "resolucion_aepd", "guia_aepd", "informe_aepd", "instruccion_aepd", "acuerdo_aepd", "documento_aepd",
        "informe_bde", "comunicacion_bde", "publicacion_bde", "guia_bde", "documento_bde",
        "nombramiento", "cese", "constitucion", "cambio_domicilio",
        "ampliacion_capital", "reduccion_capital", "disolucion", "concurso",
        "convocatoria_bdns", "convocatoria_subvencion",
    }
    missing = values - TIPOS_DOCUMENTO
    assert not missing, f"Missing from TIPOS_DOCUMENTO: {sorted(missing)}"


def test_all_ambito_seed_values_covered():
    """All ambito values used in seeds/tests must be in vocabulary."""
    values = {
        "tributario", "tributario_local", "tributario_internacional", "tributario_ue", "tributario_canarias", "fiscal",
        "reporting_regulatorio", "reporting_financiero", "mercados", "infraestructuras_mercado",
        "sanciones_cnmv",
        "aml_cft", "aml_cft_reporting", "supervision_sepblac",
        "jurisprudencia", "jurisprudencia_tributaria", "jurisprudencia_pbcft", "jurisprudencia_mercantil_regulatoria",
        "fiscal_ue", "mercados_financieros_ue", "abuso_mercado_ue", "disclosure_ue", "resiliencia_digital_ue",
        "mercado_interior", "competencia_ue", "ue_general",
        "proteccion_datos", "proteccion_datos_general", "derechos_ar", "ficheros_datos", "cookies",
        "estabilidad_financiera", "politica_monetaria", "supervision_bancaria", "sistemas_pago", "economia_espanola",
        "mercantil", "subvenciones",
    }
    missing = values - AMBITOS
    assert not missing, f"Missing from AMBITOS: {sorted(missing)}"


def test_all_organismo_emisor_seed_values_covered():
    """All organismo_emisor values used in seeds/tests must be in vocabulary."""
    values = {"DGT", "TEAC", "CNMV", "SEPBLAC", "AEPD", "Banco de Espana", "UE", "BDNS", "BORME", "Tribunal Supremo"}
    missing = values - ORGANISMOS_EMISORES
    assert not missing, f"Missing from ORGANISMOS_EMISORES: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Validation function tests
# ---------------------------------------------------------------------------


def test_validate_field_valid():
    assert validate_field("tipo_fuente", "boe") is True
    assert validate_field("tipo_documento", "ley") is True
    assert validate_field("ambito", "tributario") is True
    assert validate_field("estado_vigencia", "vigente") is True
    assert validate_field("tipo_obligacion", "presentacion_modelo") is True
    assert validate_field("organismo_emisor", "DGT") is True
    assert validate_field("estado_cobertura", "ingestada") is True
    assert validate_field("jurisdiccion", "es") is True


def test_validate_field_invalid():
    assert validate_field("tipo_fuente", "unknown") is False
    assert validate_field("tipo_documento", "fake_type") is False
    assert validate_field("ambito", "nonexistent") is False
    assert validate_field("estado_vigencia", "expired") is False
    assert validate_field("tipo_obligacion", "random") is False
    assert validate_field("organismo_emisor", "FakeOrg") is False


def test_validate_field_unknown_field():
    assert validate_field("nonexistent_field", "anything") is False


def test_validate_payload_valid():
    payload = {
        "tipo_fuente": "boe",
        "tipo_documento": "ley",
        "ambito": "tributario",
        "organismo_emisor": "DGT",
    }
    assert validate_payload(payload) == []


def test_validate_payload_invalid():
    payload = {
        "tipo_fuente": "boe",
        "tipo_documento": "fake_type",
        "ambito": "tributario",
        "unknown_field": "ignored",
    }
    errors = validate_payload(payload)
    assert len(errors) == 1
    assert "fake_type" in errors[0]


def test_validate_payload_multiple_errors():
    payload = {
        "tipo_fuente": "fake",
        "tipo_documento": "fake",
        "ambito": "fake",
    }
    errors = validate_payload(payload)
    assert len(errors) == 3


def test_validate_payload_with_allowed_fields():
    payload = {
        "tipo_fuente": "boe",
        "tipo_documento": "fake_type",
        "ambito": "tributario",
    }
    errors = validate_payload(payload, allowed_fields=frozenset({"tipo_documento"}))
    assert len(errors) == 1  # only tipo_documento checked
    assert validate_field("tipo_documento", "fake_type") is False


def test_validate_payload_strict_missing_field():
    payload = {"tipo_fuente": "boe"}
    errors = validate_payload_strict(payload, frozenset({"tipo_documento", "ambito"}))
    assert any("Missing required field" in e for e in errors)


def test_validate_payload_strict_valid():
    payload = {
        "tipo_fuente": "boe",
        "tipo_documento": "ley",
        "ambito": "tributario",
    }
    errors = validate_payload_strict(payload, frozenset({"tipo_fuente", "tipo_documento", "ambito"}))
    assert errors == []


def test_validate_payload_strict_invalid():
    payload = {
        "tipo_fuente": "boe",
        "tipo_documento": "fake",
        "ambito": "tributario",
    }
    errors = validate_payload_strict(payload, frozenset({"tipo_fuente", "tipo_documento", "ambito"}))
    assert any("Invalid tipo_documento" in e for e in errors)
