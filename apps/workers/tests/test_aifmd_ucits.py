"""Tests for AIFMD/UCITS worker - Fase 46.9."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aifmd_ucits import (
    SEED_AIFMD_FUNDS,
    SEED_UCITS_FUNDS,
)

class TestSeedAIFMDFunds:
    def test_has_5_funds(self):
        assert len(SEED_AIFMD_FUNDS) == 5

    def test_funds_have_13_fields(self):
        for fund in SEED_AIFMD_FUNDS:
            assert len(fund) == 13

    def test_all_have_fund_names(self):
        for fund in SEED_AIFMD_FUNDS:
            assert fund[0]  # fund_name

    def test_all_active(self):
        for fund in SEED_AIFMD_FUNDS:
            assert fund[12] == "active"

class TestSeedUCITSFunds:
    def test_has_4_funds(self):
        assert len(SEED_UCITS_FUNDS) == 4

    def test_funds_have_11_fields(self):
        for fund in SEED_UCITS_FUNDS:
            assert len(fund) == 11

    def test_all_have_fund_names(self):
        for fund in SEED_UCITS_FUNDS:
            assert fund[0]  # fund_name

    def test_all_active(self):
        for fund in SEED_UCITS_FUNDS:
            assert fund[10] == "active"
