#!/usr/bin/env python3
"""Backfill chunks for Fase 31 regulatory domains (MiCA, DAC8/DAC9, Ley 10/2010, Ley 11/2021, MiFID II, MAR, DORA, PRIIPs, Transparencia).

Idempotent: uses UNIQUE(documento_origen_tipo, documento_origen_id, chunk_index)
to skip already-chunked documents on re-run.

Domains covered:
  - mica: casp, crypto_asset, tokenized_asset, wallet_custodian, crypto_transaction
  - dac: dac_reporting_entity, dac_crypto_report, dac_wallet_holder
  - pbc: pbc_obligated_subject, pbc_internal_control, suspicious_activity_report, beneficial_owner_record
  - fraud: fraud_prevention_program, fraud_risk_assessment, fraud_incident
  - mifid: mifid_client_category, mifid_suitability_report, mifid_best_execution_record,
           mifid_conflict_of_interest_registry, mifid_product_governance, mifid_order_record,
           mifid_insider_list, mifid_compensation_policy
  - mar: mar_insider_transaction, mar_suspicious_transaction_report,
         mar_market_manipulation_indicator, mar_insider_communication
  - dora: dora_tic_incident, dora_third_party_provider, dora_ict_risk_register,
          dora_penetration_test, dora_incident_classification_framework
  - priips: priips_kid, priips_product, livmc_client_protection, livmc_voice_procedure
  - transparency: transparency_issuer, transparency_regulated_information,
                  transparency_voting_rights, transparency_internal_rule

Usage:
    # Dry-run for all 31.x domains
    python scripts/data/backfill_31x_chunks.py --dry-run

    # Backfill a specific domain
    python scripts/data/backfill_31x_chunks.py --corpus mica
    python scripts/data/backfill_31x_chunks.py --corpus dac
    python scripts/data/backfill_31x_chunks.py --corpus pbc
    python scripts/data/backfill_31x_chunks.py --corpus fraud
    python scripts/data/backfill_31x_chunks.py --corpus mifid
    python scripts/data/backfill_31x_chunks.py --corpus mar
    python scripts/data/backfill_31x_chunks.py --corpus dora
    python scripts/data/backfill_31x_chunks.py --corpus priips
    python scripts/data/backfill_31x_chunks.py --corpus transparency

    # Backfill everything
    python scripts/data/backfill_31x_chunks.py --corpus all

    # Backfill a single table
    python scripts/data/backfill_31x_chunks.py --table casp

    # Backfill with custom chunk size (default 1500)
    python scripts/data/backfill_31x_chunks.py --corpus all --chunk-size 2000

    # Custom database URL
    python scripts/data/backfill_31x_chunks.py --database-url postgresql+psycopg://...
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from sqlalchemy import create_engine, text

# ── Domain queries: one per table, returns rows to chunk ───────────

DOMAIN_QUERIES: dict[str, dict[str, str]] = {
    "casp": """
        SELECT id, name, registration_number, home_member_state,
               passport_active, services_offered, status, created_at
        FROM casp ORDER BY id
    """,
    "crypto_asset": """
        SELECT id, asset_type, reference_uid, issuer_jurisdiction,
               is_sha, market_value_eur, holders_count, status, created_at
        FROM crypto_asset ORDER BY id
    """,
    "tokenized_asset": """
        SELECT id, underlying_type, issuer_id, face_value, total_amount,
               listing_date, regulated_market, status, created_at
        FROM tokenized_asset ORDER BY id
    """,
    "wallet_custodian": """
        SELECT id, entity_id, wallet_type, custody_mechanism,
               insurance_coverage, audit_frequency, status, created_at
        FROM wallet_custodian ORDER BY id
    """,
    "dac_reporting_entity": """
        SELECT id, tin, entity_type, member_state,
               dac8_registered, dac9_registered, status, created_at
        FROM dac_reporting_entity ORDER BY id
    """,
    "dac_crypto_report": """
        SELECT id, entity_id, reporting_period, submitted_at,
               status, crypto_transactions_count, wallet_holders_count, created_at
        FROM dac_crypto_report ORDER BY id
    """,
    "dac_wallet_holder": """
        SELECT id, report_id, wallet_address, holder_tin, holder_member_state,
               holder_type, total_value_eur, verification_status, created_at
        FROM dac_wallet_holder ORDER BY id
    """,
    "pbc_obligated_subject": """
        SELECT id, subject_type, tin, registration_number,
               supervisory_authority, pbc_license, status, created_at
        FROM pbc_obligated_subject ORDER BY id
    """,
    "pbc_internal_control": """
        SELECT id, obligated_subject_id, risk_assessment_date, compliance_officer,
               internal_reporting_channel, training_program, audit_trail, created_at
        FROM pbc_internal_control ORDER BY id
    """,
    "suspicious_activity_report": """
        SELECT id, obligated_subject_id, submission_date, description,
               severity, status, sepblac_reference, created_at
        FROM suspicious_activity_report ORDER BY id
    """,
    "beneficial_owner_record": """
        SELECT id, entity_id, owner_name, ownership_percentage,
               acquisition_date, verification_method, verification_date, created_at
        FROM beneficial_owner_record ORDER BY id
    """,
    "fraud_prevention_program": """
        SELECT id, entity_id, code_of_conduct, internal_reporting_system,
               training_schedule, audit_frequency, compliance_officer_name, status, created_at
        FROM fraud_prevention_program ORDER BY id
    """,
    "fraud_risk_assessment": """
        SELECT id, entity_id, assessment_date, risk_areas,
               mitigation_measures, next_review_date, created_at
        FROM fraud_risk_assessment ORDER BY id
    """,
    "fraud_incident": """
        SELECT id, entity_id, incident_date, description, amount_eur,
               status, resolution_date, regulatory_notification, created_at
        FROM fraud_incident ORDER BY id
    """,
    # --- MiFID II/MiFIR ---
    "mifid_client_category": """
        SELECT id, entity_id, category, assessment_date,
               knowledge_level, experience_level, status, created_at
        FROM mifid_client_category ORDER BY id
    """,
    "mifid_suitability_report": """
        SELECT id, client_id, product_id, assessment_date,
               suitability_score, recommendation, advisor_id, status, created_at
        FROM mifid_suitability_report ORDER BY id
    """,
    "mifid_best_execution_record": """
        SELECT id, order_id, venue, execution_price,
               market_impact, speed_ms, quality_metrics, execution_timestamp, status, created_at
        FROM mifid_best_execution_record ORDER BY id
    """,
    "mifid_conflict_of_interest_registry": """
        SELECT id, department, conflict_type, description,
               mitigation_measure, identified_date, review_date, status, created_at
        FROM mifid_conflict_of_interest_registry ORDER BY id
    """,
    "mifid_product_governance": """
        SELECT id, product_id, target_market, distribution_channels,
               key_features, risk_level, review_date, status, created_at
        FROM mifid_product_governance ORDER BY id
    """,
    "mifid_order_record": """
        SELECT id, client_id, instrument, direction, quantity,
               price, timestamp, venue, status, retention_until, created_at
        FROM mifid_order_record ORDER BY id
    """,
    "mifid_insider_list": """
        SELECT id, insider_name, insider_tin, entity_id,
               inside_information_description, date_created, date_removed, status, created_at
        FROM mifid_insider_list ORDER BY id
    """,
    "mifid_compensation_policy": """
        SELECT id, entity_id, policy_version, alignment_score,
               risk_adjustment_applied, approval_date, next_review, status, created_at
        FROM mifid_compensation_policy ORDER BY id
    """,
    # --- MAR ---
    "mar_insider_transaction": """
        SELECT id, ppi_name, ppi_role, instrument,
               transaction_type, quantity, value_eur, price, date_time, country, status, created_at
        FROM mar_insider_transaction ORDER BY id
    """,
    "mar_suspicious_transaction_report": """
        SELECT id, entity_id, instrument, pattern_description,
               detection_method, severity, submitted_to_cnmv, cnmv_reference, status, created_at
        FROM mar_suspicious_transaction_report ORDER BY id
    """,
    "mar_market_manipulation_indicator": """
        SELECT id, pattern_type, instrument, time_window,
               volume_anomaly_pct, price_anomaly_pct, confidence_score, status, created_at
        FROM mar_market_manipulation_indicator ORDER BY id
    """,
    "mar_insider_communication": """
        SELECT id, sender_id, receiver_id, content_summary,
               timestamp, channel, inside_info_reference, created_at
        FROM mar_insider_communication ORDER BY id
    """,
    # --- DORA ---
    "dora_tic_incident": """
        SELECT id, entity_id, incident_severity, description,
               impact_scope, detection_date, resolution_date, root_cause, classification, status, created_at
        FROM dora_tic_incident ORDER BY id
    """,
    "dora_third_party_provider": """
        SELECT id, provider_name, provider_type,
               criticality_assessment, contract_start, contract_end,
               eu_supervision_status, exit_strategy, status, created_at
        FROM dora_third_party_provider ORDER BY id
    """,
    "dora_ict_risk_register": """
        SELECT id, entity_id, risk_description,
               likelihood, impact, mitigation, owner, review_date, status, created_at
        FROM dora_ict_risk_register ORDER BY id
    """,
    "dora_penetration_test": """
        SELECT id, entity_id, test_type, tester,
               test_date, findings_count, critical_findings, remediation_deadline, status, created_at
        FROM dora_penetration_test ORDER BY id
    """,
    "dora_incident_classification_framework": """
        SELECT id, framework_version, severity_thresholds,
               reporting_timelines, effective_date, status, created_at
        FROM dora_incident_classification_framework ORDER BY id
    """,
    # --- PRIIPs / LIVMC ---
    "priips_kid": """
        SELECT id, product_id, product_type, currency,
               risk_scale, cost_impact, negative_scenario_returns,
               version, publication_date, status, created_at
        FROM priips_kid ORDER BY id
    """,
    "priips_product": """
        SELECT id, issuer_id, product_name, underlying_assets,
               maturity_date, currency, min_investment,
               distribution_channels, status, created_at
        FROM priips_product ORDER BY id
    """,
    "livmc_client_protection": """
        SELECT id, client_id, protection_type,
               provider_id, coverage_amount, status, created_at
        FROM livmc_client_protection ORDER BY id
    """,
    "livmc_voice_procedure": """
        SELECT id, entity_id, procedure_type,
               description, effective_date, next_review, status, created_at
        FROM livmc_voice_procedure ORDER BY id
    """,
    # --- Transparencia ---
    "transparency_issuer": """
        SELECT id, issuer_id, listing_market, ticker,
               reporting_frequency, home_member_state, status, created_at
        FROM transparency_issuer ORDER BY id
    """,
    "transparency_regulated_information": """
        SELECT id, issuer_id, info_type,
               publication_date, content_url, filing_reference, status, created_at
        FROM transparency_regulated_information ORDER BY id
    """,
    "transparency_voting_rights": """
        SELECT id, issuer_id, shareholder_id,
               voting_rights_pct, date_acquired, date_reported, status, created_at
        FROM transparency_voting_rights ORDER BY id
    """,
    "transparency_internal_rule": """
        SELECT id, entity_id, designated_persons,
               internal_procedure, retention_period, status, created_at
        FROM transparency_internal_rule ORDER BY id
    """,
    # --- SFDR (31.9.1) ---
    "sfdr_product": """
        SELECT id, product_name, product_type, sustainability_strategy,
               principal_adverse_impact, paci_aggregated, paci_detailed_url,
               distribution_country, status, created_at
        FROM sfdr_product ORDER BY id
    """,
    "sfdr_paci_indicator": """
        SELECT id, product_id, indicator_code, indicator_name,
               value, unit, reference_period, methodology, status, created_at
        FROM sfdr_paci_indicator ORDER BY id
    """,
    "sfdr_entity_paci": """
        SELECT id, entity_id, reporting_year, aggregated_paci,
               sectoral_decarbonization, status, created_at
        FROM sfdr_entity_paci ORDER BY id
    """,
    "sfdr_pre_contractual": """
        SELECT id, product_id, document_type, url,
               published_date, version, status, created_at
        FROM sfdr_pre_contractual ORDER BY id
    """,
    "sfdr_annual_report": """
        SELECT id, entity_id, reporting_year, paci_results,
               engagement_activities, good_practice_examples, url,
               published_date, status, created_at
        FROM sfdr_annual_report ORDER BY id
    """,
    # --- CSRD (31.9.2) ---
    "csrd_entity_report": """
        SELECT id, entity_id, reporting_year, esap_url,
               assurance_status, reporting_standard, status, created_at
        FROM csrd_entity_report ORDER BY id
    """,
    "csrd_esg_data_point": """
        SELECT id, report_id, topic, indicator_code,
               value, unit, scope, verification_status, created_at
        FROM csrd_esg_data_point ORDER BY id
    """,
    "csrd_ess": """
        SELECT id, standard_code, topic,
               applicable_from_year, description, status, created_at
        FROM csrd_ess ORDER BY id
    """,
    "csrd_double_materiality": """
        SELECT id, entity_id, impact_materiality,
               financial_materiality, assessment_date, key_impacts,
               key_dependencies, status, created_at
        FROM csrd_double_materiality ORDER BY id
    """,
    # --- AIFMD/UCITS (31.9.3) ---
    "aifmd_fund": """
        SELECT id, fund_name, aifm_id, fund_type, registration_date,
               home_member_state, cross_border_passport, total_aum_eur,
               investor_type, lock_up_period, redemption_frequency,
               leverage_method, leverage_max_pct, status, created_at
        FROM aifmd_fund ORDER BY id
    """,
    "ucits_fund": """
        SELECT id, fund_name, management_company, registration_date,
               home_member_state, cross_border_passport, total_aum_eur,
               depositary_id, krid_url, investment_strategy,
               risk_profile, status, created_at
        FROM ucits_fund ORDER BY id
    """,
    "aifmd_regulatory_report": """
        SELECT id, fund_id, report_type, reporting_period,
               url, filed_date, status, created_at
        FROM aifmd_regulatory_report ORDER BY id
    """,
    "ucits_regulatory_report": """
        SELECT id, fund_id, report_type, reporting_period,
               url, filed_date, status, created_at
        FROM ucits_regulatory_report ORDER BY id
    """,
    "aifmd_liquidity_management": """
        SELECT id, fund_id, redemption_suspended, suspension_date,
               gating_applied, swing_price_applied, side_pocket_applied,
               stress_test_result, valuation_frequency, created_at
        FROM aifmd_liquidity_management ORDER BY id
    """,
    # --- CRD/CRR/BRRD/EMIR (31.9.4) ---
    "crd_capital_position": """
        SELECT id, entity_id, reporting_date, cet1_ratio, tier1_ratio,
               total_capital_ratio, cet1_amount, tier1_amount,
               total_capital_amount, leverage_ratio,
               risk_weighted_assets, status, created_at
        FROM crd_capital_position ORDER BY id
    """,
    "crd_stress_test": """
        SELECT id, entity_id, test_date, scenario_name,
               cet1_impact_pct, tier1_impact_pct, capital_ratio_post_test,
               competent_authority, status, created_at
        FROM crd_stress_test ORDER BY id
    """,
    "brrd_bail_in": """
        SELECT id, entity_id, total_eligible_liabilities,
               mrel_target_pct, mrel_compliance_pct, internal_mrel,
               resolution_status, status, created_at
        FROM brrd_bail_in ORDER BY id
    """,
    "emir_trade_report": """
        SELECT id, trade_id, asset_class, instrument_class,
               clearing_obligation_applied, reporting_delay_days,
               counterparty_type, status, created_at
        FROM emir_trade_report ORDER BY id
    """,
    "emir_clearing_member": """
        SELECT id, entity_id, emir_registration,
               clearing_type, status, created_at
        FROM emir_clearing_member ORDER BY id
    """,
}

# Map table -> domain label for documento_origen_tipo
TABLE_DOMAIN_MAP: dict[str, str] = {
    "casp": "mica",
    "crypto_asset": "mica",
    "tokenized_asset": "mica",
    "wallet_custodian": "mica",
    "dac_reporting_entity": "dac",
    "dac_crypto_report": "dac",
    "dac_wallet_holder": "dac",
    "pbc_obligated_subject": "pbc",
    "pbc_internal_control": "pbc",
    "suspicious_activity_report": "pbc",
    "beneficial_owner_record": "pbc",
    "fraud_prevention_program": "fraud",
    "fraud_risk_assessment": "fraud",
    "fraud_incident": "fraud",
    "mifid_client_category": "mifid",
    "mifid_suitability_report": "mifid",
    "mifid_best_execution_record": "mifid",
    "mifid_conflict_of_interest_registry": "mifid",
    "mifid_product_governance": "mifid",
    "mifid_order_record": "mifid",
    "mifid_insider_list": "mifid",
    "mifid_compensation_policy": "mifid",
    "mar_insider_transaction": "mar",
    "mar_suspicious_transaction_report": "mar",
    "mar_market_manipulation_indicator": "mar",
    "mar_insider_communication": "mar",
    "dora_tic_incident": "dora",
    "dora_third_party_provider": "dora",
    "dora_ict_risk_register": "dora",
    "dora_penetration_test": "dora",
    "dora_incident_classification_framework": "dora",
    "priips_kid": "priips",
    "priips_product": "priips",
    "livmc_client_protection": "priips",
    "livmc_voice_procedure": "priips",
    "transparency_issuer": "transparency",
    "transparency_regulated_information": "transparency",
    "transparency_voting_rights": "transparency",
    "transparency_internal_rule": "transparency",
    "sfdr_product": "sfdr",
    "sfdr_paci_indicator": "sfdr",
    "sfdr_entity_paci": "sfdr",
    "sfdr_pre_contractual": "sfdr",
    "sfdr_annual_report": "sfdr",
    "csrd_entity_report": "csrd",
    "csrd_esg_data_point": "csrd",
    "csrd_ess": "csrd",
    "csrd_double_materiality": "csrd",
    "aifmd_fund": "aifmd_ucits",
    "ucits_fund": "aifmd_ucits",
    "aifmd_regulatory_report": "aifmd_ucits",
    "ucits_regulatory_report": "aifmd_ucits",
    "aifmd_liquidity_management": "aifmd_ucits",
    "crd_capital_position": "crd_brrd_emir",
    "crd_stress_test": "crd_brrd_emir",
    "brrd_bail_in": "crd_brrd_emir",
    "emir_trade_report": "crd_brrd_emir",
    "emir_clearing_member": "crd_brrd_emir",
}

DOMAIN_TABLES: dict[str, list[str]] = {
    "mica": ["casp", "crypto_asset", "tokenized_asset", "wallet_custodian"],
    "dac": ["dac_reporting_entity", "dac_crypto_report", "dac_wallet_holder"],
    "pbc": ["pbc_obligated_subject", "pbc_internal_control", "suspicious_activity_report", "beneficial_owner_record"],
    "fraud": ["fraud_prevention_program", "fraud_risk_assessment", "fraud_incident"],
    "mifid": ["mifid_client_category", "mifid_suitability_report", "mifid_best_execution_record",
              "mifid_conflict_of_interest_registry", "mifid_product_governance", "mifid_order_record",
              "mifid_insider_list", "mifid_compensation_policy"],
    "mar": ["mar_insider_transaction", "mar_suspicious_transaction_report",
            "mar_market_manipulation_indicator", "mar_insider_communication"],
    "dora": ["dora_tic_incident", "dora_third_party_provider", "dora_ict_risk_register",
             "dora_penetration_test", "dora_incident_classification_framework"],
    "priips": ["priips_kid", "priips_product", "livmc_client_protection", "livmc_voice_procedure"],
    "transparency": ["transparency_issuer", "transparency_regulated_information",
                     "transparency_voting_rights", "transparency_internal_rule"],
    "sfdr": ["sfdr_product", "sfdr_paci_indicator", "sfdr_entity_paci", "sfdr_pre_contractual", "sfdr_annual_report"],
    "csrd": ["csrd_entity_report", "csrd_esg_data_point", "csrd_ess", "csrd_double_materiality"],
    "aifmd_ucits": ["aifmd_fund", "ucits_fund", "aifmd_regulatory_report", "ucits_regulatory_report", "aifmd_liquidity_management"],
    "crd_brrd_emir": ["crd_capital_position", "crd_stress_test", "brrd_bail_in", "emir_trade_report", "emir_clearing_member"],
}

# ── Search text builders ──────────────────────────────────────────

def _build_search_text(table: str, row: dict) -> str:
    """Build searchable text from a row dict for the given table."""
    parts: list[str] = []

    if table == "casp":
        if row.get("name"):
            parts.append(row["name"])
        if row.get("registration_number"):
            parts.append(row["registration_number"])
        if row.get("home_member_state"):
            parts.append(row["home_member_state"])
        if row.get("passport_active"):
            parts.append("passport" if row["passport_active"] else "no-passport")
        if row.get("services_offered"):
            svc = row["services_offered"]
            if isinstance(svc, str):
                parts.append(svc)
            elif isinstance(svc, list):
                parts.append(" ".join(str(s) for s in svc))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "crypto_asset":
        for field in ("asset_type", "reference_uid", "issuer_jurisdiction"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("is_sha"):
            parts.append("significant")
        if row.get("market_value_eur"):
            parts.append(str(row["market_value_eur"]))
        if row.get("holders_count"):
            parts.append(str(row["holders_count"]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "tokenized_asset":
        for field in ("underlying_type", "regulated_market"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("issuer_id"):
            parts.append(f"issuer:{row['issuer_id']}")
        if row.get("face_value"):
            parts.append(str(row["face_value"]))
        if row.get("total_amount"):
            parts.append(str(row["total_amount"]))
        if row.get("listing_date"):
            parts.append(str(row["listing_date"]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "wallet_custodian":
        for field in ("wallet_type", "custody_mechanism", "audit_frequency"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("insurance_coverage"):
            parts.append(str(row["insurance_coverage"]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "dac_reporting_entity":
        for field in ("tin", "entity_type", "member_state"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("dac8_registered"):
            parts.append("dac8" if row["dac8_registered"] else "no-dac8")
        if row.get("dac9_registered"):
            parts.append("dac9" if row["dac9_registered"] else "no-dac9")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "dac_crypto_report":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("reporting_period"):
            parts.append(row["reporting_period"])
        if row.get("status"):
            parts.append(row["status"])
        if row.get("crypto_transactions_count"):
            parts.append(f"txns:{row['crypto_transactions_count']}")
        if row.get("wallet_holders_count"):
            parts.append(f"holders:{row['wallet_holders_count']}")

    elif table == "dac_wallet_holder":
        for field in ("wallet_address", "holder_tin", "holder_member_state", "holder_type"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("report_id"):
            parts.append(f"report:{row['report_id']}")
        if row.get("total_value_eur"):
            parts.append(str(row["total_value_eur"]))
        if row.get("verification_status"):
            parts.append(row["verification_status"])

    elif table == "pbc_obligated_subject":
        for field in ("subject_type", "tin", "registration_number", "supervisory_authority", "pbc_license"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "pbc_internal_control":
        if row.get("obligated_subject_id"):
            parts.append(f"subject:{row['obligated_subject_id']}")
        if row.get("risk_assessment_date"):
            parts.append(str(row["risk_assessment_date"]))
        if row.get("compliance_officer"):
            parts.append(row["compliance_officer"])
        for bool_field in ("internal_reporting_channel", "training_program", "audit_trail"):
            if row.get(bool_field):
                parts.append(bool_field.replace("_", " "))

    elif table == "suspicious_activity_report":
        if row.get("obligated_subject_id"):
            parts.append(f"subject:{row['obligated_subject_id']}")
        if row.get("submission_date"):
            parts.append(str(row["submission_date"]))
        if row.get("description"):
            parts.append(row["description"])
        if row.get("severity"):
            parts.append(row["severity"])
        if row.get("status"):
            parts.append(row["status"])
        if row.get("sepblac_reference"):
            parts.append(row["sepblac_reference"])

    elif table == "beneficial_owner_record":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("owner_name"):
            parts.append(row["owner_name"])
        if row.get("ownership_percentage"):
            parts.append(str(row["ownership_percentage"]))
        if row.get("acquisition_date"):
            parts.append(str(row["acquisition_date"]))
        if row.get("verification_method"):
            parts.append(row["verification_method"])
        if row.get("verification_date"):
            parts.append(str(row["verification_date"]))

    elif table == "fraud_prevention_program":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        for bool_field in ("code_of_conduct", "internal_reporting_system"):
            if row.get(bool_field):
                parts.append(bool_field.replace("_", " "))
        if row.get("training_schedule"):
            parts.append(row["training_schedule"])
        if row.get("audit_frequency"):
            parts.append(row["audit_frequency"])
        if row.get("compliance_officer_name"):
            parts.append(row["compliance_officer_name"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "fraud_risk_assessment":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("assessment_date"):
            parts.append(str(row["assessment_date"]))
        if row.get("risk_areas"):
            parts.append(row["risk_areas"])
        if row.get("mitigation_measures"):
            parts.append(row["mitigation_measures"])
        if row.get("next_review_date"):
            parts.append(str(row["next_review_date"]))

    elif table == "fraud_incident":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("incident_date"):
            parts.append(str(row["incident_date"]))
        if row.get("description"):
            parts.append(row["description"])
        if row.get("amount_eur"):
            parts.append(str(row["amount_eur"]))
        if row.get("status"):
            parts.append(row["status"])
        if row.get("resolution_date"):
            parts.append(str(row["resolution_date"]))
        if row.get("regulatory_notification"):
            parts.append("regulatory-notified" if row["regulatory_notification"] else "not-notified")

    # --- MiFID II/MiFIR ---
    elif table == "mifid_client_category":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("category"):
            parts.append(row["category"])
        if row.get("assessment_date"):
            parts.append(str(row["assessment_date"]))
        for field in ("knowledge_level", "experience_level", "status"):
            if row.get(field):
                parts.append(str(row[field]))

    elif table == "mifid_suitability_report":
        for field in ("client_id", "product_id", "assessment_date"):
            if row.get(field):
                parts.append(f"{field}:{row[field]}")
        if row.get("suitability_score"):
            parts.append(f"score:{row['suitability_score']}")
        if row.get("recommendation"):
            parts.append(row["recommendation"])
        if row.get("advisor_id"):
            parts.append(f"advisor:{row['advisor_id']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mifid_best_execution_record":
        if row.get("order_id"):
            parts.append(f"order:{row['order_id']}")
        if row.get("venue"):
            parts.append(f"venue:{row['venue']}")
        if row.get("execution_price"):
            parts.append(f"price:{row['execution_price']}")
        if row.get("market_impact"):
            parts.append(f"impact:{row['market_impact']}")
        if row.get("speed_ms"):
            parts.append(f"speed:{row['speed_ms']}ms")
        if row.get("quality_metrics"):
            parts.append(str(row["quality_metrics"]))
        if row.get("execution_timestamp"):
            parts.append(str(row["execution_timestamp"]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mifid_conflict_of_interest_registry":
        for field in ("department", "conflict_type", "description", "mitigation_measure"):
            if row.get(field):
                parts.append(str(row[field]))
        for date_field in ("identified_date", "review_date"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mifid_product_governance":
        if row.get("product_id"):
            parts.append(f"product:{row['product_id']}")
        for field in ("target_market", "key_features"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("distribution_channels"):
            parts.append(str(row["distribution_channels"]))
        if row.get("risk_level"):
            parts.append(f"risk:{row['risk_level']}")
        if row.get("review_date"):
            parts.append(f"review:{row['review_date']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mifid_order_record":
        if row.get("client_id"):
            parts.append(f"client:{row['client_id']}")
        for field in ("instrument", "direction", "venue"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("quantity"):
            parts.append(f"qty:{row['quantity']}")
        if row.get("price"):
            parts.append(f"price:{row['price']}")
        if row.get("timestamp"):
            parts.append(str(row["timestamp"]))
        if row.get("retention_until"):
            parts.append(f"retain:{row['retention_until']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mifid_insider_list":
        for field in ("insider_name", "insider_tin", "inside_information_description"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        for date_field in ("date_created", "date_removed"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mifid_compensation_policy":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("policy_version"):
            parts.append(f"version:{row['policy_version']}")
        if row.get("alignment_score"):
            parts.append(f"alignment:{row['alignment_score']}")
        if row.get("risk_adjustment_applied"):
            parts.append("risk-adjusted" if row["risk_adjustment_applied"] else "no-risk-adjustment")
        for date_field in ("approval_date", "next_review"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        if row.get("status"):
            parts.append(row["status"])

    # --- MAR ---
    elif table == "mar_insider_transaction":
        for field in ("ppi_name", "ppi_role", "instrument", "transaction_type"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("quantity"):
            parts.append(f"qty:{row['quantity']}")
        if row.get("value_eur"):
            parts.append(f"value:{row['value_eur']}")
        if row.get("price"):
            parts.append(f"price:{row['price']}")
        if row.get("date_time"):
            parts.append(str(row["date_time"]))
        if row.get("country"):
            parts.append(f"country:{row['country']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mar_suspicious_transaction_report":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("instrument"):
            parts.append(f"instrument:{row['instrument']}")
        if row.get("pattern_description"):
            parts.append(row["pattern_description"])
        if row.get("detection_method"):
            parts.append(f"detection:{row['detection_method']}")
        if row.get("severity"):
            parts.append(f"severity:{row['severity']}")
        if row.get("submitted_to_cnmv"):
            parts.append("submitted" if row["submitted_to_cnmv"] else "not-submitted")
        if row.get("cnmv_reference"):
            parts.append(f"ref:{row['cnmv_reference']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mar_market_manipulation_indicator":
        for field in ("pattern_type", "instrument", "time_window"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("volume_anomaly_pct"):
            parts.append(f"vol_anomaly:{row['volume_anomaly_pct']}%")
        if row.get("price_anomaly_pct"):
            parts.append(f"price_anomaly:{row['price_anomaly_pct']}%")
        if row.get("confidence_score"):
            parts.append(f"confidence:{row['confidence_score']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "mar_insider_communication":
        if row.get("sender_id"):
            parts.append(f"sender:{row['sender_id']}")
        if row.get("receiver_id"):
            parts.append(f"receiver:{row['receiver_id']}")
        if row.get("content_summary"):
            parts.append(row["content_summary"])
        if row.get("timestamp"):
            parts.append(str(row["timestamp"]))
        if row.get("channel"):
            parts.append(f"channel:{row['channel']}")
        if row.get("inside_info_reference"):
            parts.append(f"info_ref:{row['inside_info_reference']}")

    # --- DORA ---
    elif table == "dora_tic_incident":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        for field in ("incident_severity", "description", "impact_scope", "root_cause", "classification"):
            if row.get(field):
                parts.append(str(row[field]))
        for date_field in ("detection_date", "resolution_date"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "dora_third_party_provider":
        for field in ("provider_name", "provider_type", "criticality_assessment"):
            if row.get(field):
                parts.append(str(row[field]))
        for date_field in ("contract_start", "contract_end"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        for field in ("eu_supervision_status", "exit_strategy", "status"):
            if row.get(field):
                parts.append(str(row[field]))

    elif table == "dora_ict_risk_register":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("risk_description"):
            parts.append(row["risk_description"])
        for field in ("likelihood", "impact", "mitigation", "owner"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("review_date"):
            parts.append(f"review:{row['review_date']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "dora_penetration_test":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        for field in ("test_type", "tester"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("test_date"):
            parts.append(f"test_date:{row['test_date']}")
        if row.get("findings_count"):
            parts.append(f"findings:{row['findings_count']}")
        if row.get("critical_findings"):
            parts.append(f"critical:{row['critical_findings']}")
        if row.get("remediation_deadline"):
            parts.append(f"deadline:{row['remediation_deadline']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "dora_incident_classification_framework":
        if row.get("framework_version"):
            parts.append(f"version:{row['framework_version']}")
        if row.get("severity_thresholds"):
            parts.append(str(row["severity_thresholds"]))
        if row.get("reporting_timelines"):
            parts.append(str(row["reporting_timelines"]))
        if row.get("effective_date"):
            parts.append(f"effective:{row['effective_date']}")
        if row.get("status"):
            parts.append(row["status"])

    # --- PRIIPs / LIVMC ---
    elif table == "priips_kid":
        if row.get("product_id"):
            parts.append(f"product:{row['product_id']}")
        for field in ("product_type", "currency"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("risk_scale"):
            parts.append(f"risk_scale:{row['risk_scale']}")
        if row.get("cost_impact"):
            parts.append(f"cost:{row['cost_impact']}")
        if row.get("negative_scenario_returns"):
            parts.append(f"scenarios:{row['negative_scenario_returns']}")
        for field in ("version", "publication_date"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "priips_product":
        if row.get("issuer_id"):
            parts.append(f"issuer:{row['issuer_id']}")
        if row.get("product_name"):
            parts.append(row["product_name"])
        if row.get("underlying_assets"):
            parts.append(str(row["underlying_assets"]))
        if row.get("maturity_date"):
            parts.append(f"maturity:{row['maturity_date']}")
        for field in ("currency", "status"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("min_investment"):
            parts.append(f"min:{row['min_investment']}")
        if row.get("distribution_channels"):
            parts.append(str(row["distribution_channels"]))

    elif table == "livmc_client_protection":
        if row.get("client_id"):
            parts.append(f"client:{row['client_id']}")
        for field in ("protection_type", "status"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("provider_id"):
            parts.append(f"provider:{row['provider_id']}")
        if row.get("coverage_amount"):
            parts.append(f"coverage:{row['coverage_amount']}")

    elif table == "livmc_voice_procedure":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        for field in ("procedure_type", "description"):
            if row.get(field):
                parts.append(str(row[field]))
        for date_field in ("effective_date", "next_review"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        if row.get("status"):
            parts.append(row["status"])

    # --- Transparencia ---
    elif table == "transparency_issuer":
        if row.get("issuer_id"):
            parts.append(f"issuer:{row['issuer_id']}")
        for field in ("listing_market", "ticker", "reporting_frequency", "home_member_state"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "transparency_regulated_information":
        if row.get("issuer_id"):
            parts.append(f"issuer:{row['issuer_id']}")
        for field in ("info_type", "publication_date", "content_url", "filing_reference"):
            if row.get(field):
                parts.append(str(row[field]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "transparency_voting_rights":
        if row.get("issuer_id"):
            parts.append(f"issuer:{row['issuer_id']}")
        if row.get("shareholder_id"):
            parts.append(f"shareholder:{row['shareholder_id']}")
        if row.get("voting_rights_pct"):
            parts.append(f"pct:{row['voting_rights_pct']}")
        for date_field in ("date_acquired", "date_reported"):
            if row.get(date_field):
                parts.append(f"{date_field}:{row[date_field]}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "transparency_internal_rule":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("designated_persons"):
            parts.append(str(row["designated_persons"]))
        if row.get("internal_procedure"):
            parts.append(row["internal_procedure"])
        if row.get("retention_period"):
            parts.append(f"retention:{row['retention_period']}")
        if row.get("status"):
            parts.append(row["status"])

    # --- SFDR (31.9.1) ---
    elif table == "sfdr_product":
        if row.get("product_name"):
            parts.append(row["product_name"])
        if row.get("product_type"):
            parts.append(f"type:{row['product_type']}")
        if row.get("sustainability_strategy"):
            parts.append(row["sustainability_strategy"])
        if row.get("principal_adverse_impact"):
            parts.append(f"paci:{row['principal_adverse_impact']}")
        if row.get("paci_aggregated"):
            parts.append(str(row["paci_aggregated"]))
        if row.get("paci_detailed_url"):
            parts.append(row["paci_detailed_url"])
        if row.get("distribution_country"):
            parts.append(str(row["distribution_country"]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "sfdr_paci_indicator":
        if row.get("product_id"):
            parts.append(f"product:{row['product_id']}")
        if row.get("indicator_code"):
            parts.append(f"code:{row['indicator_code']}")
        if row.get("indicator_name"):
            parts.append(row["indicator_name"])
        if row.get("value") is not None:
            parts.append(f"value:{row['value']}")
        if row.get("unit"):
            parts.append(row["unit"])
        if row.get("reference_period"):
            parts.append(f"period:{row['reference_period']}")
        if row.get("methodology"):
            parts.append(row["methodology"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "sfdr_entity_paci":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("reporting_year"):
            parts.append(f"year:{row['reporting_year']}")
        if row.get("aggregated_paci"):
            parts.append(str(row["aggregated_paci"]))
        if row.get("sectoral_decarbonization"):
            parts.append(row["sectoral_decarbonization"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "sfdr_pre_contractual":
        if row.get("product_id"):
            parts.append(f"product:{row['product_id']}")
        if row.get("document_type"):
            parts.append(f"doc_type:{row['document_type']}")
        if row.get("url"):
            parts.append(row["url"])
        if row.get("published_date"):
            parts.append(str(row["published_date"]))
        if row.get("version"):
            parts.append(f"version:{row['version']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "sfdr_annual_report":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("reporting_year"):
            parts.append(f"year:{row['reporting_year']}")
        if row.get("paci_results"):
            parts.append(str(row["paci_results"]))
        if row.get("engagement_activities"):
            parts.append(row["engagement_activities"])
        if row.get("good_practice_examples"):
            parts.append(row["good_practice_examples"])
        if row.get("url"):
            parts.append(row["url"])
        if row.get("published_date"):
            parts.append(str(row["published_date"]))
        if row.get("status"):
            parts.append(row["status"])

    # --- CSRD (31.9.2) ---
    elif table == "csrd_entity_report":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("reporting_year"):
            parts.append(f"year:{row['reporting_year']}")
        if row.get("esap_url"):
            parts.append(row["esap_url"])
        if row.get("assurance_status"):
            parts.append(f"assurance:{row['assurance_status']}")
        if row.get("reporting_standard"):
            parts.append(row["reporting_standard"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "csrd_esg_data_point":
        if row.get("report_id"):
            parts.append(f"report:{row['report_id']}")
        if row.get("topic"):
            parts.append(f"topic:{row['topic']}")
        if row.get("indicator_code"):
            parts.append(f"code:{row['indicator_code']}")
        if row.get("value") is not None:
            parts.append(f"value:{row['value']}")
        if row.get("unit"):
            parts.append(row["unit"])
        if row.get("scope") is not None:
            parts.append(f"scope:{row['scope']}")
        if row.get("verification_status"):
            parts.append(row["verification_status"])

    elif table == "csrd_ess":
        if row.get("standard_code"):
            parts.append(f"standard:{row['standard_code']}")
        if row.get("topic"):
            parts.append(row["topic"])
        if row.get("applicable_from_year"):
            parts.append(f"from:{row['applicable_from_year']}")
        if row.get("description"):
            parts.append(row["description"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "csrd_double_materiality":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("impact_materiality"):
            parts.append(str(row["impact_materiality"]))
        if row.get("financial_materiality"):
            parts.append(str(row["financial_materiality"]))
        if row.get("assessment_date"):
            parts.append(str(row["assessment_date"]))
        if row.get("key_impacts"):
            parts.append(row["key_impacts"])
        if row.get("key_dependencies"):
            parts.append(row["key_dependencies"])
        if row.get("status"):
            parts.append(row["status"])

    # --- AIFMD/UCITS (31.9.3) ---
    elif table == "aifmd_fund":
        if row.get("fund_name"):
            parts.append(row["fund_name"])
        if row.get("aifm_id"):
            parts.append(f"aifm:{row['aifm_id']}")
        if row.get("fund_type"):
            parts.append(f"type:{row['fund_type']}")
        if row.get("registration_date"):
            parts.append(str(row["registration_date"]))
        if row.get("home_member_state"):
            parts.append(row["home_member_state"])
        if row.get("cross_border_passport"):
            parts.append("passport" if row["cross_border_passport"] else "no-passport")
        if row.get("total_aum_eur"):
            parts.append(f"aum:{row['total_aum_eur']}")
        if row.get("investor_type"):
            parts.append(row["investor_type"])
        if row.get("lock_up_period"):
            parts.append(row["lock_up_period"])
        if row.get("redemption_frequency"):
            parts.append(row["redemption_frequency"])
        if row.get("leverage_method"):
            parts.append(row["leverage_method"])
        if row.get("leverage_max_pct"):
            parts.append(f"leverage_max:{row['leverage_max_pct']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "ucits_fund":
        if row.get("fund_name"):
            parts.append(row["fund_name"])
        if row.get("management_company"):
            parts.append(row["management_company"])
        if row.get("registration_date"):
            parts.append(str(row["registration_date"]))
        if row.get("home_member_state"):
            parts.append(row["home_member_state"])
        if row.get("cross_border_passport"):
            parts.append("passport" if row["cross_border_passport"] else "no-passport")
        if row.get("total_aum_eur"):
            parts.append(f"aum:{row['total_aum_eur']}")
        if row.get("depositary_id"):
            parts.append(f"depositary:{row['depositary_id']}")
        if row.get("krid_url"):
            parts.append(row["krid_url"])
        if row.get("investment_strategy"):
            parts.append(row["investment_strategy"])
        if row.get("risk_profile"):
            parts.append(row["risk_profile"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "aifmd_regulatory_report" or table == "ucits_regulatory_report":
        if row.get("fund_id"):
            parts.append(f"fund:{row['fund_id']}")
        if row.get("report_type"):
            parts.append(f"type:{row['report_type']}")
        if row.get("reporting_period"):
            parts.append(row["reporting_period"])
        if row.get("url"):
            parts.append(row["url"])
        if row.get("filed_date"):
            parts.append(str(row["filed_date"]))
        if row.get("status"):
            parts.append(row["status"])

    elif table == "aifmd_liquidity_management":
        if row.get("fund_id"):
            parts.append(f"fund:{row['fund_id']}")
        if row.get("redemption_suspended"):
            parts.append("suspended" if row["redemption_suspended"] else "not_suspended")
        if row.get("suspension_date"):
            parts.append(str(row["suspension_date"]))
        if row.get("gating_applied"):
            parts.append("gating" if row["gating_applied"] else "no-gating")
        if row.get("swing_price_applied"):
            parts.append("swing-price" if row["swing_price_applied"] else "no-swing-price")
        if row.get("side_pocket_applied"):
            parts.append("side-pocket" if row["side_pocket_applied"] else "no-side-pocket")
        if row.get("stress_test_result"):
            parts.append(str(row["stress_test_result"]))
        if row.get("valuation_frequency"):
            parts.append(row["valuation_frequency"])

    # --- CRD/CRR/BRRD/EMIR (31.9.4) ---
    elif table == "crd_capital_position":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("reporting_date"):
            parts.append(str(row["reporting_date"]))
        if row.get("cet1_ratio"):
            parts.append(f"cet1:{row['cet1_ratio']}")
        if row.get("tier1_ratio"):
            parts.append(f"tier1:{row['tier1_ratio']}")
        if row.get("total_capital_ratio"):
            parts.append(f"total_capital:{row['total_capital_ratio']}")
        if row.get("cet1_amount"):
            parts.append(f"cet1_amount:{row['cet1_amount']}")
        if row.get("tier1_amount"):
            parts.append(f"tier1_amount:{row['tier1_amount']}")
        if row.get("total_capital_amount"):
            parts.append(f"total_capital_amount:{row['total_capital_amount']}")
        if row.get("leverage_ratio"):
            parts.append(f"leverage:{row['leverage_ratio']}")
        if row.get("risk_weighted_assets"):
            parts.append(f"rwa:{row['risk_weighted_assets']}")
        if row.get("status"):
            parts.append(row["status"])

    elif table == "crd_stress_test":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("test_date"):
            parts.append(str(row["test_date"]))
        if row.get("scenario_name"):
            parts.append(row["scenario_name"])
        if row.get("cet1_impact_pct"):
            parts.append(f"cet1_impact:{row['cet1_impact_pct']}")
        if row.get("tier1_impact_pct"):
            parts.append(f"tier1_impact:{row['tier1_impact_pct']}")
        if row.get("capital_ratio_post_test"):
            parts.append(f"post_test:{row['capital_ratio_post_test']}")
        if row.get("competent_authority"):
            parts.append(row["competent_authority"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "brrd_bail_in":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("total_eligible_liabilities"):
            parts.append(f"liabilities:{row['total_eligible_liabilities']}")
        if row.get("mrel_target_pct"):
            parts.append(f"mrel_target:{row['mrel_target_pct']}")
        if row.get("mrel_compliance_pct"):
            parts.append(f"mrel_compliance:{row['mrel_compliance_pct']}")
        if row.get("internal_mrel"):
            parts.append(f"internal_mrel:{row['internal_mrel']}")
        if row.get("resolution_status"):
            parts.append(row["resolution_status"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "emir_trade_report":
        if row.get("trade_id"):
            parts.append(f"trade:{row['trade_id']}")
        if row.get("asset_class"):
            parts.append(f"class:{row['asset_class']}")
        if row.get("instrument_class"):
            parts.append(row["instrument_class"])
        if row.get("clearing_obligation_applied"):
            parts.append("clearing" if row["clearing_obligation_applied"] else "no-clearing")
        if row.get("reporting_delay_days"):
            parts.append(f"delay:{row['reporting_delay_days']}")
        if row.get("counterparty_type"):
            parts.append(row["counterparty_type"])
        if row.get("status"):
            parts.append(row["status"])

    elif table == "emir_clearing_member":
        if row.get("entity_id"):
            parts.append(f"entity:{row['entity_id']}")
        if row.get("emir_registration"):
            parts.append(f"reg:{row['emir_registration']}")
        if row.get("clearing_type"):
            parts.append(row["clearing_type"])
        if row.get("status"):
            parts.append(row["status"])

    return " ".join(parts)


# ── Chunking logic ────────────────────────────────────────────────

def _split_into_chunks(text: str, max_size: int = 1500) -> list[dict[str, Any]]:
    """Split text into chunks. For structured data, the text is short
    so we typically get a single chunk per row."""
    if not text:
        return []

    text = text.strip()
    if len(text) <= max_size:
        return [{
            "chunk_type": "natural",
            "titulo": None,
            "texto": text,
            "char_start": 0,
            "char_end": len(text),
            "token_count": len(text.split()),
        }]

    # Size-based split with overlap
    overlap = max_size // 4
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        chunk_text = text[start:end].strip()
        if not chunk_text:
            break
        chunks.append({
            "chunk_type": "fallback",
            "titulo": None,
            "texto": chunk_text,
            "char_start": start,
            "char_end": end,
            "token_count": len(chunk_text.split()),
        })
        start = end - overlap if end < len(text) else end

    return chunks


# ── Core backfill logic ───────────────────────────────────────────

def backfill_31x_chunks(
    engine,
    corpus: str,
    chunk_size: int,
    dry_run: bool,
    table_filter: str | None = None,
) -> dict[str, int]:
    """Run the backfill. Returns counts: inserted, skipped, documents_processed."""
    counts = {"inserted": 0, "skipped": 0, "documents_processed": 0, "dry_run": dry_run}

    with engine.connect() as conn:
        tables_to_process: list[str] = []
        if table_filter:
            if table_filter in DOMAIN_QUERIES:
                tables_to_process = [table_filter]
            else:
                print(f"ERROR: Unknown table '{table_filter}'. Valid: {', '.join(DOMAIN_QUERIES.keys())}", file=sys.stderr)
                return counts
        elif corpus == "all":
            tables_to_process = list(DOMAIN_QUERIES.keys())
        else:
            tables_to_process = DOMAIN_TABLES.get(corpus, [])

        for table in tables_to_process:
            n = _backfill_table(conn, table, chunk_size, dry_run, counts)
            counts["inserted"] += n
            counts["documents_processed"] += n

    return counts


def _backfill_table(
    conn,
    table: str,
    chunk_size: int,
    dry_run: bool,
    counts: dict[str, int],
) -> int:
    """Backfill chunks for a single 31.x table."""
    domain = TABLE_DOMAIN_MAP[table]
    query = text(DOMAIN_QUERIES[table])
    rows = conn.execute(query).mappings()
    inserted = 0

    for row in rows:
        row_id = row["id"]

        # Check if already has chunks (idempotency)
        existing = conn.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM documento_fragmento "
                "WHERE documento_origen_tipo = :tipo "
                "AND documento_origen_id = :doc_id"
            ),
            {"tipo": domain, "doc_id": row_id},
        ).scalar()

        if existing > 0:
            counts["skipped"] += 1
            continue

        search_text = _build_search_text(table, dict(row))
        if not search_text:
            continue

        chunks = _split_into_chunks(search_text, chunk_size)
        if not chunks:
            continue

        for idx, chunk in enumerate(chunks):
            if dry_run:
                print(
                    f"  [DRY-RUN] INSERT {domain} table={table} id={row_id} "
                    f"idx={idx} type={chunk['chunk_type']} tokens={chunk['token_count']}"
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO documento_fragmento
                            (documento_origen_tipo, documento_origen_id, chunk_index,
                             chunk_type, titulo, texto, char_start, char_end, token_count)
                        VALUES
                            (:tipo, :doc_id, :idx, :chunk_type, :titulo, :texto,
                             :char_start, :char_end, :token_count)
                        ON CONFLICT (documento_origen_tipo, documento_origen_id, chunk_index)
                        DO NOTHING
                        """
                    ),
                    {
                        "tipo": domain,
                        "doc_id": row_id,
                        "idx": idx,
                        "chunk_type": chunk["chunk_type"],
                        "titulo": chunk["titulo"],
                        "texto": chunk["texto"],
                        "char_start": chunk["char_start"],
                        "char_end": chunk["char_end"],
                        "token_count": chunk["token_count"],
                    },
                )
                inserted += 1

    if not dry_run and inserted > 0:
        conn.commit()

    return inserted


