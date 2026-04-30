"""Tests for MAR/MiFID worker - Fase 46.15."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mar_mifid import (
    SEED_MAR_TRANSACTIONS,
    SEED_MIFID_INSIDER_LISTS,
    SEED_MAR_MANIPULATION,
    SEED_MAR_COMMUNICATIONS,
    SEED_MAR_SUSPICIOUS,
    SEED_MIFID_BEST_EXEC,
    SEED_MIFID_CLIENT_CAT,
    SEED_MIFID_COMPENSATION,
    SEED_MIFID_CONFLICTS,
    SEED_MIFID_ORDERS,
    SEED_MIFID_PRODUCT_GOVERNANCE,
    SEED_MIFID_SUITABILITY,
)

class TestSeedMARTransactions:
    def test_has_5_transactions(self):
        assert len(SEED_MAR_TRANSACTIONS) == 5
    def test_all_have_10_fields(self):
        for t in SEED_MAR_TRANSACTIONS:
            assert len(t) == 10
    def test_all_reported(self):
        for t in SEED_MAR_TRANSACTIONS:
            assert t[9] == "reported"

class TestSeedMIFIDInsiders:
    def test_has_4_lists(self):
        assert len(SEED_MIFID_INSIDER_LISTS) == 4
    def test_all_have_7_fields(self):
        for l in SEED_MIFID_INSIDER_LISTS:
            assert len(l) == 7

class TestSeedMARManipulation:
    def test_has_4_indicators(self):
        assert len(SEED_MAR_MANIPULATION) == 4
    def test_all_have_7_fields(self):
        for i in SEED_MAR_MANIPULATION:
            assert len(i) == 7

class TestSeedMARCommunications:
    def test_has_3_communications(self):
        assert len(SEED_MAR_COMMUNICATIONS) == 3
    def test_all_have_6_fields(self):
        for c in SEED_MAR_COMMUNICATIONS:
            assert len(c) == 6

class TestSeedMARSuspicious:
    def test_has_3_reports(self):
        assert len(SEED_MAR_SUSPICIOUS) == 3
    def test_all_have_8_fields(self):
        for r in SEED_MAR_SUSPICIOUS:
            assert len(r) == 8

class TestSeedMIFIDBestExec:
    def test_has_3_records(self):
        assert len(SEED_MIFID_BEST_EXEC) == 3
    def test_all_have_8_fields(self):
        for r in SEED_MIFID_BEST_EXEC:
            assert len(r) == 8

class TestSeedMIFIDClientCat:
    def test_has_4_records(self):
        assert len(SEED_MIFID_CLIENT_CAT) == 4
    def test_all_have_6_fields(self):
        for r in SEED_MIFID_CLIENT_CAT:
            assert len(r) == 6

class TestSeedMIFIDCompensation:
    def test_has_3_records(self):
        assert len(SEED_MIFID_COMPENSATION) == 3
    def test_all_have_7_fields(self):
        for r in SEED_MIFID_COMPENSATION:
            assert len(r) == 7

class TestSeedMIFIDConflicts:
    def test_has_3_records(self):
        assert len(SEED_MIFID_CONFLICTS) == 3
    def test_all_have_7_fields(self):
        for r in SEED_MIFID_CONFLICTS:
            assert len(r) == 7

class TestSeedMIFIDOrders:
    def test_has_3_records(self):
        assert len(SEED_MIFID_ORDERS) == 3
    def test_all_have_9_fields(self):
        for r in SEED_MIFID_ORDERS:
            assert len(r) == 9

class TestSeedMIFIDProductGovernance:
    def test_has_3_records(self):
        assert len(SEED_MIFID_PRODUCT_GOVERNANCE) == 3
    def test_all_have_7_fields(self):
        for r in SEED_MIFID_PRODUCT_GOVERNANCE:
            assert len(r) == 7

class TestSeedMIFIDSuitability:
    def test_has_3_records(self):
        assert len(SEED_MIFID_SUITABILITY) == 3
    def test_all_have_7_fields(self):
        for r in SEED_MIFID_SUITABILITY:
            assert len(r) == 7
