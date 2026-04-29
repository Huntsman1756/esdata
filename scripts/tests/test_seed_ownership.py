"""Tests para seed_ownership.py — Ownership shares, relations, UBOs, beneficial owners."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_ownership import SHARES, RELATIONS, UBOS, BENEFICIAL_OWNERS


class TestOwnershipSharesData:
    def test_shares_not_empty(self):
        assert len(SHARES) > 0

    def test_shares_correct_count(self):
        assert len(SHARES) == 5

    def test_shares_have_eleven_fields(self):
        for row in SHARES:
            assert len(row) == 11

    def test_shares_empresa_id_valid(self):
        for row in SHARES:
            assert row[0] in (1, 2, 3, 4, 5)

    def test_shares_titular_id_valid(self):
        for row in SHARES:
            assert row[1] in (1, 2, 3, 4, 5)

    def test_shares_titular_tipo_valid(self):
        for row in SHARES:
            assert row[2] == "empresa"

    def test_shares_titular_names_valid(self):
        valid_names = {"Telefonica, S.A.", "Banco Santander, S.A.", "Iberdrola, S.A.", "Mapfre, S.A."}
        for row in SHARES:
            assert row[3] in valid_names

    def test_shares_porcentaje_range(self):
        for row in SHARES:
            assert 0 < row[4] <= 100

    def test_shares_tipo_participacion_valid(self):
        for row in SHARES:
            assert row[5] == "directa"

    def test_shares_fuente_valid(self):
        for row in SHARES:
            assert row[8] in ("BOE", "CNMV")


class TestOwnershipRelationsData:
    def test_relations_not_empty(self):
        assert len(RELATIONS) > 0

    def test_relations_correct_count(self):
        assert len(RELATIONS) == 3

    def test_relations_have_ten_fields(self):
        for row in RELATIONS:
            assert len(row) == 10

    def test_relations_origen_destino_valid(self):
        for row in RELATIONS:
            assert row[0] in (1, 2, 3, 4, 5)
            assert row[1] in (1, 2, 3, 4, 5)

    def test_relations_tipo_valid(self):
        valid = {"participacion_significativa", "participacion_mayoritaria", "grupo_economico", "control", "absorbente", "absorbida", "escindente", "escindida", "filial", "matriz", "equivalencia", "joint_venture", "representante_legal", "administrador"}
        for row in RELATIONS:
            assert row[2] in valid

    def test_relations_porcentaje_range(self):
        for row in RELATIONS:
            assert 0 < row[3] <= 100

    def test_relations_fuente_valid(self):
        for row in RELATIONS:
            assert row[6] in ("BOE", "CNMV")

    def test_relations_nota_non_empty(self):
        for row in RELATIONS:
            assert len(row[9]) > 0


class TestUBORecordsData:
    def test_ubos_not_empty(self):
        assert len(UBOS) > 0

    def test_ubos_correct_count(self):
        assert len(UBOS) == 5

    def test_ubos_have_fourteen_fields(self):
        for row in UBOS:
            assert len(row) == 14

    def test_ubos_empresa_id_valid(self):
        for row in UBOS:
            assert row[0] in (1, 2, 3, 4, 5)

    def test_ubos_nombre_non_empty(self):
        for row in UBOS:
            assert len(row[1]) > 0

    def test_ubos_pais_valid(self):
        for row in UBOS:
            assert row[4] == "es"

    def test_ubos_tipo_valid(self):
        valid = {"administrador_legal", "organo_administracion", "control_por_otros_medios", "administracion_publica", "titular_poder", "titular_propiedad", "representante"}
        for row in UBOS:
            assert row[5] in valid

    def test_ubos_porcentaje_valid(self):
        for row in UBOS:
            assert row[6] > 0

    def test_ubos_umbral_valid(self):
        for row in UBOS:
            assert row[7] == "superior_50"

    def test_ubos_fuente_valid(self):
        for row in UBOS:
            assert row[10] in ("BOE", "CNMV")


class TestBeneficialOwnersData:
    def test_owners_not_empty(self):
        assert len(BENEFICIAL_OWNERS) > 0

    def test_owners_correct_count(self):
        assert len(BENEFICIAL_OWNERS) == 5

    def test_owners_have_six_fields(self):
        for row in BENEFICIAL_OWNERS:
            assert len(row) == 6

    def test_owners_entity_id_valid(self):
        for row in BENEFICIAL_OWNERS:
            assert row[0] in (1, 2, 3, 4, 5)

    def test_owners_names_non_empty(self):
        for row in BENEFICIAL_OWNERS:
            assert len(row[1]) > 0

    def test_owners_percentages_valid(self):
        for row in BENEFICIAL_OWNERS:
            assert 0 < row[2] <= 100

    def test_owners_methods_valid(self):
        valid = {"registro_boe", "statutory"}
        for row in BENEFICIAL_OWNERS:
            assert row[4] in valid