# ── CLI ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill chunks for Fase 31 regulatory domains (MiCA, DAC8, Ley 10/2010, Ley 11/2021, MiFID II, MAR, DORA, PRIIPs, Transparencia, SFDR, CSRD, AIFMD/UCITS, CRD/CRR/BRRD/EMIR)."
    )
    parser.add_argument(
        "--corpus",
        choices=["mica", "dac", "pbc", "fraud", "mifid", "mar", "dora", "priips", "transparency", "sfdr", "csrd", "aifmd_ucits", "crd_brrd_emir", "all"],
        default="all",
        help="Which domain to backfill (default: all).",
    )
    parser.add_argument(
        "--table",
        type=str,
        default=None,
        help="Backfill only a specific table (e.g. casp, crypto_asset).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1500,
        help="Max characters per chunk (default: 1500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be inserted without writing.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="DATABASE_URL override (default: env var DATABASE_URL).",
    )

    args = parser.parse_args()

    db_url = args.database_url or (
        "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata"
    )

    print("Connecting to database...")
    engine = create_engine(db_url, future=True)

    try:
        # Verify tables exist
        with engine.connect() as conn:
            tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('documento_fragmento', " +
                    ", ".join(f"'{t}'" for t in DOMAIN_QUERIES) +
                    ")"
                )
            ).fetchall()
            table_names = {t[0] for t in tables}
            if "documento_fragmento" not in table_names:
                print("ERROR: documento_fragmento table not found. Run Alembic migration first.", file=sys.stderr)
                return 1

            missing = set(DOMAIN_QUERIES.keys()) - table_names
            if missing:
                print(f"WARNING: Missing tables: {', '.join(sorted(missing))}", file=sys.stderr)

        print(f"Backfilling corpus='{args.corpus}' table='{args.table}' chunk_size={args.chunk_size} dry_run={args.dry_run}")

        counts = backfill_31x_chunks(
            engine,
            corpus=args.corpus,
            chunk_size=args.chunk_size,
            dry_run=args.dry_run,
            table_filter=args.table,
        )

        print()
        print("=== Results ===")
        print(f"  Documents processed: {counts['documents_processed']}")
        print(f"  Chunks inserted:     {counts['inserted']}")
        print(f"  Documents skipped:   {counts['skipped']}")
        if counts["dry_run"]:
            print("  (dry-run — no data was written)")
        else:
            print("  (search_vector populated by DB trigger)")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
