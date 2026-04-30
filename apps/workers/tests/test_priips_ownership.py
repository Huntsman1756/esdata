"""Tests for PRIIPs/Ownership worker - Fase 46.16 + 46.17."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from priips_ownership import (
    PRIIPS_NORMAS,
    SEED_PRIIPS_PRODUCTS,
    SEED_PRIIPS_KIDS,
    SEED_OWNERSHIP_RELATIONS,
    SEED_OWNERSHIP_SHARES,
)

class TestPRIIPSNormas:
    def test_has_1_norma(self):
        assert len(PRIIPS_NORMAS) == 1
    def test_norma_has_required_fields(self):
        required = ["codigo", "boe_id", "tipo_documento", "titulo", "ambito", "regulacion"]
        for norma in PRIIPS_NORMAS:
            for field in required:
                assert field in norma
    def test_norma_has_celex_id(self):
        assert PRIIPS_NORMAS[0]["boe_id"].startswith("EUR-CELEX-")
    def test_norma_is_priips_related(self):
        assert PRIIPS_NORMAS[0]["regulacion"] == "priips"

class TestSeedPRIIPSProducts:
    def test_has_4_products(self):
        assert len(SEED_PRIIPS_PRODUCTS) == 4
    def test_all_have_8_fields(self):
        for p in SEED_PRIIPS_PRODUCTS:
            assert len(p) == 8
    def test_all_active(self):
        for p in SEED_PRIIPS_PRODUCTS:
            assert p[7] == "active"

class TestSeedPRIIPSKIDs:
    def test_has_4_kids(self):
        assert len(SEED_PRIIPS_KIDS) == 4
    def test_all_have_9_fields(self):
        for k in SEED_PRIIPS_KIDS:
            assert len(k) == 9
    def test_all_active(self):
        for k in SEED_PRIIPS_KIDS:
            assert k[8] == "active"

class TestSeedOwnershipRelations:
    def test_has_3_relations(self):
        assert len(SEED_OWNERSHIP_RELATIONS) == 3
    def test_all_have_10_fields(self):
        for r in SEED_OWNERSHIP_RELATIONS:
            assert len(r) == 10

class TestSeedOwnershipShares:
    def test_has_3_shares(self):
        assert len(SEED_OWNERSHIP_SHARES) == 3
    def test_all_have_11_fields(self):
        for s in SEED_OWNERSHIP_SHARES:
            assert len(s) == 11
