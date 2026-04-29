"""Tests para seed_screening_worker.py — Screening (sanctions, PEPs, watchlists)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_screening_worker import LISTS_DATA, ENTRIES_DATA


class TestScreeningLists:
    """Validaciones de las listas de screening."""

    def test_lists_not_empty(self):
        assert len(LISTS_DATA) > 0

    def test_lists_correct_count(self):
        assert len(LISTS_DATA) == 5

    def test_lists_have_nine_fields(self):
        for row in LISTS_DATA:
            assert len(row) == 9, f"Row has {len(row)} fields: {row}"

    def test_lists_have_unique_codigos(self):
        codigos = [row[0] for row in LISTS_DATA]
        assert len(codigos) == len(set(codigos))

    def test_lists_tipo_valid(self):
        valid = {"sanctions", "watchlist", "pep"}
        for row in LISTS_DATA:
            assert row[2] in valid, f"Invalid tipo: {row[2]}"

    def test_lists_pais_valid(self):
        valid = {"US", "EU", "UN", "ES"}
        for row in LISTS_DATA:
            assert row[4] in valid, f"Invalid pais: {row[4]}"

    def test_lists_all_active(self):
        for row in LISTS_DATA:
            assert row[8] is True

    def test_list_ofac_sdn_exists(self):
        codigos = [row[0] for row in LISTS_DATA]
        assert "OFAC_SDN" in codigos

    def test_list_eu_sanctions_exists(self):
        codigos = [row[0] for row in LISTS_DATA]
        assert "EU_SANCTIONS" in codigos

    def test_list_sepblac_exists(self):
        codigos = [row[0] for row in LISTS_DATA]
        assert "SEPBLAC" in codigos

    def test_list_es_peps_exists(self):
        codigos = [row[0] for row in LISTS_DATA]
        assert "ES_PEPS" in codigos


class TestScreeningEntries:
    """Validaciones de las entradas de screening."""

    def test_entries_not_empty(self):
        assert len(ENTRIES_DATA) > 0

    def test_entries_correct_count(self):
        assert len(ENTRIES_DATA) == 14

    def test_entries_have_sixteen_fields(self):
        for row in ENTRIES_DATA:
            assert len(row) == 16, f"Row has {len(row)} fields: {row}"

    def test_entries_have_unique_entidad_ids(self):
        ids = [row[1] for row in ENTRIES_DATA]
        assert len(ids) == len(set(ids))

    def test_entries_all_have_list_ids(self):
        for row in ENTRIES_DATA:
            assert row[0] in ("OFAC_SDN", "EU_SANCTIONS", "UN_SANCTIONS", "SEPBLAC", "ES_PEPS")

    def test_entries_names_not_empty(self):
        for row in ENTRIES_DATA:
            assert len(row[2]) > 0, "Entry name should not be empty"

    def test_entries_types_valid(self):
        valid = {"entity", "person"}
        for row in ENTRIES_DATA:
            assert row[4] in valid, f"Invalid tipo_entidad: {row[4]}"

    def test_entries_all_active(self):
        for row in ENTRIES_DATA:
            assert row[14] is True

    def test_entries_have_aliases(self):
        for row in ENTRIES_DATA:
            assert isinstance(row[8], list)
            assert len(row[8]) > 0

    def test_entries_have_categories(self):
        for row in ENTRIES_DATA:
            assert isinstance(row[9], list)
            assert len(row[9]) > 0

    def test_entries_have_metadata_json(self):
        for row in ENTRIES_DATA:
            assert row[15] is not None
