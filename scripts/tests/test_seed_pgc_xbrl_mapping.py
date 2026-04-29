"""Tests para seed_pgc_xbrl_mapping.py — PGC XBRL mappings."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pgc_xbrl_mapping import MAPPINGS


class TestPgcXbrlMappingData:
    def test_records_not_empty(self):
        assert len(MAPPINGS) > 0

    def test_records_correct_count(self):
        assert len(MAPPINGS) == 54

    def test_records_have_six_fields(self):
        for row in MAPPINGS:
            assert len(row) == 6

    def test_records_xbrl_qname_format(self):
        for row in MAPPINGS:
            assert row[0].startswith("es-gvr:")

    def test_records_account_codes_valid(self):
        for row in MAPPINGS:
            assert row[1].isdigit()
            assert int(row[1]) > 0

    def test_records_confidence_values(self):
        valid = {"high", "medium", "low"}
        for row in MAPPINGS:
            assert row[2] in valid

    def test_records_mapping_type_values(self):
        valid = {"direct", "similar", "derived", "expert"}
        for row in MAPPINGS:
            assert row[3] in valid

    def test_records_note_non_empty(self):
        for row in MAPPINGS:
            assert len(row[4]) > 0

    def test_records_is_active_true(self):
        for row in MAPPINGS:
            assert row[5] is True

    def test_records_xbrl_qnames_unique(self):
        qnames = [r[0] for r in MAPPINGS]
        assert len(qnames) == len(set(qnames))
