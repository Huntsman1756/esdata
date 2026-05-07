"""Tests for the vocabulary_validation worker module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vocabulary_validation import (
    DOCUMENTO_VOCAB_FIELDS,
    WORKER_FALLBACKS,
    safe_payload_value,
    sanitize_documento_payload,
    sanitize_payload,
)


class TestSafePayloadValue:
    """Test safe_payload_value function."""

    def test_valid_value_unchanged(self):
        assert safe_payload_value("tipo_fuente", "boe") == "boe"
        assert safe_payload_value("tipo_documento", "ley") == "ley"
        assert safe_payload_value("ambito", "tributario") == "tributario"
        assert safe_payload_value("estado_vigencia", "vigente") == "vigente"
        assert safe_payload_value("tipo_obligacion", "presentacion_modelo") == "presentacion_modelo"
        assert safe_payload_value("organismo_emisor", "DGT") == "DGT"
        assert safe_payload_value("estado_cobertura", "ingestada") == "ingestada"
        assert safe_payload_value("jurisdiccion", "es") == "es"

    def test_invalid_value_kept_without_fallback(self, caplog):
        """Invalid values are kept (graceful degradation)."""
        result = safe_payload_value("tipo_documento", "fake_type")
        assert result == "fake_type"
        assert len([r for r in caplog.records if r.levelname == "WARNING"]) >= 1

    def test_invalid_organismo_emisor_fallback(self, caplog):
        """TSJ should be mapped to Tribunal Supremo."""
        result = safe_payload_value("organismo_emisor", "TSJ")
        assert result == "Tribunal Supremo"

    def test_valid_organismo_emisor_unchanged(self):
        assert safe_payload_value("organismo_emisor", "Audiencia Nacional") == "Audiencia Nacional"
        assert safe_payload_value("organismo_emisor", "CENDOJ") == "CENDOJ"

    def test_unknown_field_returns_false(self):
        result = safe_payload_value("nonexistent_field", "anything")
        assert result == "anything"

    def test_safe_payload_value_uses_explicit_fallback_when_mapping_missing(self):
        result = safe_payload_value(
            "ambito",
            "ambito_invalido",
            fallback="mercados",
        )

        assert result == "mercados"

    def test_safe_payload_value_ignores_invalid_worker_mapping_and_uses_explicit_fallback(
        self,
    ):
        original = WORKER_FALLBACKS.setdefault("ambito", {}).get("ambito_invalido")
        WORKER_FALLBACKS["ambito"]["ambito_invalido"] = "valor_no_permitido"

        try:
            result = safe_payload_value(
                "ambito",
                "ambito_invalido",
                fallback="mercados",
            )
        finally:
            if original is None:
                del WORKER_FALLBACKS["ambito"]["ambito_invalido"]
            else:
                WORKER_FALLBACKS["ambito"]["ambito_invalido"] = original

        assert result == "mercados"


class TestSanitizePayload:
    """Test sanitize_payload function."""

    def test_valid_payload_unchanged(self):
        payload = {
            "tipo_fuente": "boe",
            "tipo_documento": "ley",
            "ambito": "tributario",
            "jurisdiccion": "es",
        }
        result = sanitize_payload(payload)
        assert result == payload

    def test_invalid_values_replaced(self):
        payload = {
            "tipo_fuente": "boe",
            "tipo_documento": "fake_type",
            "ambito": "tributario",
        }
        result = sanitize_payload(payload)
        assert result["tipo_fuente"] == "boe"
        assert result["tipo_documento"] == "fake_type"  # kept, not in vocab
        assert result["ambito"] == "tributario"

    def test_only_checked_fields_sanitized(self):
        payload = {
            "tipo_fuente": "boe",
            "tipo_documento": "fake_type",
            "custom_field": "custom_value",
        }
        result = sanitize_payload(payload, frozenset({"tipo_documento"}))
        assert result["tipo_documento"] == "fake_type"  # kept (no fallback)
        assert result["custom_field"] == "custom_value"  # untouched

    def test_explicit_empty_vocabulary_fields_sanitizes_nothing(self):
        payload = {
            "organismo_emisor": "TSJ",
            "ambito": "general_cnmv",
        }

        result = sanitize_payload(payload, frozenset())

        assert result == payload

    def test_partial_invalid_payload(self):
        payload = {
            "tipo_fuente": "fake_source",
            "tipo_documento": "ley",
            "ambito": "fake_ambito",
            "jurisdiccion": "es",
        }
        result = sanitize_payload(payload)
        assert result["tipo_fuente"] == "fake_source"  # kept (no fallback)
        assert result["tipo_documento"] == "ley"
        assert result["ambito"] == "fake_ambito"  # kept (no fallback)
        assert result["jurisdiccion"] == "es"

    def test_non_string_values_ignored(self):
        payload = {
            "tipo_fuente": "boe",
            "some_int": 42,
            "some_none": None,
        }
        result = sanitize_payload(payload)
        assert result["tipo_fuente"] == "boe"
        assert result["some_int"] == 42
        assert result["some_none"] is None

    def test_cendoj_payload_sanitization(self):
        """CENDOJ worker payload with TSJ organism."""
        payload = {
            "tipo_documento": "sentencia",
            "tipo_fuente": "cendoj",
            "organismo_emisor": "TSJ",
            "ambito": "jurisprudencia_tributaria",
            "jurisdiccion": "es",
        }
        result = sanitize_payload(payload)
        assert result["organismo_emisor"] == "Tribunal Supremo"

    def test_sanitize_payload_prefers_worker_mapping_over_explicit_field_fallback(self):
        payload = {"organismo_emisor": "TSJ"}

        result = sanitize_payload(
            payload,
            frozenset({"organismo_emisor"}),
            field_fallbacks={"organismo_emisor": "CENDOJ"},
        )

        assert result["organismo_emisor"] == "Tribunal Supremo"

    def test_sanitize_documento_payload_applies_known_worker_mappings(self):
        payload = {
            "tipo_documento": "resolucion_cnmv",
            "organismo_emisor": "Banco de España",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
            "ambito": "general_cnmv",
            "estado_vigencia": "vigente",
        }

        result = sanitize_documento_payload(payload)

        assert DOCUMENTO_VOCAB_FIELDS == frozenset(
            {
                "tipo_documento",
                "organismo_emisor",
                "jurisdiccion",
                "tipo_fuente",
                "ambito",
                "estado_vigencia",
            }
        )
        assert result["tipo_documento"] == "documento_cnmv"
        assert result["organismo_emisor"] == "Banco de Espana"
        assert result["ambito"] == "mercados"
        assert result["estado_vigencia"] == "vigente"

    def test_empty_payload(self):
        assert sanitize_payload({}) == {}


class TestWorkerFallbacks:
    """Test worker fallback mapping configuration."""

    def test_fallbacks_structure(self):
        assert isinstance(WORKER_FALLBACKS, dict)

    def test_tsj_fallback_exists(self):
        assert "TSJ" in WORKER_FALLBACKS.get("organismo_emisor", {})
        assert WORKER_FALLBACKS["organismo_emisor"]["TSJ"] == "Tribunal Supremo"
