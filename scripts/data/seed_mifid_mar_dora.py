#!/usr/bin/env python3
"""Seed MiFID II/MAR/DORA — Datos regulatorios financieros.

Crea datos de referencia MiFID, MAR, DORA, PRIIPs, LIVMC y Transparencia.
Basado en el worker mifid_mar_dora.py.

Uso:
    python scripts/data/seed_mifid_mar_dora.py [--database-url URL]
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

# MiFID II client categories
MIFID_CLIENT_CATEGORIES = [
    {"entity_id": 1, "category": "retail", "assessment_date": "2024-01-15", "knowledge_level": "bajo", "experience_level": "limitado", "status": "active"},
    {"entity_id": 2, "category": "professional", "assessment_date": "2024-02-01", "knowledge_level": "alto", "experience_level": "extenso", "status": "active"},
    {"entity_id": 3, "category": "eligible_counterparty", "assessment_date": "2024-03-10", "knowledge_level": "experto", "experience_level": "profesional", "status": "active"},
]

MIFID_SUITABILITY_REPORTS = [
    {"client_id": 1, "product_id": 101, "assessment_date": "2024-01-20", "suitability_score": 3, "recommendation": "no_recommended", "advisor_id": 1, "status": "active"},
    {"client_id": 2, "product_id": 102, "assessment_date": "2024-02-05", "suitability_score": 8, "recommendation": "recommended", "advisor_id": 2, "status": "active"},
]

MIFID_BEST_EXECUTION = [
    {"order_id": 5001, "venue": "BME", "execution_price": 15.45, "market_impact": 0.0023, "speed_ms": 45, "quality_metrics": json.dumps({"slippage": 0.001, "fill_rate": 0.98}), "execution_timestamp": "2024-03-01 10:30:00+01", "status": "active"},
    {"order_id": 5002, "venue": "MSE", "execution_price": 15.48, "market_impact": 0.0018, "speed_ms": 38, "quality_metrics": json.dumps({"slippage": 0.0005, "fill_rate": 1.0}), "execution_timestamp": "2024-03-01 11:15:00+01", "status": "active"},
]

MIFID_CONFLICTS = [
    {"department": "trading", "conflict_type": "personal_dealing", "description": "Empleados con posiciones en instrumentos negociados por la cuenta de clientes", "mitigation_measure": "pre-clearing requerido, lista de vigilancia", "identified_date": "2024-01-10", "review_date": "2024-07-10", "status": "active"},
    {"department": "advisory", "conflict_type": "cross_interest", "description": "Asesoria simultanea a partes con intereses contrapuestos", "mitigation_measure": "chinese walls, segregacion de equipos", "identified_date": "2024-02-15", "review_date": "2024-08-15", "status": "active"},
]

MIFID_PRODUCT_GOVERNANCE = [
    {"product_id": 101, "target_market": "investidor_profesional", "distribution_channels": json.dumps(["distribuidor_bancario", "plataforma_online"]), "key_features": "derivados complejos, apalancamiento", "risk_level": 6, "review_date": "2024-12-31", "status": "active"},
    {"product_id": 102, "target_market": "investidor_minorista", "distribution_channels": json.dumps(["distribuidor_bancario"]), "key_features": "fondo indexado, bajo riesgo", "risk_level": 3, "review_date": "2024-12-31", "status": "active"},
]

MIFID_ORDER_RECORDS = [
    {"client_id": 1, "instrument": "IBE.MC", "direction": "buy", "quantity": 100, "price": 15.42, "timestamp": "2024-03-01 10:29:55+01", "venue": "BME", "status": "executed", "retention_until": "2029-03-01"},
    {"client_id": 2, "instrument": "SAN.MC", "direction": "sell", "quantity": 200, "price": 4.15, "timestamp": "2024-03-02 09:45:00+01", "venue": "BME", "status": "executed", "retention_until": "2029-03-02"},
]

MIFID_INSIDER_LISTS = [
    {"insider_name": "Maria Garcia Lopez", "insider_tin": "12345678A", "entity_id": 1, "inside_information_description": "Plan de adquisicion de participaciones en compania X", "date_created": "2024-01-20", "status": "active"},
    {"insider_name": "Carlos Fernandez Ruiz", "insider_tin": "87654321B", "entity_id": 2, "inside_information_description": "Negociaciones de fusion con compania Y", "date_created": "2024-02-10", "status": "active"},
]

MIFID_COMPENSATION = [
    {"entity_id": 1, "policy_version": "2024.1", "alignment_score": 85, "risk_adjustment_applied": True, "approval_date": "2024-01-01", "next_review": "2025-01-01", "status": "active"},
    {"entity_id": 2, "policy_version": "2024.2", "alignment_score": 90, "risk_adjustment_applied": True, "approval_date": "2024-02-01", "next_review": "2025-02-01", "status": "active"},
]

# MAR
MAR_INSIDER_TRANSACTIONS = [
    {"ppi_name": "Ana Martinez", "ppi_role": "director_general", "instrument": "Telefonia.SA", "transaction_type": "buy", "quantity": 5000, "value_eur": 25000.0, "price": 5.0, "date_time": "2024-03-01 09:00:00+01", "country": "ES", "status": "reported"},
    {"ppi_name": "Pedro Sanchez", "ppi_role": "consejero", "instrument": "Iberdrola.SA", "transaction_type": "sell", "quantity": 2000, "value_eur": 38000.0, "price": 19.0, "date_time": "2024-03-02 14:30:00+01", "country": "ES", "status": "reported"},
]

MAR_STR = [
    {"entity_id": 1, "instrument": "BBVA.MC", "pattern_description": "Operacion en cascada con volumen 3x promedio diario", "detection_method": "monitorizacion_situacion_mercado", "severity": "high", "submitted_to_cnmv": True, "cnmv_reference": "STR-2024-001", "status": "under_review"},
    {"entity_id": 2, "instrument": "Inditex.MC", "pattern_description": "Operacion cruzada entre cuentas controladas por mismo beneficiario", "detection_method": "analisis_comportamiento_transaccional", "severity": "critical", "submitted_to_cnmv": True, "cnmv_reference": "STR-2024-002", "status": "submitted"},
]

MAR_MANIPULATION = [
    {"pattern_type": "spoofing", "instrument": "REPSOL.MC", "time_window": "2024-02-28 09:00-16:00", "volume_anomaly_pct": 250.0, "price_anomaly_pct": 5.2, "confidence_score": 0.78, "status": "active"},
    {"pattern_type": "wash_trade", "instrument": "AMADEI.MC", "time_window": "2024-03-01 10:00-12:00", "volume_anomaly_pct": 180.0, "price_anomaly_pct": 2.1, "confidence_score": 0.65, "status": "active"},
]

MAR_COMMUNICATIONS = [
    {"sender_id": 1, "receiver_id": 2, "content_summary": "Comunicacion sobre resultados trimestrales no publicados", "timestamp": "2024-03-01 08:30:00+01", "channel": "email_interno", "inside_info_reference": "INFO-2024-Q1-RESULTADOS"},
    {"sender_id": 3, "receiver_id": 1, "content_summary": "Consulta sobre plan de recompra de acciones", "timestamp": "2024-03-02 11:00:00+01", "channel": "intranet_seguira", "inside_info_reference": "INFO-2024-BUYBACK_PLAN"},
]

# DORA
DORA_INCIDENTS = [
    {"entity_id": 1, "incident_severity": "high", "description": "Ataque ransomware afectando sistema de trading", "impact_scope": "sistemas_de_negocio_principales", "detection_date": "2024-02-15", "resolution_date": "2024-02-20", "root_cause": "phishing_email_empleado", "classification": "cyber-attack", "status": "resolved"},
    {"entity_id": 2, "incident_severity": "medium", "description": "Interrupcion servicio cloud proveedor AWS", "impact_scope": "plataforma_online_clientes", "detection_date": "2024-03-01", "resolution_date": "2024-03-01", "root_cause": "fallos_proveedor", "classification": "outage", "status": "resolved"},
    {"entity_id": 1, "incident_severity": "critical", "description": "Fuga de datos personales de 5000 clientes", "impact_scope": "base_datos_clientes_completa", "detection_date": "2024-03-10", "resolution_date": None, "root_cause": "vulnerabilidad_api", "classification": "data-breach", "status": "open"},
]

DORA_PROVIDERS = [
    {"provider_name": "Amazon Web Services EU", "provider_type": "cloud", "criticality_assessment": "critical", "contract_start": "2020-01-01", "contract_end": "2026-12-31", "eu_supervision_status": "bajo_supervision_EBA", "exit_strategy": "plan_migracion_multi-cloud", "status": "active"},
    {"provider_name": "Microsoft Azure EU", "provider_type": "cloud", "criticality_assessment": "high", "contract_start": "2021-06-01", "contract_end": "2025-05-31", "eu_supervision_status": "bajo_supervision_EBA", "exit_strategy": "migracion_planificada", "status": "active"},
    {"provider_name": "Salesforce EU", "provider_type": "software", "criticality_assessment": "medium", "contract_start": "2022-01-01", "contract_end": "2025-12-31", "eu_supervision_status": "sin_supervision_directa", "exit_strategy": "exportacion_datos_estandar", "status": "active"},
]

DORA_RISKS = [
    {"entity_id": 1, "risk_description": "Dependencia de unico proveedor cloud", "likelihood": "probable", "impact": "alto", "mitigation": "multi-cloud strategy, contratos con SLA", "owner": "CISO", "review_date": "2024-06-30", "status": "active"},
    {"entity_id": 2, "risk_description": "Vulnerabilidades en aplicaciones legacy", "likelihood": "improbable", "impact": "critico", "mitigation": "programa modernizacion, pentest trimestral", "owner": "CTO", "review_date": "2024-09-30", "status": "active"},
]

DORA_PENTESTS = [
    {"entity_id": 1, "test_type": "black_box", "tester": "Cure53", "test_date": "2024-01-15", "findings_count": 12, "critical_findings": 2, "remediation_deadline": "2024-03-15", "status": "completed"},
    {"entity_id": 2, "test_type": "white_box", "tester": "SecuriTeam", "test_date": "2024-02-20", "findings_count": 8, "critical_findings": 0, "remediation_deadline": "2024-04-20", "status": "completed"},
]

DORA_CLASSIFICATION = [
    {"framework_version": "1.0", "severity_thresholds": json.dumps({"low": {"max_impact": "isolated", "max_duration_minutes": 30}, "medium": {"max_impact": "regional", "max_duration_minutes": 120}, "high": {"max_impact": "national", "max_duration_minutes": 480}, "critical": {"max_impact": "systemic", "max_duration_minutes": 1440}}), "reporting_timelines": json.dumps({"critical": "4_hours", "high": "24_hours", "medium": "72_hours"}), "effective_date": "2024-01-01", "status": "active"},
]

# PRIIPs
PRIIPs_KIDS = [
    {"product_id": 101, "product_type": "fondo_inversion", "currency": "EUR", "risk_scale": 6, "cost_impact": json.dumps({"entry_fee_pct": 0.0, "exit_fee_pct": 0.0, "ongoing_cost_pct": 1.85}), "negative_scenario_returns": json.dumps({"stress_1y": -0.35, "stress_5y": -0.60}), "version": "2024.1", "publication_date": "2024-01-15", "status": "active"},
    {"product_id": 102, "product_type": "etf", "currency": "EUR", "risk_scale": 3, "cost_impact": json.dumps({"entry_fee_pct": 0.0, "exit_fee_pct": 0.0, "ongoing_cost_pct": 0.25}), "negative_scenario_returns": json.dumps({"stress_1y": -0.15, "stress_5y": -0.30}), "version": "2024.1", "publication_date": "2024-02-01", "status": "active"},
]

PRIIPs_PRODUCTS = [
    {"issuer_id": 1, "product_name": "Fondo Renta Variable Europa", "underlying_assets": json.dumps([{"type": "equity", "region": "Europa", "weight_pct": 100}]), "maturity_date": None, "currency": "EUR", "min_investment": 3000.0, "distribution_channels": json.dumps(["banco", "banca_online"]), "status": "active"},
    {"issuer_id": 2, "product_name": "ETF Euro Stoxx 50", "underlying_assets": json.dumps([{"type": "index", "name": "Euro Stoxx 50", "weight_pct": 100}]), "maturity_date": None, "currency": "EUR", "min_investment": 100.0, "distribution_channels": json.dumps(["plataforma_online", "banco"]), "status": "active"},
]

# LIVMC
LIVMC_PROTECTIONS = [
    {"client_id": 1, "protection_type": "dispute-resolution", "provider_id": 1, "coverage_amount": 20000.0, "status": "active"},
    {"client_id": 2, "protection_type": "mediation", "provider_id": 2, "coverage_amount": 50000.0, "status": "active"},
]

LIVMC_PROCEDURES = [
    {"entity_id": 1, "procedure_type": "quejas_clientes", "description": "Procedimiento de gestion de quejas conforme a art. 10 LivMC", "effective_date": "2024-01-01", "next_review": "2025-01-01", "status": "active"},
    {"entity_id": 2, "procedure_type": "reclamaciones", "description": "Procedimiento de reclamaciones ante CNMV", "effective_date": "2024-01-01", "next_review": "2025-01-01", "status": "active"},
]

# Transparencia
TRANSPARENCY_ISSUERS = [
    {"issuer_id": 1, "listing_market": "BME", "ticker": "IBE.MC", "reporting_frequency": "anual", "home_member_state": "ES", "status": "active"},
    {"issuer_id": 2, "listing_market": "BME", "ticker": "SAN.MC", "reporting_frequency": "anual", "home_member_state": "ES", "status": "active"},
    {"issuer_id": 3, "listing_market": "BME", "ticker": "TEF.MC", "reporting_frequency": "semestral", "home_member_state": "ES", "status": "active"},
]

TRANSPARENCY_INFO = [
    {"issuer_id": 1, "info_type": "financial-report", "publication_date": "2024-03-15", "content_url": "https://www.iberdrola.com/inversores/resultados", "filing_reference": "IR-IBE-2024-Q4", "status": "published"},
    {"issuer_id": 2, "info_type": "share-capital-change", "publication_date": "2024-02-28", "content_url": "https://www.bbvapaper.com/inversores", "filing_reference": "IR-BBVA-2024-CAP", "status": "published"},
    {"issuer_id": 3, "info_type": "insider-info", "publication_date": "2024-03-10", "content_url": "https://www.telefonica.com/inversores", "filing_reference": "IR-TEF-2024-INSIDER", "status": "published"},
]

TRANSPARENCY_VOTING = [
    {"issuer_id": 1, "shareholder_id": 10, "voting_rights_pct": 0.0523, "date_acquired": "2024-01-15", "date_reported": "2024-01-20", "status": "active"},
    {"issuer_id": 1, "shareholder_id": 11, "voting_rights_pct": 0.0301, "date_acquired": "2024-02-01", "date_reported": "2024-02-05", "status": "active"},
    {"issuer_id": 2, "shareholder_id": 10, "voting_rights_pct": 0.0750, "date_acquired": "2024-01-20", "date_reported": "2024-01-25", "status": "active"},
]

TRANSPARENCY_RULES = [
    {"entity_id": 1, "designated_persons": json.dumps(["ceo", "cfo", "secretario_consejo"]), "internal_procedure": "notificacion_inmediata_comite_emergente", "retention_period": "10_anos", "status": "active"},
    {"entity_id": 2, "designated_persons": json.dumps(["ceo", "cfo", "compliance_officer"]), "internal_procedure": "notificacion_24h_desde_deteccion", "retention_period": "10_anos", "status": "active"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed MiFID II/MAR/DORA data")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    # MiFID II
    for d in MIFID_CLIENT_CATEGORIES:
        cur.execute(
            """INSERT INTO mifid_client_category (entity_id, category, assessment_date,
               knowledge_level, experience_level, status)
               VALUES (%(entity_id)s, %(category)s, %(assessment_date)s, %(knowledge_level)s,
                       %(experience_level)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_SUITABILITY_REPORTS:
        cur.execute(
            """INSERT INTO mifid_suitability_report (client_id, product_id, assessment_date,
               suitability_score, recommendation, advisor_id, status)
               VALUES (%(client_id)s, %(product_id)s, %(assessment_date)s, %(suitability_score)s,
                       %(recommendation)s, %(advisor_id)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_BEST_EXECUTION:
        cur.execute(
            """INSERT INTO mifid_best_execution_record (order_id, venue, execution_price,
               market_impact, speed_ms, quality_metrics, execution_timestamp, status)
               VALUES (%(order_id)s, %(venue)s, %(execution_price)s, %(market_impact)s, %(speed_ms)s,
                       %(quality_metrics)s, %(execution_timestamp)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_CONFLICTS:
        cur.execute(
            """INSERT INTO mifid_conflict_of_interest_registry (department, conflict_type,
               description, mitigation_measure, identified_date, review_date, status)
               VALUES (%(department)s, %(conflict_type)s, %(description)s, %(mitigation_measure)s,
                       %(identified_date)s, %(review_date)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_PRODUCT_GOVERNANCE:
        cur.execute(
            """INSERT INTO mifid_product_governance (product_id, target_market,
               distribution_channels, key_features, risk_level, review_date, status)
               VALUES (%(product_id)s, %(target_market)s, %(distribution_channels)s, %(key_features)s,
                       %(risk_level)s, %(review_date)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_ORDER_RECORDS:
        cur.execute(
            """INSERT INTO mifid_order_record (client_id, instrument, direction, quantity,
               price, timestamp, venue, status, retention_until)
               VALUES (%(client_id)s, %(instrument)s, %(direction)s, %(quantity)s, %(price)s,
                       %(timestamp)s, %(venue)s, %(status)s, %(retention_until)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_INSIDER_LISTS:
        cur.execute(
            """INSERT INTO mifid_insider_list (insider_name, insider_tin, entity_id,
               inside_information_description, date_created, status)
               VALUES (%(insider_name)s, %(insider_tin)s, %(entity_id)s,
                       %(inside_information_description)s, %(date_created)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MIFID_COMPENSATION:
        cur.execute(
            """INSERT INTO mifid_compensation_policy (entity_id, policy_version,
               alignment_score, risk_adjustment_applied, approval_date, next_review, status)
               VALUES (%(entity_id)s, %(policy_version)s, %(alignment_score)s,
                       %(risk_adjustment_applied)s, %(approval_date)s, %(next_review)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    # MAR
    for d in MAR_INSIDER_TRANSACTIONS:
        cur.execute(
            """INSERT INTO mar_insider_transaction (ppi_name, ppi_role, instrument,
               transaction_type, quantity, value_eur, price, date_time, country, status)
               VALUES (%(ppi_name)s, %(ppi_role)s, %(instrument)s, %(transaction_type)s, %(quantity)s,
                       %(value_eur)s, %(price)s, %(date_time)s, %(country)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MAR_STR:
        cur.execute(
            """INSERT INTO mar_suspicious_transaction_report (entity_id, instrument,
               pattern_description, detection_method, severity, submitted_to_cnmv,
               cnmv_reference, status)
               VALUES (%(entity_id)s, %(instrument)s, %(pattern_description)s, %(detection_method)s,
                       %(severity)s, %(submitted_to_cnmv)s, %(cnmv_reference)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MAR_MANIPULATION:
        cur.execute(
            """INSERT INTO mar_market_manipulation_indicator (pattern_type, instrument,
               time_window, volume_anomaly_pct, price_anomaly_pct, confidence_score, status)
               VALUES (%(pattern_type)s, %(instrument)s, %(time_window)s, %(volume_anomaly_pct)s,
                       %(price_anomaly_pct)s, %(confidence_score)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in MAR_COMMUNICATIONS:
        cur.execute(
            """INSERT INTO mar_insider_communication (sender_id, receiver_id,
               content_summary, timestamp, channel, inside_info_reference)
               VALUES (%(sender_id)s, %(receiver_id)s, %(content_summary)s, %(timestamp)s,
                       %(channel)s, %(inside_info_reference)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    # DORA
    for d in DORA_INCIDENTS:
        cur.execute(
            """INSERT INTO dora_tic_incident (entity_id, incident_severity, description,
               impact_scope, detection_date, resolution_date, root_cause, classification, status)
               VALUES (%(entity_id)s, %(incident_severity)s, %(description)s, %(impact_scope)s,
                       %(detection_date)s, %(resolution_date)s, %(root_cause)s, %(classification)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in DORA_PROVIDERS:
        cur.execute(
            """INSERT INTO dora_third_party_provider (provider_name, provider_type,
               criticality_assessment, contract_start, contract_end, eu_supervision_status,
               exit_strategy, status)
               VALUES (%(provider_name)s, %(provider_type)s, %(criticality_assessment)s,
                       %(contract_start)s, %(contract_end)s, %(eu_supervision_status)s,
                       %(exit_strategy)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in DORA_RISKS:
        cur.execute(
            """INSERT INTO dora_ict_risk_register (entity_id, risk_description, likelihood,
               impact, mitigation, owner, review_date, status)
               VALUES (%(entity_id)s, %(risk_description)s, %(likelihood)s, %(impact)s,
                       %(mitigation)s, %(owner)s, %(review_date)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in DORA_PENTESTS:
        cur.execute(
            """INSERT INTO dora_penetration_test (entity_id, test_type, tester, test_date,
               findings_count, critical_findings, remediation_deadline, status)
               VALUES (%(entity_id)s, %(test_type)s, %(tester)s, %(test_date)s, %(findings_count)s,
                       %(critical_findings)s, %(remediation_deadline)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in DORA_CLASSIFICATION:
        cur.execute(
            """INSERT INTO dora_incident_classification_framework (framework_version,
               severity_thresholds, reporting_timelines, effective_date, status)
               VALUES (%(framework_version)s, %(severity_thresholds)s, %(reporting_timelines)s,
                       %(effective_date)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    # PRIIPs
    for d in PRIIPs_KIDS:
        cur.execute(
            """INSERT INTO priips_kid (product_id, product_type, currency, risk_scale,
               cost_impact, negative_scenario_returns, version, publication_date, status)
               VALUES (%(product_id)s, %(product_type)s, %(currency)s, %(risk_scale)s,
                       %(cost_impact)s, %(negative_scenario_returns)s, %(version)s,
                       %(publication_date)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in PRIIPs_PRODUCTS:
        cur.execute(
            """INSERT INTO priips_product (issuer_id, product_name, underlying_assets,
               maturity_date, currency, min_investment, distribution_channels, status)
               VALUES (%(issuer_id)s, %(product_name)s, %(underlying_assets)s, %(maturity_date)s,
                       %(currency)s, %(min_investment)s, %(distribution_channels)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    # LIVMC
    for d in LIVMC_PROTECTIONS:
        cur.execute(
            """INSERT INTO livmc_client_protection (client_id, protection_type,
               provider_id, coverage_amount, status)
               VALUES (%(client_id)s, %(protection_type)s, %(provider_id)s, %(coverage_amount)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in LIVMC_PROCEDURES:
        cur.execute(
            """INSERT INTO livmc_voice_procedure (entity_id, procedure_type,
               description, effective_date, next_review, status)
               VALUES (%(entity_id)s, %(procedure_type)s, %(description)s, %(effective_date)s,
                       %(next_review)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    # Transparencia
    for d in TRANSPARENCY_ISSUERS:
        cur.execute(
            """INSERT INTO transparency_issuer (issuer_id, listing_market, ticker,
               reporting_frequency, home_member_state, status)
               VALUES (%(issuer_id)s, %(listing_market)s, %(ticker)s, %(reporting_frequency)s,
                       %(home_member_state)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in TRANSPARENCY_INFO:
        cur.execute(
            """INSERT INTO transparency_regulated_information (issuer_id, info_type,
               publication_date, content_url, filing_reference, status)
               VALUES (%(issuer_id)s, %(info_type)s, %(publication_date)s, %(content_url)s,
                       %(filing_reference)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in TRANSPARENCY_VOTING:
        cur.execute(
            """INSERT INTO transparency_voting_rights (issuer_id, shareholder_id,
               voting_rights_pct, date_acquired, date_reported, status)
               VALUES (%(issuer_id)s, %(shareholder_id)s, %(voting_rights_pct)s,
                       %(date_acquired)s, %(date_reported)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    for d in TRANSPARENCY_RULES:
        cur.execute(
            """INSERT INTO transparency_internal_rule (entity_id, designated_persons,
               internal_procedure, retention_period, status)
               VALUES (%(entity_id)s, %(designated_persons)s, %(internal_procedure)s,
                       %(retention_period)s, %(status)s)
               ON CONFLICT DO NOTHING""",
            d,
        )

    conn.commit()
    total = (
        len(MIFID_CLIENT_CATEGORIES) + len(MIFID_SUITABILITY_REPORTS) + len(MIFID_BEST_EXECUTION) +
        len(MIFID_CONFLICTS) + len(MIFID_PRODUCT_GOVERNANCE) + len(MIFID_ORDER_RECORDS) +
        len(MIFID_INSIDER_LISTS) + len(MIFID_COMPENSATION) +
        len(MAR_INSIDER_TRANSACTIONS) + len(MAR_STR) + len(MAR_MANIPULATION) + len(MAR_COMMUNICATIONS) +
        len(DORA_INCIDENTS) + len(DORA_PROVIDERS) + len(DORA_RISKS) + len(DORA_PENTESTS) +
        len(DORA_CLASSIFICATION) +
        len(PRIIPs_KIDS) + len(PRIIPs_PRODUCTS) +
        len(LIVMC_PROTECTIONS) + len(LIVMC_PROCEDURES) +
        len(TRANSPARENCY_ISSUERS) + len(TRANSPARENCY_INFO) + len(TRANSPARENCY_VOTING) + len(TRANSPARENCY_RULES)
    )
    print(f"OK: {total} registros MiFID/MAR/DORA insertados")
    conn.close()


if __name__ == "__main__":
    main()
