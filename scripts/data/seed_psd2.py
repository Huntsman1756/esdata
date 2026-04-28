#!/usr/bin/env python
"""Seed PSD2/PSD3, SEPA, Consumer Credit, IDD, Solvency II data.

Fase 31.10 — Expansion regulatoria.

Fuentes:
- PSD2: EBA register of payment service providers
- SEPA: EPC scheme rules
- Consumer Credit: Directive 2008/48/EC
- IDD: Directive 2016/97/EU
- Solvency II: EIOPA reports

verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

# --- PSD2 ASPSP ---
PSD2_ASPSP = [
    ("1", "BBKIES21", "PSD-2023-001", "true", "v2", "registered", "ES"),
    ("2", "BBVAESMM", "PSD-2023-002", "true", "v2", "registered", "ES"),
    ("3", "BSCHESMM", "PSD-2023-003", "true", "v2", "registered", "ES"),
    ("4", "DEUTDEFF", "PSD-2023-004", "true", "v2", "registered", "DE"),
    ("5", "BNPAFRPP", "PSD-2023-005", "true", "v2", "registered", "FR"),
    ("6", "INGBNL2A", "PSD-2023-006", "true", "v2", "registered", "NL"),
]

# --- PSD2 AISP ---
PSD2_AISP = [
    ("10", "AISP-2023-001", "REG-AISP-001", "accounts,balances,transactions", "2024-01-01", "2025-12-31", "active"),
    ("11", "AISP-2023-002", "REG-AISP-002", "accounts,balances", "2024-03-01", "2025-06-30", "active"),
    ("12", "AISP-2023-003", "REG-AISP-003", "accounts", "2024-06-01", "2025-12-31", "active"),
]

# --- PSD2 PISP ---
PSD2_PISP = [
    ("20", "PISP-2023-001", "authorized", "ES", "not_started"),
    ("21", "PISP-2023-002", "authorized", "ES", "in_transition"),
    ("22", "PISP-2023-003", "authorized", "DE", "not_started"),
]

# --- PSD2 Consent ---
PSD2_CONSENT = [
    (100, 1, "AIS", 2, 10, 3, "2024-06-01", "2024-12-31", "active"),
    (101, 2, "PIS", 1, 5, 1, "2024-07-01", "2024-12-31", "active"),
]

# --- PSD2 Incident ---
PSD2_INCIDENT = [
    ("1", "authentication_failure", "high", "Multiple failed auth attempts from IP range", "true", "2024-07-15"),
    ("2", "api_unavailability", "critical", "ASPSP API down for 4 hours", "true", "2024-08-01"),
]

# --- SEPA Payment Rules ---
SEPA_RULES = [
    ("pain.001.001.03", "SEPA CT", "SEPA", "Core", "salary", "2024-01-01 14:00:00+01", 1),
    ("pain.001.001.03", "SEPA CT", "SEPA", "Corporate", "invoice", "2024-01-01 15:00:00+01", 1),
    ("pain.008.001.02", "SEPA PAIN", "SEPA", "Core", "refund", "2024-01-01 16:00:00+01", 1),
    ("pain.009.001.01", "SEPA Direct Debit", "SEPA", "Core", "utility", "2024-01-01 17:00:00+01", 1),
    ("pain.009.001.01", "SEPA Direct Debit", "SEPA", "B2B", "subscription", "2024-01-01 17:00:00+01", 1),
]

# --- Consumer Credit Contracts ---
CONSUMER_CREDIT = [
    ("1", "100", "installment", 5000.00, 7.50, 5750.00, 12, "personal", "2024-01-15", "active"),
    ("1", "101", "revolving", 3000.00, 12.90, 3387.00, 24, "consumption", "2024-03-01", "active"),
    ("2", "102", "real-secured", 25000.00, 4.50, 27500.00, 60, "home_improvement", "2024-02-01", "active"),
]

# --- Consumer Credit Disclosure ---
CONSUMER_DISCLOSURE = [
    ("1", 8.20, 750.00, 450.00, "true", 50.00),
    ("2", 14.50, 1087.00, 141.13, "true", 75.00),
    ("3", 5.10, 2500.00, 458.33, "true", 100.00),
]

# --- IDD Distributors ---
IDD_DISTRIBUTOR = [
    ("50", "IDD-2023-001", "AO-2023-001", '["life", "non-life"]', "true", "true", "active"),
    ("51", "IDD-2023-002", "AO-2023-002", '["life"]', "true", "false", "inactive"),
    ("52", "IDD-2023-003", "AO-2023-003", '["non-life", "health"]', "true", "true", "active"),
]

# --- IDD UCI Products ---
IDD_UCI = [
    (1, "life", "death, disability, critical illness", 0.5, 2.0, 0.0, 1, "active"),
    (2, "non-life", "property damage, liability", 0.3, 1.5, 0.0, 1, "active"),
]

# --- Solvency II Entities ---
SOLVENCY_ENTITIES = [
    ("60", "life", "100000000.00", "50000000.00", "220.50", "2024-12-31", "Bde"),
    ("61", "non-life", "75000000.00", "30000000.00", "185.00", "2024-12-31", "Bde"),
    ("62", "mixed", "150000000.00", "60000000.00", "195.00", "2024-12-31", "Bde"),
]

SOLVENCY_SFP = [
    ("60", "2024-10-01", '{"equity": 60, "bonds": 30, "cash": 10}', '{"govt": 40, "corp": 20, "re": 10}', "https://example.com/sfp", "published"),
    ("61", "2024-10-01", '{"equity": 40, "bonds": 50, "cash": 10}', '{"govt": 50, "corp": 30, "re": 5}', "https://example.com/sfp-nl", "published"),
]

def seed():
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            for row in PSD2_ASPSP:
                cur.execute(
                    """INSERT INTO psd2_aspsp (entity_id, bic, psd2_license, strong_customer_auth_applied, api_version, regulatory_status, home_member_state)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in PSD2_AISP:
                cur.execute(
                    """INSERT INTO psd2_aisp (entity_id, registration_number, registration_id, access_scope, valid_from, valid_to, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in PSD2_PISP:
                cur.execute(
                    """INSERT INTO psd2_pisp (entity_id, registration_number, authorization_status, home_member_state, psd3_transition_status)
                       VALUES (%s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in PSD2_CONSENT:
                cur.execute(
                    """INSERT INTO psd2_consent (client_id, aspsp_id, consent_type, accounts_accessed, payment_count_limit, used_count, valid_from, valid_to, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in PSD2_INCIDENT:
                cur.execute(
                    """INSERT INTO psd2_incident_report (aspsp_id, incident_type, severity, description, reported_to_bde, reported_date)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in SEPA_RULES:
                cur.execute(
                    """INSERT INTO sepa_payment_rule (scheme_version, payment_type, service_level, local_instrument, category_purpose, cut_off_time, settlement_days)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in CONSUMER_CREDIT:
                cur.execute(
                    """INSERT INTO consumer_credit_contract (lender_id, borrower_id, credit_type, principal_amount, annual_percentage_rate, total_amount, term_months, purpose, signing_date, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in CONSUMER_DISCLOSURE:
                cur.execute(
                    """INSERT INTO consumer_credit_disclosure (contract_id, fap, total_cost, regular_payment, right_of_withdrawal, early_repayment_penalty)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in IDD_DISTRIBUTOR:
                cur.execute(
                    """INSERT INTO idd_distributor (entity_id, registration_number, insurance_ao, products_covered, professional_indemnity, training_certified, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in IDD_UCI:
                cur.execute(
                    """INSERT INTO idd_product_uci (product_id, product_type, risk_coverage, cost_breakdown, exit_costs, taxes, version, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in SOLVENCY_ENTITIES:
                cur.execute(
                    """INSERT INTO solvency_ii_entity (entity_id, entity_type, solvency_capital_requirement, minimum_capital_requirement, solvency_ratio, reporting_date, home_supervisor)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            for row in SOLVENCY_SFP:
                cur.execute(
                    """INSERT INTO solvency_ii_sfp (entity_id, reporting_period, fund_breakdown, asset_allocation, url, status)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       """,
                    row,
                )

            conn.commit()

    print(f"Seeded: {len(PSD2_ASPSP)} ASPSP, {len(PSD2_AISP)} AISP, {len(PSD2_PISP)} PISP, "
          f"{len(PSD2_CONSENT)} consent, {len(PSD2_INCIDENT)} incident, {len(SEPA_RULES)} SEPA rules, "
          f"{len(CONSUMER_CREDIT)} credit contracts, {len(IDD_DISTRIBUTOR)} IDD distributors, "
          f"{len(IDD_UCI)} UCI products, {len(SOLVENCY_ENTITIES)} Solvency II entities, {len(SOLVENCY_SFP)} SFP")


if __name__ == "__main__":
    seed()
