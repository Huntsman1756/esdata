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
        description="Backfill chunks for Fase 31 regulatory domains (MiCA, DAC8, Ley 10/2010, Ley 11/2021, MiFID II, MAR, DORA, PRIIPs, Transparencia)."
    )
    parser.add_argument(
        "--corpus",
        choices=["mica", "dac", "pbc", "fraud", "mifid", "mar", "dora", "priips", "transparency", "all"],
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
                    ", ".join(f"'{t}'" for t in DOMAIN_QUERIES.keys()) +
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
