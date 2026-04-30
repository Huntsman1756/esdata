"""Tests for PGC real worker - Fase 46.3."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pgc_real import PGC_ACCOUNTS_REAL


class TestPGCAccounts:
    """Test PGC accounts structure."""

    def test_has_accounts(self):
        assert len(PGC_ACCOUNTS_REAL) > 0

    def test_accounts_have_required_fields(self):
        required = ["codigo", "descripcion", "nivel", "padre_codigo", "grupo", "clase", "saldo_normal"]
        for cuenta in PGC_ACCOUNTS_REAL:
            for field in required:
                assert field in cuenta, f"Missing field {field} in {cuenta.get('codigo', 'unknown')}"

    def test_accounts_cover_classes_1_and_2(self):
        """Test that accounts cover classes 1 and 2."""
        clases = set(c["clase"] for c in PGC_ACCOUNTS_REAL)
        assert "1" in clases
        assert "2" in clases

    def test_accounts_have_valid_niveles(self):
        """Test that all account levels are valid (1, 2, or 3)."""
        valid_niveles = {1, 2, 3}
        for cuenta in PGC_ACCOUNTS_REAL:
            assert cuenta["nivel"] in valid_niveles, f"Invalid nivel {cuenta['nivel']} for {cuenta['codigo']}"

    def test_accounts_have_valid_saldos(self):
        """Test that all accounts have valid saldo_normal values."""
        valid_saldos = {"Deudor", "Acrecedor"}
        for cuenta in PGC_ACCOUNTS_REAL:
            assert cuenta["saldo_normal"] in valid_saldos, f"Invalid saldo_normal: {cuenta['saldo_normal']}"

    def test_accounts_codes_are_unique(self):
        """Test that all account codes are unique."""
        codigos = [c["codigo"] for c in PGC_ACCOUNTS_REAL]
        assert len(codigos) == len(set(codigos)), "Duplicate account codes"

    def test_class_1_has_parent(self):
        """Test that class 1 accounts have padre_codigo = None or class value."""
        for cuenta in PGC_ACCOUNTS_REAL:
            if cuenta["nivel"] == 1:
                assert cuenta["padre_codigo"] is None or cuenta["padre_codigo"] == cuenta["codigo"]

    def test_class_2_has_parent(self):
        """Test that class 2 accounts have padre_codigo set to class 1 code."""
        for cuenta in PGC_ACCOUNTS_REAL:
            if cuenta["nivel"] == 2:
                assert cuenta["padre_codigo"] is not None
                assert cuenta["padre_codigo"] in ["1", "2"]

    def test_class_3_has_parent(self):
        """Test that class 3 accounts have padre_codigo set to class 2 code."""
        for cuenta in PGC_ACCOUNTS_REAL:
            if cuenta["nivel"] == 3:
                assert cuenta["padre_codigo"] is not None
                assert len(cuenta["padre_codigo"]) == 2

    def test_accounts_have_group_codes(self):
        """Test that all accounts have group codes matching their prefix."""
        for cuenta in PGC_ACCOUNTS_REAL:
            if cuenta.get("grupo"):
                assert cuenta["codigo"].startswith(cuenta["grupo"]), \
                    f"Group {cuenta['grupo']} doesn't match code {cuenta['codigo']}"

    def test_accounts_have_class_codes(self):
        """Test that all accounts have class codes matching their prefix."""
        for cuenta in PGC_ACCOUNTS_REAL:
            assert cuenta["codigo"].startswith(cuenta["clase"]), \
                f"Class {cuenta['clase']} doesn't match code {cuenta['codigo']}"

    def test_no_empty_descriptions(self):
        """Test that no accounts have empty descriptions."""
        for cuenta in PGC_ACCOUNTS_REAL:
            assert cuenta["descripcion"].strip(), f"Empty description for {cuenta['codigo']}"

    def test_accounts_count_reasonable(self):
        """Test that we have a reasonable number of accounts."""
        # We have 100+ accounts covering classes 1 and 2
        assert len(PGC_ACCOUNTS_REAL) >= 100
        assert len(PGC_ACCOUNTS_REAL) <= 500
