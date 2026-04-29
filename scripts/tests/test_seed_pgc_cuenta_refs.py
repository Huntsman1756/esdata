"""Tests para seed_pgc_cuenta_refs.py — PGC account fiscal and AEAT model references."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pgc_cuenta_refs import FISCAL_REFS, AEAT_MODEL_REFS


class TestPgcFiscalRefsData:
    def test_fiscal_refs_not_empty(self):
        assert len(FISCAL_REFS) > 0

    def test_fiscal_refs_correct_count(self):
        assert len(FISCAL_REFS) == 66

    def test_fiscal_refs_have_five_fields(self):
        for row in FISCAL_REFS:
            assert len(row) == 5

    def test_fiscal_refs_cuenta_numeric(self):
        for row in FISCAL_REFS:
            assert row[0].isdigit()

    def test_fiscal_refs_modelo_numeric(self):
        for row in FISCAL_REFS:
            assert row[1].isdigit()

    def test_fiscal_refs_notes_non_empty(self):
        for row in FISCAL_REFS:
            assert len(row[4]) > 0


class TestPgcAeatModelRefsData:
    def test_aeat_refs_not_empty(self):
        assert len(AEAT_MODEL_REFS) > 0

    def test_aeat_refs_correct_count(self):
        assert len(AEAT_MODEL_REFS) == 51

    def test_aeat_refs_have_four_fields(self):
        for row in AEAT_MODEL_REFS:
            assert len(row) == 4

    def test_aeat_refs_cuenta_numeric(self):
        for row in AEAT_MODEL_REFS:
            assert row[0].isdigit()

    def test_aeat_refs_modelo_numeric(self):
        for row in AEAT_MODEL_REFS:
            assert row[1].isdigit()

    def test_aeat_refs_notes_non_empty(self):
        for row in AEAT_MODEL_REFS:
            assert len(row[3]) > 0
