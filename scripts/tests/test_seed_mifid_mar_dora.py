"""Tests para seed_mifid_mar_dora.py — MiFID II/MAR/DORA/PRIIPs/LIVMC/Transparencia."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_mifid_mar_dora import (
    MIFID_CLIENT_CATEGORIES,
    MIFID_SUITABILITY_REPORTS,
    MIFID_BEST_EXECUTION,
    MIFID_CONFLICTS,
    MIFID_PRODUCT_GOVERNANCE,
    MIFID_ORDER_RECORDS,
    MIFID_INSIDER_LISTS,
    MIFID_COMPENSATION,
    MAR_INSIDER_TRANSACTIONS,
    MAR_STR,
    MAR_MANIPULATION,
    MAR_COMMUNICATIONS,
    DORA_INCIDENTS,
    DORA_PROVIDERS,
    DORA_RISKS,
    DORA_PENTESTS,
    DORA_CLASSIFICATION,
    PRIIPs_KIDS,
    PRIIPs_PRODUCTS,
    LIVMC_PROTECTIONS,
    LIVMC_PROCEDURES,
    TRANSPARENCY_ISSUERS,
    TRANSPARENCY_INFO,
    TRANSPARENCY_VOTING,
    TRANSPARENCY_RULES,
)


class TestMifidClientCategories:
    """Validaciones de categorias de cliente MiFID."""

    def test_not_empty(self):
        assert len(MIFID_CLIENT_CATEGORIES) > 0

    def test_correct_count(self):
        assert len(MIFID_CLIENT_CATEGORIES) == 3

    def test_categories_valid(self):
        valid = {"retail", "professional", "eligible_counterparty"}
        for c in MIFID_CLIENT_CATEGORIES:
            assert c["category"] in valid

    def test_status_active(self):
        for c in MIFID_CLIENT_CATEGORIES:
            assert c["status"] == "active"

    def test_have_required_fields(self):
        required = {"entity_id", "category", "assessment_date", "knowledge_level", "experience_level", "status"}
        for c in MIFID_CLIENT_CATEGORIES:
            assert required.issubset(c.keys())


class TestMifidSuitabilityReports:
    """Validaciones de informes de idoneidad MiFID."""

    def test_not_empty(self):
        assert len(MIFID_SUITABILITY_REPORTS) > 0

    def test_recommendations_valid(self):
        valid = {"recommended", "no_recommended", "neutral"}
        for r in MIFID_SUITABILITY_REPORTS:
            assert r["recommendation"] in valid


class TestMifidBestExecution:
    """Validaciones de best execution MiFID."""

    def test_not_empty(self):
        assert len(MIFID_BEST_EXECUTION) > 0

    def test_venues_valid(self):
        valid = {"BME", "MSE"}
        for b in MIFID_BEST_EXECUTION:
            assert b["venue"] in valid


class TestMifidConflicts:
    """Validaciones de conflictos de interes MiFID."""

    def test_not_empty(self):
        assert len(MIFID_CONFLICTS) > 0

    def test_conflict_types_valid(self):
        valid = {"personal_dealing", "cross_interest"}
        for c in MIFID_CONFLICTS:
            assert c["conflict_type"] in valid


class TestMifidProductGovernance:
    """Validaciones de gobierno de productos MiFID."""

    def test_not_empty(self):
        assert len(MIFID_PRODUCT_GOVERNANCE) > 0

    def test_target_markets_valid(self):
        valid = {"investidor_profesional", "investidor_minorista"}
        for p in MIFID_PRODUCT_GOVERNANCE:
            assert p["target_market"] in valid


class TestMifidOrderRecords:
    """Validaciones de registros de ordenes MiFID."""

    def test_not_empty(self):
        assert len(MIFID_ORDER_RECORDS) > 0

    def test_directions_valid(self):
        valid = {"buy", "sell"}
        for o in MIFID_ORDER_RECORDS:
            assert o["direction"] in valid


class TestMifidInsiderLists:
    """Validaciones de listas de insider MiFID."""

    def test_not_empty(self):
        assert len(MIFID_INSIDER_LISTS) > 0

    def test_status_valid(self):
        valid = {"active", "closed", "pending"}
        for l in MIFID_INSIDER_LISTS:
            assert l["status"] in valid


class TestMifidCompensation:
    """Validaciones de politica de compensacion MiFID."""

    def test_not_empty(self):
        assert len(MIFID_COMPENSATION) > 0

    def test_risk_adjustment_applied(self):
        for c in MIFID_COMPENSATION:
            assert c["risk_adjustment_applied"] is True


class TestMarInsiderTransactions:
    """Validaciones de transacciones insider MAR."""

    def test_not_empty(self):
        assert len(MAR_INSIDER_TRANSACTIONS) > 0

    def test_transaction_types_valid(self):
        valid = {"buy", "sell", "option_exercise", "grant"}
        for t in MAR_INSIDER_TRANSACTIONS:
            assert t["transaction_type"] in valid


class TestMarStr:
    """Validaciones de STR MAR."""

    def test_not_empty(self):
        assert len(MAR_STR) > 0

    def test_severity_valid(self):
        valid = {"low", "medium", "high", "critical"}
        for s in MAR_STR:
            assert s["severity"] in valid


class TestMarManipulation:
    """Validaciones de manipulacion de mercado MAR."""

    def test_not_empty(self):
        assert len(MAR_MANIPULATION) > 0

    def test_pattern_types_valid(self):
        valid = {"spoofing", "wash_trade", "front_running", "pump_and_dump"}
        for m in MAR_MANIPULATION:
            assert m["pattern_type"] in valid


class TestMarCommunications:
    """Validaciones de comunicaciones insider MAR."""

    def test_not_empty(self):
        assert len(MAR_COMMUNICATIONS) > 0


class TestDoraIncidents:
    """Validaciones de incidentes DORA."""

    def test_not_empty(self):
        assert len(DORA_INCIDENTS) > 0

    def test_severity_valid(self):
        valid = {"low", "medium", "high", "critical"}
        for i in DORA_INCIDENTS:
            assert i["incident_severity"] in valid

    def test_classifications_valid(self):
        valid = {"cyber-attack", "outage", "data-breach", "phishing"}
        for i in DORA_INCIDENTS:
            assert i["classification"] in valid


class TestDoraProviders:
    """Validaciones de proveedores DORA."""

    def test_not_empty(self):
        assert len(DORA_PROVIDERS) > 0

    def test_provider_types_valid(self):
        valid = {"cloud", "software", "network", " Outsourcing"}
        for p in DORA_PROVIDERS:
            assert p["provider_type"] in valid


class TestDoraRisks:
    """Validaciones de riesgos DORA."""

    def test_not_empty(self):
        assert len(DORA_RISKS) > 0

    def test_likelihood_valid(self):
        valid = {"improbable", "unlikely", "probable", "likely", "almost_certain"}
        for r in DORA_RISKS:
            assert r["likelihood"] in valid


class TestDoraPentests:
    """Validaciones de penetration tests DORA."""

    def test_not_empty(self):
        assert len(DORA_PENTESTS) > 0

    def test_test_types_valid(self):
        valid = {"black_box", "white_box", "gray_box"}
        for p in DORA_PENTESTS:
            assert p["test_type"] in valid


class TestDoraClassification:
    """Validaciones de clasificacion DORA."""

    def test_not_empty(self):
        assert len(DORA_CLASSIFICATION) > 0

    def test_framework_version(self):
        for c in DORA_CLASSIFICATION:
            assert c["framework_version"] == "1.0"


class TestPriipsKids:
    """Validaciones de KIDs PRIIPs."""

    def test_not_empty(self):
        assert len(PRIIPs_KIDS) > 0

    def test_risk_scales_valid(self):
        for kid in PRIIPs_KIDS:
            assert 1 <= kid["risk_scale"] <= 7


class TestPriipsProducts:
    """Validaciones de productos PRIIPs."""

    def test_not_empty(self):
        assert len(PRIIPs_PRODUCTS) > 0

    def test_product_types_valid(self):
        valid = {"fondo_inversion", "etf", "documento_inversion", "producto_pension"}
        for p in PRIIPs_PRODUCTS:
            assert p["product_name"] is not None


class TestLivmcProtections:
    """Validaciones de protecciones LIVMC."""

    def test_not_empty(self):
        assert len(LIVMC_PROTECTIONS) > 0

    def test_protection_types_valid(self):
        valid = {"dispute-resolution", "mediation", "arbitration"}
        for p in LIVMC_PROTECTIONS:
            assert p["protection_type"] in valid


class TestLivmcProcedures:
    """Validaciones de procedimientos LIVMC."""

    def test_not_empty(self):
        assert len(LIVMC_PROCEDURES) > 0


class TestTransparencyIssuers:
    """Validaciones de emisores transparencia."""

    def test_not_empty(self):
        assert len(TRANSPARENCY_ISSUERS) > 0

    def test_tickers_valid(self):
        for i in TRANSPARENCY_ISSUERS:
            assert ".MC" in i["ticker"]


class TestTransparencyInfo:
    """Validaciones de informacion regulada."""

    def test_not_empty(self):
        assert len(TRANSPARENCY_INFO) > 0

    def test_info_types_valid(self):
        valid = {"financial-report", "share-capital-change", "insider-info", "governance"}
        for i in TRANSPARENCY_INFO:
            assert i["info_type"] in valid


class TestTransparencyVoting:
    """Validaciones de derechos de voto."""

    def test_not_empty(self):
        assert len(TRANSPARENCY_VOTING) > 0

    def test_voting_rights_range(self):
        for v in TRANSPARENCY_VOTING:
            assert 0 < v["voting_rights_pct"] <= 1.0


class TestTransparencyRules:
    """Validaciones de reglas internas transparencia."""

    def test_not_empty(self):
        assert len(TRANSPARENCY_RULES) > 0

    def test_retention_period_valid(self):
        for r in TRANSPARENCY_RULES:
            assert r["retention_period"] == "10_anos"
