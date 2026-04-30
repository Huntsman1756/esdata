"""Tests for XBRL worker - Fase 46.14."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xbrl import SEED_XBRL_COMPANIES

class TestSeedCompanies:
    def test_has_6_companies(self):
        assert len(SEED_XBRL_COMPANIES) == 6

    def test_companies_have_7_fields(self):
        for comp in SEED_XBRL_COMPANIES:
            assert len(comp) == 7

    def test_all_have_company_names(self):
        for comp in SEED_XBRL_COMPANIES:
            assert comp[1]  # company_name

    def test_all_active(self):
        for comp in SEED_XBRL_COMPANIES:
            assert comp[6] == "active"

    def test_all_cotizada(self):
        for comp in SEED_XBRL_COMPANIES:
            assert comp[2] == "cotizada"
