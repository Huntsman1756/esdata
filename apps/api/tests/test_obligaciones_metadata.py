"""Unit tests for obligaciones_metadata module."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from obligaciones_metadata import enrich_obligacion_metadata


class TestEnrichObligacionMetadata:
    """Verify enrichment logic for known obligations and fallback."""

    def test_fallback_default_enrichment(self):
        obligacion = {"codigo": "UNKNOWN", "descripcion": "test"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["evidencia_requerida"] == ["evidencia_operativa_basica"]
        assert result["owner_rol_sugerido"] == "operaciones"
        assert result["criticidad"] == "media"
        assert result["control_interno_sugerido"] == "control_operativo_general"

    def test_fallback_preserves_original_fields(self):
        obligacion = {"codigo": "X", "descripcion": "test"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["codigo"] == "X"
        assert result["descripcion"] == "test"

    def test_fallback_does_not_override_existing(self):
        obligacion = {
            "codigo": "X",
            "criticidad": "baja",
            "evidencia_requerida": ["custom"],
        }
        result = enrich_obligacion_metadata(obligacion)
        assert result["criticidad"] == "baja"
        assert result["evidencia_requerida"] == ["custom"]

    def test_sepblac_indicio_m19_enrichment(self):
        obligacion = {"codigo": "SEPBLAC-INDICIO-M19"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "compliance"
        assert result["criticidad"] == "alta"
        assert "acuse_presentacion_modelo_19" in result["evidencia_requerida"]
        assert result["control_interno_sugerido"] == "escalado_indicios_y_validacion"

    def test_cnmv_ir_reservada_enrichment(self):
        obligacion = {"codigo": "CNMV-IR-RESERVADA"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "reporting_regulatorio"
        assert result["criticidad"] == "alta"
        assert "acuse_remision_cnmv" in result["evidencia_requerida"]
        assert result["control_interno_sugerido"] == "calendario_reporting_y_doble_revision"

    def test_aml_cft_enrichment(self):
        obligacion = {"codigo": "X", "ambito": "aml_cft"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "compliance"
        assert result["criticidad"] == "alta"
        assert result["control_interno_sugerido"] == "control_prevencion_blanco_capitales"

    def test_aml_cft_reporting_enrichment(self):
        obligacion = {"codigo": "X", "ambito": "aml_cft_reporting"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "compliance"

    def test_reporting_regulatorio_enrichment(self):
        obligacion = {"codigo": "X", "ambito": "reporting_regulatorio"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "reporting_regulatorio"
        assert result["criticidad"] == "media"

    def test_reporting_financiero_enrichment(self):
        obligacion = {"codigo": "X", "ambito": "reporting_financiero"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "reporting_regulatorio"

    def test_cnmv_fuente_enrichment(self):
        obligacion = {"codigo": "X", "fuente": "cnmv"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "reporting_regulatorio"
        assert result["criticidad"] == "media"

    def test_presentacion_modelo_enrichment(self):
        obligacion = {"codigo": "X", "tipo_obligacion": "presentacion_modelo"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "fiscal"
        assert result["criticidad"] == "media"
        assert "acuse_presentacion" in result["evidencia_requerida"]

    def test_specific_rule_takes_precedence_over_generic(self):
        """SEPBLAC-INDICIO-M19 should match its specific rule, not a generic one."""
        obligacion = {"codigo": "SEPBLAC-INDICIO-M19", "ambito": "reporting_regulatorio"}
        result = enrich_obligacion_metadata(obligacion)
        assert result["owner_rol_sugerido"] == "compliance"
        assert "acuse_presentacion_modelo_19" in result["evidencia_requerida"]
