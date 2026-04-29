"""Tests para seed_pbc.py — PBC/FT data (prevencion blanqueo capitales)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_pbc import SUBJECTS_DATA, CONTROLS_DATA, SAR_DATA, BENEFICIAL_OWNER_DATA


class TestPbcSubjectsData:
    def test_subjects_not_empty(self):
        assert len(SUBJECTS_DATA) > 0

    def test_subjects_correct_count(self):
        assert len(SUBJECTS_DATA) == 6

    def test_subjects_have_six_fields(self):
        for row in SUBJECTS_DATA:
            assert len(row) == 6

    def test_subjects_have_required_keys(self):
        required = {"subject_type", "tin", "registration_number", "supervisory_authority", "pbc_license", "status"}
        for row in SUBJECTS_DATA:
            assert required.issubset(row.keys())

    def test_subjects_tin_format(self):
        for row in SUBJECTS_DATA:
            assert row["tin"].startswith("ESA")
            assert len(row["tin"]) == 11

    def test_subjects_status_valid(self):
        valid = {"active", "inactive", "suspended"}
        for row in SUBJECTS_DATA:
            assert row["status"] in valid

    def test_subjects_types_valid(self):
        valid = {"credit_institution", "investment_firm", "insurance_company", "trust_company", "crypto_asset_service", "real_estate_agency"}
        for row in SUBJECTS_DATA:
            assert row["subject_type"] in valid


class TestPbcControlsData:
    def test_controls_not_empty(self):
        assert len(CONTROLS_DATA) > 0

    def test_controls_correct_count(self):
        assert len(CONTROLS_DATA) == 6

    def test_controls_have_six_fields(self):
        for row in CONTROLS_DATA:
            assert len(row) == 6

    def test_controls_have_required_keys(self):
        required = {"obligated_subject_id", "risk_assessment_date", "compliance_officer", "internal_reporting_channel", "training_program", "audit_trail"}
        for row in CONTROLS_DATA:
            assert required.issubset(row.keys())

    def test_controls_booleans(self):
        for row in CONTROLS_DATA:
            assert isinstance(row["internal_reporting_channel"], bool)
            assert isinstance(row["training_program"], bool)
            assert isinstance(row["audit_trail"], bool)


class TestPbcSARData:
    def test_sars_not_empty(self):
        assert len(SAR_DATA) > 0

    def test_sars_correct_count(self):
        assert len(SAR_DATA) == 5

    def test_sars_have_six_fields(self):
        for row in SAR_DATA:
            assert len(row) == 6

    def test_sars_have_required_keys(self):
        required = {"submission_date", "description", "severity", "status", "sepblac_reference"}
        for row in SAR_DATA:
            assert required.issubset(row.keys())

    def test_sars_severity_valid(self):
        valid = {"low", "medium", "high", "critical"}
        for row in SAR_DATA:
            assert row["severity"] in valid

    def test_sars_status_valid(self):
        valid = {"filed", "under_review", "escalated", "closed"}
        for row in SAR_DATA:
            assert row["status"] in valid

    def test_sars_sepblac_format(self):
        for row in SAR_DATA:
            assert row["sepblac_reference"].startswith("SAR-2025-")


class TestPbcBeneficialOwnersData:
    def test_owners_not_empty(self):
        assert len(BENEFICIAL_OWNER_DATA) > 0

    def test_owners_correct_count(self):
        assert len(BENEFICIAL_OWNER_DATA) == 7

    def test_owners_have_six_fields(self):
        for row in BENEFICIAL_OWNER_DATA:
            assert len(row) == 6

    def test_owners_have_required_keys(self):
        required = {"owner_name", "ownership_percentage", "acquisition_date", "verification_method", "verification_date"}
        for row in BENEFICIAL_OWNER_DATA:
            assert required.issubset(row.keys())

    def test_owners_percentages_valid(self):
        for row in BENEFICIAL_OWNER_DATA:
            assert 0 < row["ownership_percentage"] <= 100

    def test_owners_verification_methods(self):
        valid = {"dni_verificado", "registro_mercantil", "escritura_publica", "comunicacion_cnmv"}
        for row in BENEFICIAL_OWNER_DATA:
            assert row["verification_method"] in valid
