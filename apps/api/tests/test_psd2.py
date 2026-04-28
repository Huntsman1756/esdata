"""Tests para Fase 31.10 — PSD2/PSD3, SEPA, Consumer Credit, IDD, Solvency II.

Cubre:
- PSD2: ASPSP, AISP, PISP, Consent, Incident Report
- SEPA: Payment Rules
- Consumer Credit: Contracts, Disclosure, Overindebtedness
- IDD: Distributors, UCI Products
- Solvency II: Entities, SFP
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import text

# ===========================================================================
# Seeds
# ===========================================================================

PSD2_SEED_SQL = [
    # ASPSP
    """INSERT INTO psd2_aspsp (entity_id, bic, psd2_license, strong_customer_auth_applied, api_version, regulatory_status, home_member_state)
       VALUES (1, 'BBKIES21', 'PSD-2023-001', true, 'v2', 'registered', 'ES')""",
    """INSERT INTO psd2_aspsp (entity_id, bic, psd2_license, strong_customer_auth_applied, api_version, regulatory_status, home_member_state)
       VALUES (2, 'DEUTDEFF', 'PSD-2023-002', true, 'v2', 'registered', 'DE')""",
    # AISP
    """INSERT INTO psd2_aisp (entity_id, registration_number, registration_id, access_scope, valid_from, valid_to, status)
       VALUES (10, 'AISP-2023-001', 'REG-AISP-001', 'accounts,balances', '2024-01-01', '2025-12-31', 'active')""",
    # PISP
    """INSERT INTO psd2_pisp (entity_id, registration_number, authorization_status, home_member_state, psd3_transition_status)
       VALUES (20, 'PISP-2023-001', 'authorized', 'ES', 'not_started')""",
    # Consent
    """INSERT INTO psd2_consent (client_id, aspsp_id, consent_type, accounts_accessed, payment_count_limit, used_count, valid_from, valid_to, status)
       VALUES (100, 1, 'AIS', '["ES1234567890"]', 10, 3, '2024-06-01', '2024-12-31', 'active')""",
    # Incident
    """INSERT INTO psd2_incident_report (aspsp_id, incident_type, severity, description, reported_to_bde, reported_date)
       VALUES (1, 'authentication_failure', 'high', 'Multiple failed auth attempts from IP range', true, '2024-07-15')""",
    # SEPA
    """INSERT INTO sepa_payment_rule (scheme_version, payment_type, service_level, local_instrument, category_purpose, cut_off_time, settlement_days)
       VALUES ('pain.001.001.03', 'SEPA CT', 'SEPA', 'Core', 'salary', '14:00 CET', 1)""",
    """INSERT INTO sepa_payment_rule (scheme_version, payment_type, service_level, local_instrument, category_purpose, cut_off_time, settlement_days)
       VALUES ('pain.008.001.02', 'SEPA PAIN', 'SEPA', 'Core', 'invoice', '15:00 CET', 1)""",
    # Consumer Credit
    """INSERT INTO consumer_credit_contract (lender_id, borrower_id, credit_type, principal_amount, annual_percentage_rate, total_amount, term_months, purpose, signing_date, status)
       VALUES (1, 100, 'installment', 5000.00, 7.50, 5750.00, 12, 'personal', '2024-01-15', 'active')""",
    """INSERT INTO consumer_credit_contract (lender_id, borrower_id, credit_type, principal_amount, annual_percentage_rate, total_amount, term_months, purpose, signing_date, status)
       VALUES (1, 101, 'revolving', 3000.00, 12.90, 3387.00, 24, 'consumption', '2024-03-01', 'active')""",
    # Disclosure
    """INSERT INTO consumer_credit_disclosure (contract_id, fap, total_cost, regular_payment, right_of_withdrawal, early_repayment_penalty)
       VALUES (1, 8.20, 750.00, 450.00, true, 50.00)""",
    # Overindebtedness
    """INSERT INTO consumer_credit_overindebtedness (borrower_id, declared_date, total_debt, monthly_income, unsecured_debt, procedure_status, court_reference)
       VALUES (102, '2024-05-01', 50000.00, 1200.00, 35000.00, 'declared', 'JUZ-045-2024')""",
    # IDD
    """INSERT INTO idd_distributor (entity_id, registration_number, insurance_ao, products_covered, professional_indemnity, training_certified, status)
       VALUES (50, 'IDD-2023-001', 'AO-2023-001', '["life", "non-life"]', true, true, 'active')""",
    """INSERT INTO idd_distributor (entity_id, registration_number, insurance_ao, products_covered, professional_indemnity, training_certified, status)
       VALUES (51, 'IDD-2023-002', 'AO-2023-002', '["life"]', true, false, 'inactive')""",
    # UCI Product
    """INSERT INTO idd_product_uci (product_id, product_type, risk_coverage, cost_breakdown, exit_costs, taxes, version, status)
       VALUES (1, 'life', 'death, disability', '{"admin": 0.5, "distribution": 1.0}', '2.0', 'IVA excluded', 'v1', 'active')""",
    # Solvency II
    """INSERT INTO solvency_ii_entity (entity_id, entity_type, solvency_capital_requirement, minimum_capital_requirement, solvency_ratio, reporting_date, home_supervisor)
       VALUES (60, 'life', 100000000.00, 50000000.00, 220.50, '2024-12-31', 'Bde')""",
    """INSERT INTO solvency_ii_entity (entity_id, entity_type, solvency_capital_requirement, minimum_capital_requirement, solvency_ratio, reporting_date, home_supervisor)
       VALUES (61, 'non-life', 75000000.00, 30000000.00, 185.00, '2024-12-31', 'Bde')""",
    # SFP
    """INSERT INTO solvency_ii_sfp (entity_id, reporting_period, fund_breakdown, asset_allocation, url, status)
       VALUES (60, '2024-Q4', '{"equity": 60, "bonds": 30, "cash": 10}', '{"govt": 40, "corp": 20, "re": 10}', 'https://example.com/sfp', 'published')""",
]

PSD2_CLEANUP = [
    "DELETE FROM solvency_ii_sfp",
    "DELETE FROM solvency_ii_entity",
    "DELETE FROM idd_product_uci",
    "DELETE FROM idd_distributor",
    "DELETE FROM consumer_credit_overindebtedness",
    "DELETE FROM consumer_credit_disclosure",
    "DELETE FROM consumer_credit_contract",
    "DELETE FROM sepa_payment_rule",
    "DELETE FROM psd2_incident_report",
    "DELETE FROM psd2_consent",
    "DELETE FROM psd2_pisp",
    "DELETE FROM psd2_aisp",
    "DELETE FROM psd2_aspsp",
]


@pytest_asyncio.fixture(autouse=True)
async def _seed_psd2():
    from db import engine
    with engine.begin() as conn:
        for sql in PSD2_SEED_SQL:
            conn.execute(text(sql))
    yield
    with engine.begin() as conn:
        for sql in PSD2_CLEANUP:
            conn.execute(text(sql))


# ===========================================================================
# PSD2 — ASPSP
# ===========================================================================

class TestPsd2Aspsp:
    @pytest.mark.asyncio
    async def test_list_aspsp_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/aspsp")
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_aspsp_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/aspsp/99999")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_aspsp_filter_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/aspsp", params={"regulatory_status": "registered"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["regulatory_status"] == "registered"


# ===========================================================================
# PSD2 — AISP
# ===========================================================================

class TestPsd2Aisp:
    @pytest.mark.asyncio
    async def test_list_aisp_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/aisp")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_aisp_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/aisp/99999")
            assert resp.status_code == 404


# ===========================================================================
# PSD2 — PISP
# ===========================================================================

class TestPsd2Pisp:
    @pytest.mark.asyncio
    async def test_list_pisp_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/pisp")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_pisp_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/pisp/99999")
            assert resp.status_code == 404


# ===========================================================================
# PSD2 — Consent
# ===========================================================================

class TestPsd2Consent:
    @pytest.mark.asyncio
    async def test_list_consent_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/consent")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_consent_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/consent/99999")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_consent_filter_type(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/consent", params={"consent_type": "AIS"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["consent_type"] == "AIS"


# ===========================================================================
# PSD2 — Incidents
# ===========================================================================

class TestPsd2Incidents:
    @pytest.mark.asyncio
    async def test_list_incidents_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/incidents")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_incident_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/incidents/99999")
            assert resp.status_code == 404


# ===========================================================================
# SEPA — Payment Rules
# ===========================================================================

class TestSepaRules:
    @pytest.mark.asyncio
    async def test_list_sepa_rules_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/sepa-rules")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_sepa_rule_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/psd2/sepa-rules/99999")
            assert resp.status_code == 404


# ===========================================================================
# Consumer Credit — Contracts
# ===========================================================================

class TestConsumerCreditContracts:
    @pytest.mark.asyncio
    async def test_list_contracts_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/contracts")
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_contract_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/contracts/99999")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_contracts_filter_type(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/contracts", params={"credit_type": "installment"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["credit_type"] == "installment"


# ===========================================================================
# Consumer Credit — Disclosure
# ===========================================================================

class TestConsumerCreditDisclosure:
    @pytest.mark.asyncio
    async def test_list_disclosures_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/disclosures")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_disclosure_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/disclosures/99999")
            assert resp.status_code == 404


# ===========================================================================
# Consumer Credit — Overindebtedness
# ===========================================================================

class TestConsumerCreditOverindebtedness:
    @pytest.mark.asyncio
    async def test_list_overindebtedness_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/overindebtedness")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_overindebtedness_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/consumer-credit/overindebtedness/99999")
            assert resp.status_code == 404


# ===========================================================================
# IDD — Distributors
# ===========================================================================

class TestIddDistributors:
    @pytest.mark.asyncio
    async def test_list_distributors_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/distributors")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_distributor_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/distributors/99999")
            assert resp.status_code == 404


# ===========================================================================
# IDD — UCI Products
# ===========================================================================

class TestIddUciProducts:
    @pytest.mark.asyncio
    async def test_list_uci_products_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/uci-products")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_uci_product_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/uci-products/99999")
            assert resp.status_code == 404


# ===========================================================================
# Solvency II — Entities
# ===========================================================================

class TestSolvencyEntities:
    @pytest.mark.asyncio
    async def test_list_entities_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/solvency-entities")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_entity_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/solvency-entities/99999")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_entities_filter_type(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/solvency-entities", params={"entity_type": "life"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["entity_type"] == "life"


# ===========================================================================
# Solvency II — SFP
# ===========================================================================

class TestSolvencySfp:
    @pytest.mark.asyncio
    async def test_list_sfp_status_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/solvency-sfp")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_sfp_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/insurance/solvency-sfp/99999")
            assert resp.status_code == 404
