"""Unit tests for change_impact_data module (data layer, not router)."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from change_impact_data import SEED_CHANGES, list_seed_changes


class TestSeedChanges:
    """Verify SEED_CHANGES contract."""

    def test_seed_changes_is_list(self):
        assert isinstance(SEED_CHANGES, list)

    def test_seed_changes_has_one_entry(self):
        assert len(SEED_CHANGES) == 1

    def test_seed_change_has_required_fields(self):
        item = SEED_CHANGES[0]
        required = {"codigo", "fuente", "impacto", "estado", "obligaciones_afectadas",
                     "accion_recomendada", "prioridad", "fecha_detectado"}
        assert required.issubset(item.keys())

    def test_seed_change_fields_values(self):
        item = SEED_CHANGES[0]
        assert item["codigo"] == "CAMBIO-CNMV-001"
        assert item["fuente"] == "cnmv"
        assert item["estado"] == "nuevo"
        assert item["prioridad"] == "alta"
        assert item["obligaciones_afectadas"] == ["CNMV-IR-RESERVADA"]
        assert item["fecha_detectado"] == "2026-04-25"


class TestListSeedChanges:
    """Verify list_seed_changes returns independent copies."""

    def test_returns_list(self):
        result = list_seed_changes()
        assert isinstance(result, list)

    def test_same_content_as_seed(self):
        result = list_seed_changes()
        assert result[0]["codigo"] == "CAMBIO-CNMV-001"

    def test_returns_independent_copy(self):
        result = list_seed_changes()
        result[0]["codigo"] = "MODIFIED"
        assert SEED_CHANGES[0]["codigo"] == "CAMBIO-CNMV-001"

    def test_same_number_of_items(self):
        result = list_seed_changes()
        assert len(result) == len(SEED_CHANGES)
