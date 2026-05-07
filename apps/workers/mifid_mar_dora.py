"""Worker para ingestion de datos MiFID II/MiFIR, MAR, DORA, PRIIPs, LIVMC y Transparencia.

Fase 31.8 — Expansion regulatoria.

Ingesta datos estructurados de referencia para:
- MiFID II/MiFIR: categorias de cliente, adecuacion, mejor ejecucion, conflictos, gobierno de productos, ordenes, listas insider, politica compensacion
- MAR: operaciones de PPI, reportes de operaciones sospechosas, indicadores de manipulacion, comunicaciones de insider
- DORA: incidentes TIC, proveedores TPT, registro de riesgos ICT, pruebas de penetracion, marco clasificacion
- PRIIPs/LIVMC: documentos KID, productos PRIIPs, proteccion inversor minorista, procedimientos de voz
- Transparencia: emisores, informacion regulada, derechos de voto, reglas internas

Datos de referencia para poblacion inicial (no datos reales).
"""

import argparse
import logging
import time
from datetime import UTC, datetime, date

from boe import _ensure_sync_log_table, log_sync
from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# ---------------------------------------------------------------------------
# Seed data — MiFID II/MiFIR
# ---------------------------------------------------------------------------

SEED_MIFID_CLIENT_CATEGORIES = [
    {"entity_id": 1, "category": "retail", "assessment_date": "2024-01-15", "knowledge_level": "bajo", "experience_level": "limitado", "status": "active"},
    {"entity_id": 2, "category": "professional", "assessment_date": "2024-02-01", "knowledge_level": "alto", "experience_level": "extenso", "status": "active"},
    {"entity_id": 3, "category": "eligible_counterparty", "assessment_date": "2024-03-10", "knowledge_level": "experto", "experience_level": "profesional", "status": "active"},
]

SEED_MIFID_SUITABILITY_REPORTS = [
    {"client_id": 1, "product_id": 101, "assessment_date": "2024-01-20", "suitability_score": 3, "recommendation": "no_recommended", "advisor_id": 1, "status": "active"},
    {"client_id": 2, "product_id": 102, "assessment_date": "2024-02-05", "suitability_score": 8, "recommendation": "recommended", "advisor_id": 2, "status": "active"},
]

SEED_MIFID_BEST_EXECUTION_RECORDS = [
    {"order_id": 5001, "venue": "BME", "execution_price": 15.45, "market_impact": 0.0023, "speed_ms": 45, "quality_metrics": {"slippage": 0.001, "fill_rate": 0.98}, "execution_timestamp": "2024-03-01 10:30:00+01", "status": "active"},
    {"order_id": 5002, "venue": "MSE", "execution_price": 15.48, "market_impact": 0.0018, "speed_ms": 38, "quality_metrics": {"slippage": 0.0005, "fill_rate": 1.0}, "execution_timestamp": "2024-03-01 11:15:00+01", "status": "active"},
]

SEED_MIFID_CONFLICTS_OF_INTEREST = [
    {"department": "trading", "conflict_type": "personal_dealing", "description": "Empleados con posiciones en instrumentos negociados por la cuenta de clientes", "mitigation_measure": "pre-clearing requerido, lista de vigilancia", "identified_date": "2024-01-10", "review_date": "2024-07-10", "status": "active"},
    {"department": "advisory", "conflict_type": "cross_interest", "description": "Asesoria simultanea a partes con intereses contrapuestos", "mitigation_measure": "chinese walls, segregacion de equipos", "identified_date": "2024-02-15", "review_date": "2024-08-15", "status": "active"},
]

SEED_MIFID_PRODUCT_GOVERNANCE = [
    {"product_id": 101, "target_market": "investidor_profesional", "distribution_channels": ["distribuidor_bancario", "plataforma_online"], "key_features": "derivados complejos, apalancamiento", "risk_level": 6, "review_date": "2024-12-31", "status": "active"},
    {"product_id": 102, "target_market": "investidor_minorista", "distribution_channels": ["distribuidor_bancario"], "key_features": "fondo indexado, bajo riesgo", "risk_level": 3, "review_date": "2024-12-31", "status": "active"},
]

SEED_MIFID_ORDER_RECORDS = [
    {"client_id": 1, "instrument": "IBE.MC", "direction": "buy", "quantity": 100, "price": 15.42, "timestamp": "2024-03-01 10:29:55+01", "venue": "BME", "status": "executed", "retention_until": "2029-03-01"},
    {"client_id": 2, "instrument": "SAN.MC", "direction": "sell", "quantity": 200, "price": 4.15, "timestamp": "2024-03-02 09:45:00+01", "venue": "BME", "status": "executed", "retention_until": "2029-03-02"},
]

SEED_MIFID_INSIDER_LISTS = [
    {"insider_name": "Maria Garcia Lopez", "insider_tin": "12345678A", "entity_id": 1, "inside_information_description": "Plan de aquisicion de participaciones en compania X", "date_created": "2024-01-20", "status": "active"},
    {"insider_name": "Carlos Fernandez Ruiz", "insider_tin": "87654321B", "entity_id": 2, "inside_information_description": "Negociaciones de fusion con compania Y", "date_created": "2024-02-10", "status": "active"},
]

SEED_MIFID_COMPENSATION_POLICIES = [
    {"entity_id": 1, "policy_version": "2024.1", "alignment_score": 85, "risk_adjustment_applied": True, "approval_date": "2024-01-01", "next_review": "2025-01-01", "status": "active"},
    {"entity_id": 2, "policy_version": "2024.2", "alignment_score": 90, "risk_adjustment_applied": True, "approval_date": "2024-02-01", "next_review": "2025-02-01", "status": "active"},
]

# ---------------------------------------------------------------------------
# Seed data — MAR (Market Abuse Regulation)
# ---------------------------------------------------------------------------

SEED_MAR_INSIDER_TRANSACTIONS = [
    {"ppi_name": "Ana Martinez", "ppi_role": "director_general", "instrument": "Telefonia.SA", "transaction_type": "buy", "quantity": 5000, "value_eur": 25000.0, "price": 5.0, "date_time": "2024-03-01 09:00:00+01", "country": "ES", "status": "reported"},
    {"ppi_name": "Pedro Sanchez", "ppi_role": "consejero", "instrument": "Iberdrola.SA", "transaction_type": "sell", "quantity": 2000, "value_eur": 38000.0, "price": 19.0, "date_time": "2024-03-02 14:30:00+01", "country": "ES", "status": "reported"},
]

SEED_MAR_STR = [
    {"entity_id": 1, "instrument": "BBVA.MC", "pattern_description": "Operacion en cascada con volumen 3x promedio diario", "detection_method": "monitorizacion_situacion_mercado", "severity": "high", "submitted_to_cnmv": True, "cnmv_reference": "STR-2024-001", "status": "under_review"},
    {"entity_id": 2, "instrument": "Inditex.MC", "pattern_description": "Operacion cruzada entre cuentas controladas por mismo beneficiario", "detection_method": "analisis_comportamiento_transaccional", "severity": "critical", "submitted_to_cnmv": True, "cnmv_reference": "STR-2024-002", "status": "submitted"},
]

SEED_MAR_MANIPULATION_INDICATORS = [
    {"pattern_type": "spoofing", "instrument": "REPSOL.MC", "time_window": "2024-02-28 09:00-16:00", "volume_anomaly_pct": 250.0, "price_anomaly_pct": 5.2, "confidence_score": 0.78, "status": "active"},
    {"pattern_type": "wash_trade", "instrument": "AMADEI.MC", "time_window": "2024-03-01 10:00-12:00", "volume_anomaly_pct": 180.0, "price_anomaly_pct": 2.1, "confidence_score": 0.65, "status": "active"},
]

SEED_MAR_INSIDER_COMMUNICATIONS = [
    {"sender_id": 1, "receiver_id": 2, "content_summary": "Comunicacion sobre resultados trimestrales no publicados", "timestamp": "2024-03-01 08:30:00+01", "channel": "email_interno", "inside_info_reference": "INFO-2024-Q1-RESULTADOS"},
    {"sender_id": 3, "receiver_id": 1, "content_summary": "Consulta sobre plan de recompra de acciones", "timestamp": "2024-03-02 11:00:00+01", "channel": "intranet_seguira", "inside_info_reference": "INFO-2024-BUYBACK_PLAN"},
]

# ---------------------------------------------------------------------------
# Seed data — DORA (Digital Operational Resilience Act)
# ---------------------------------------------------------------------------

SEED_DORA_TIC_INCIDENTS = [
    {"entity_id": 1, "incident_severity": "high", "description": "Ataque ransomware afectando sistema de trading", "impact_scope": "sistemas_de_negocio_principales", "detection_date": "2024-02-15", "resolution_date": "2024-02-20", "root_cause": "phishing_email_empleado", "classification": "cyber-attack", "status": "resolved"},
    {"entity_id": 2, "incident_severity": "medium", "description": "Interrupcion servicio cloud proveedor AWS", "impact_scope": "plataforma_online_clientes", "detection_date": "2024-03-01", "resolution_date": "2024-03-01", "root_cause": "fallos_proveedor", "classification": "outage", "status": "resolved"},
    {"entity_id": 1, "incident_severity": "critical", "description": "Fuga de datos personales de 5000 clientes", "impact_scope": "base_datos_clientes_completa", "detection_date": "2024-03-10", "resolution_date": None, "root_cause": "vulnerabilidad_api", "classification": "data-breach", "status": "open"},
]

SEED_DORA_THIRD_PARTY_PROVIDERS = [
    {"provider_name": "Amazon Web Services EU", "provider_type": "cloud", "criticality_assessment": "critical", "contract_start": "2020-01-01", "contract_end": "2026-12-31", "eu_supervision_status": "bajo_supervision_EBA", "exit_strategy": "plan_migracion_multi-cloud", "status": "active"},
    {"provider_name": "Microsoft Azure EU", "provider_type": "cloud", "criticality_assessment": "high", "contract_start": "2021-06-01", "contract_end": "2025-05-31", "eu_supervision_status": "bajo_supervision_EBA", "exit_strategy": "migracion_planificada", "status": "active"},
    {"provider_name": "Salesforce EU", "provider_type": "software", "criticality_assessment": "medium", "contract_start": "2022-01-01", "contract_end": "2025-12-31", "eu_supervision_status": "sin_supervision_directa", "exit_strategy": "exportacion_datos_estandar", "status": "active"},
]

SEED_DORA_ICT_RISKS = [
    {"entity_id": 1, "risk_description": "Dependencia de unico proveedor cloud", "likelihood": "probable", "impact": "alto", "mitigation": "multi-cloud strategy, contratos con SLA", "owner": "CISO", "review_date": "2024-06-30", "status": "active"},
    {"entity_id": 2, "risk_description": "Vulnerabilidades en aplicaciones legacy", "likelihood": "improbable", "impact": "critico", "mitigation": "programa modernizacion, pentest trimestral", "owner": "CTO", "review_date": "2024-09-30", "status": "active"},
]

SEED_DORA_PENETRATION_TESTS = [
    {"entity_id": 1, "test_type": "black_box", "tester": "Cure53", "test_date": "2024-01-15", "findings_count": 12, "critical_findings": 2, "remediation_deadline": "2024-03-15", "status": "completed"},
    {"entity_id": 2, "test_type": "white_box", "tester": "SecuriTeam", "test_date": "2024-02-20", "findings_count": 8, "critical_findings": 0, "remediation_deadline": "2024-04-20", "status": "completed"},
    {"entity_id": 1, "test_type": "purple_team", "tester": "internal_red_team", "test_date": "2024-06-15", "findings_count": None, "critical_findings": None, "remediation_deadline": None, "status": "scheduled"},
]

SEED_DORA_CLASSIFICATION_FRAMEWORKS = [
    {"framework_version": "1.0", "severity_thresholds": {"low": {"max_impact": "isolated", "max_duration_minutes": 30}, "medium": {"max_impact": "regional", "max_duration_minutes": 120}, "high": {"max_impact": "national", "max_duration_minutes": 480}, "critical": {"max_impact": "systemic", "max_duration_minutes": 1440}}, "reporting_timelines": {"critical": "4_hours", "high": "24_hours", "medium": "72_hours"}, "effective_date": "2024-01-01", "status": "active"},
]

# ---------------------------------------------------------------------------
# Seed data — PRIIPs / LIVMC
# ---------------------------------------------------------------------------

SEED_PRIIPs_KIDS = [
    {"product_id": 101, "product_type": "fondo_inversion", "currency": "EUR", "risk_scale": 6, "cost_impact": {"entry_fee_pct": 0.0, "exit_fee_pct": 0.0, "ongoing_cost_pct": 1.85}, "negative_scenario_returns": {"stress_1y": -0.35, "stress_5y": -0.60}, "version": "2024.1", "publication_date": "2024-01-15", "status": "active"},
    {"product_id": 102, "product_type": "etf", "currency": "EUR", "risk_scale": 3, "cost_impact": {"entry_fee_pct": 0.0, "exit_fee_pct": 0.0, "ongoing_cost_pct": 0.25}, "negative_scenario_returns": {"stress_1y": -0.15, "stress_5y": -0.30}, "version": "2024.1", "publication_date": "2024-02-01", "status": "active"},
]

SEED_PRIIPs_PRODUCTS = [
    {"issuer_id": 1, "product_name": "Fondo Renta Variable Europa", "underlying_assets": [{"type": "equity", "region": "Europa", "weight_pct": 100}], "maturity_date": None, "currency": "EUR", "min_investment": 3000.0, "distribution_channels": ["banco", "banca_online"], "status": "active"},
    {"issuer_id": 2, "product_name": "ETF Euro Stoxx 50", "underlying_assets": [{"type": "index", "name": "Euro Stoxx 50", "weight_pct": 100}], "maturity_date": None, "currency": "EUR", "min_investment": 100.0, "distribution_channels": ["plataforma_online", "banco"], "status": "active"},
]

SEED_LIVMC_CLIENT_PROTECTIONS = [
    {"client_id": 1, "protection_type": "dispute-resolution", "provider_id": 1, "coverage_amount": 20000.0, "status": "active"},
    {"client_id": 2, "protection_type": "mediation", "provider_id": 2, "coverage_amount": 50000.0, "status": "active"},
]

SEED_LIVMC_VOICE_PROCEDURES = [
    {"entity_id": 1, "procedure_type": "quejas_clientes", "description": "Procedimiento de gestion de quejas conforme a art. 10 LivMC", "effective_date": "2024-01-01", "next_review": "2025-01-01", "status": "active"},
    {"entity_id": 2, "procedure_type": "reclamaciones", "description": "Procedimiento de reclamaciones ante CNMV", "effective_date": "2024-01-01", "next_review": "2025-01-01", "status": "active"},
]

# ---------------------------------------------------------------------------
# Seed data — Transparencia
# ---------------------------------------------------------------------------

SEED_TRANSPARENCY_ISSUERS = [
    {"issuer_id": 1, "listing_market": "BME", "ticker": "IBE.MC", "reporting_frequency": "anual", "home_member_state": "ES", "status": "active"},
    {"issuer_id": 2, "listing_market": "BME", "ticker": "SAN.MC", "reporting_frequency": "anual", "home_member_state": "ES", "status": "active"},
    {"issuer_id": 3, "listing_market": "BME", "ticker": "TEF.MC", "reporting_frequency": "semestral", "home_member_state": "ES", "status": "active"},
]

SEED_TRANSPARENCY_REGULATED_INFO = [
    {"issuer_id": 1, "info_type": "financial-report", "publication_date": "2024-03-15", "content_url": "https://www.iberdrola.com/inversores/resultados", "filing_reference": "IR-IBE-2024-Q4", "status": "published"},
    {"issuer_id": 2, "info_type": "share-capital-change", "publication_date": "2024-02-28", "content_url": "https://www.bbvapaper.com/inversores", "filing_reference": "IR-BBVA-2024-CAP", "status": "published"},
    {"issuer_id": 3, "info_type": "insider-info", "publication_date": "2024-03-10", "content_url": "https://www.telefonica.com/inversores", "filing_reference": "IR-TEF-2024-INSIDER", "status": "published"},
]

SEED_TRANSPARENCY_VOTING_RIGHTS = [
    {"issuer_id": 1, "shareholder_id": 10, "voting_rights_pct": 0.0523, "date_acquired": "2024-01-15", "date_reported": "2024-01-20", "status": "active"},
    {"issuer_id": 1, "shareholder_id": 11, "voting_rights_pct": 0.0301, "date_acquired": "2024-02-01", "date_reported": "2024-02-05", "status": "active"},
    {"issuer_id": 2, "shareholder_id": 10, "voting_rights_pct": 0.0750, "date_acquired": "2024-01-20", "date_reported": "2024-01-25", "status": "active"},
]

SEED_TRANSPARENCY_INTERNAL_RULES = [
    {"entity_id": 1, "designated_persons": ["ceo", "cfo", "secretario_consejo"], "internal_procedure": "notificacion_inmediata_comite_emergente", "retention_period": "10_anos", "status": "active"},
    {"entity_id": 2, "designated_persons": ["ceo", "cfo", "compliance_officer"], "internal_procedure": "notificacion_24h_desde_deteccion", "retention_period": "10_anos", "status": "active"},
]

# ---------------------------------------------------------------------------
# Upsert functions
# ---------------------------------------------------------------------------


def upsert_mifid_client_category(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_client_category (entity_id, category, assessment_date,
                knowledge_level, experience_level, status)
            VALUES (:entity_id, :category, :assessment_date, :knowledge_level,
                :experience_level, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_suitability_report(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_suitability_report (client_id, product_id, assessment_date,
                suitability_score, recommendation, advisor_id, status)
            VALUES (:client_id, :product_id, :assessment_date, :suitability_score,
                :recommendation, :advisor_id, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_best_execution_record(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_best_execution_record (order_id, venue, execution_price,
                market_impact, speed_ms, quality_metrics, execution_timestamp, status)
            VALUES (:order_id, :venue, :execution_price, :market_impact, :speed_ms,
                :quality_metrics, :execution_timestamp, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_conflict_of_interest(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_conflict_of_interest_registry (department, conflict_type,
                description, mitigation_measure, identified_date, review_date, status)
            VALUES (:department, :conflict_type, :description, :mitigation_measure,
                :identified_date, :review_date, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_product_governance(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_product_governance (product_id, target_market,
                distribution_channels, key_features, risk_level, review_date, status)
            VALUES (:product_id, :target_market, :distribution_channels, :key_features,
                :risk_level, :review_date, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_order_record(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_order_record (client_id, instrument, direction, quantity,
                price, timestamp, venue, status, retention_until)
            VALUES (:client_id, :instrument, :direction, :quantity, :price, :timestamp,
                :venue, :status, :retention_until)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_insider_list(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_insider_list (insider_name, insider_tin, entity_id,
                inside_information_description, date_created, status)
            VALUES (:insider_name, :insider_tin, :entity_id, :inside_information_description,
                :date_created, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mifid_compensation_policy(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mifid_compensation_policy (entity_id, policy_version,
                alignment_score, risk_adjustment_applied, approval_date, next_review, status)
            VALUES (:entity_id, :policy_version, :alignment_score, :risk_adjustment_applied,
                :approval_date, :next_review, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mar_insider_transaction(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mar_insider_transaction (ppi_name, ppi_role, instrument,
                transaction_type, quantity, value_eur, price, date_time, country, status)
            VALUES (:ppi_name, :ppi_role, :instrument, :transaction_type, :quantity,
                :value_eur, :price, :date_time, :country, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mar_str(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mar_suspicious_transaction_report (entity_id, instrument,
                pattern_description, detection_method, severity, submitted_to_cnmv,
                cnmv_reference, status)
            VALUES (:entity_id, :instrument, :pattern_description, :detection_method,
                :severity, :submitted_to_cnmv, :cnmv_reference, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mar_manipulation_indicator(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mar_market_manipulation_indicator (pattern_type, instrument,
                time_window, volume_anomaly_pct, price_anomaly_pct, confidence_score, status)
            VALUES (:pattern_type, :instrument, :time_window, :volume_anomaly_pct,
                :price_anomaly_pct, :confidence_score, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_mar_insider_communication(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO mar_insider_communication (sender_id, receiver_id,
                content_summary, timestamp, channel, inside_info_reference)
            VALUES (:sender_id, :receiver_id, :content_summary, :timestamp,
                :channel, :inside_info_reference)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_dora_tic_incident(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO dora_tic_incident (entity_id, incident_severity, description,
                impact_scope, detection_date, resolution_date, root_cause, classification, status)
            VALUES (:entity_id, :incident_severity, :description, :impact_scope,
                :detection_date, :resolution_date, :root_cause, :classification, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_dora_third_party_provider(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO dora_third_party_provider (provider_name, provider_type,
                criticality_assessment, contract_start, contract_end,
                eu_supervision_status, exit_strategy, status)
            VALUES (:provider_name, :provider_type, :criticality_assessment,
                :contract_start, :contract_end, :eu_supervision_status,
                :exit_strategy, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_dora_ict_risk(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO dora_ict_risk_register (entity_id, risk_description,
                likelihood, impact, mitigation, owner, review_date, status)
            VALUES (:entity_id, :risk_description, :likelihood, :impact,
                :mitigation, :owner, :review_date, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_dora_penetration_test(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO dora_penetration_test (entity_id, test_type, tester,
                test_date, findings_count, critical_findings, remediation_deadline, status)
            VALUES (:entity_id, :test_type, :tester, :test_date, :findings_count,
                :critical_findings, :remediation_deadline, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_dora_classification_framework(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO dora_incident_classification_framework (framework_version,
                severity_thresholds, reporting_timelines, effective_date, status)
            VALUES (:framework_version, :severity_thresholds, :reporting_timelines,
                :effective_date, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_priips_kid(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO priips_kid (product_id, product_type, currency, risk_scale,
                cost_impact, negative_scenario_returns, version, publication_date, status)
            VALUES (:product_id, :product_type, :currency, :risk_scale,
                :cost_impact, :negative_scenario_returns, :version, :publication_date, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_priips_product(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO priips_product (issuer_id, product_name, underlying_assets,
                maturity_date, currency, min_investment, distribution_channels, status)
            VALUES (:issuer_id, :product_name, :underlying_assets,
                :maturity_date, :currency, :min_investment, :distribution_channels, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_livmc_client_protection(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO livmc_client_protection (client_id, protection_type,
                provider_id, coverage_amount, status)
            VALUES (:client_id, :protection_type, :provider_id, :coverage_amount, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_livmc_voice_procedure(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO livmc_voice_procedure (entity_id, procedure_type,
                description, effective_date, next_review, status)
            VALUES (:entity_id, :procedure_type, :description, :effective_date,
                :next_review, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_transparency_issuer(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO transparency_issuer (issuer_id, listing_market, ticker,
                reporting_frequency, home_member_state, status)
            VALUES (:issuer_id, :listing_market, :ticker, :reporting_frequency,
                :home_member_state, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_transparency_regulated_info(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO transparency_regulated_information (issuer_id, info_type,
                publication_date, content_url, filing_reference, status)
            VALUES (:issuer_id, :info_type, :publication_date, :content_url,
                :filing_reference, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_transparency_voting_rights(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO transparency_voting_rights (issuer_id, shareholder_id,
                voting_rights_pct, date_acquired, date_reported, status)
            VALUES (:issuer_id, :shareholder_id, :voting_rights_pct,
                :date_acquired, :date_reported, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )


def upsert_transparency_internal_rule(conn, data):
    conn.execute(
        text(
            """
            INSERT INTO transparency_internal_rule (entity_id, designated_persons,
                internal_procedure, retention_period, status)
            VALUES (:entity_id, :designated_persons, :internal_procedure,
                :retention_period, :status)
            ON CONFLICT DO NOTHING
            """
        ),
        data,
    )

# ---------------------------------------------------------------------------
# Main sync
# ---------------------------------------------------------------------------


def run_sync(
    worker_name: str = "worker-mifid-mar-dora",
) -> dict[str, int]:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()

    try:
        with engine.begin() as conn:
            _ensure_sync_log_table(conn)

            # MiFID II
            mifid_cc = 0
            for d in SEED_MIFID_CLIENT_CATEGORIES:
                upsert_mifid_client_category(conn, d)
                mifid_cc += 1
            mifid_sr = 0
            for d in SEED_MIFID_SUITABILITY_REPORTS:
                upsert_mifid_suitability_report(conn, d)
                mifid_sr += 1
            mifid_be = 0
            for d in SEED_MIFID_BEST_EXECUTION_RECORDS:
                upsert_mifid_best_execution_record(conn, d)
                mifid_be += 1
            mifid_coi = 0
            for d in SEED_MIFID_CONFLICTS_OF_INTEREST:
                upsert_mifid_conflict_of_interest(conn, d)
                mifid_coi += 1
            mifid_pg = 0
            for d in SEED_MIFID_PRODUCT_GOVERNANCE:
                upsert_mifid_product_governance(conn, d)
                mifid_pg += 1
            mifid_or = 0
            for d in SEED_MIFID_ORDER_RECORDS:
                upsert_mifid_order_record(conn, d)
                mifid_or += 1
            mifid_il = 0
            for d in SEED_MIFID_INSIDER_LISTS:
                upsert_mifid_insider_list(conn, d)
                mifid_il += 1
            mifid_cp = 0
            for d in SEED_MIFID_COMPENSATION_POLICIES:
                upsert_mifid_compensation_policy(conn, d)
                mifid_cp += 1

            # MAR
            mar_it = 0
            for d in SEED_MAR_INSIDER_TRANSACTIONS:
                upsert_mar_insider_transaction(conn, d)
                mar_it += 1
            mar_str = 0
            for d in SEED_MAR_STR:
                upsert_mar_str(conn, d)
                mar_str += 1
            mar_mmi = 0
            for d in SEED_MAR_MANIPULATION_INDICATORS:
                upsert_mar_manipulation_indicator(conn, d)
                mar_mmi += 1
            mar_ic = 0
            for d in SEED_MAR_INSIDER_COMMUNICATIONS:
                upsert_mar_insider_communication(conn, d)
                mar_ic += 1

            # DORA
            dora_tic = 0
            for d in SEED_DORA_TIC_INCIDENTS:
                upsert_dora_tic_incident(conn, d)
                dora_tic += 1
            dora_tpp = 0
            for d in SEED_DORA_THIRD_PARTY_PROVIDERS:
                upsert_dora_third_party_provider(conn, d)
                dora_tpp += 1
            dora_ict = 0
            for d in SEED_DORA_ICT_RISKS:
                upsert_dora_ict_risk(conn, d)
                dora_ict += 1
            dora_pt = 0
            for d in SEED_DORA_PENETRATION_TESTS:
                upsert_dora_penetration_test(conn, d)
                dora_pt += 1
            dora_icf = 0
            for d in SEED_DORA_CLASSIFICATION_FRAMEWORKS:
                upsert_dora_classification_framework(conn, d)
                dora_icf += 1

            # PRIIPs / LIVMC
            priips_kid = 0
            for d in SEED_PRIIPs_KIDS:
                upsert_priips_kid(conn, d)
                priips_kid += 1
            priips_prod = 0
            for d in SEED_PRIIPs_PRODUCTS:
                upsert_priips_product(conn, d)
                priips_prod += 1
            livmc_cp = 0
            for d in SEED_LIVMC_CLIENT_PROTECTIONS:
                upsert_livmc_client_protection(conn, d)
                livmc_cp += 1
            livmc_vp = 0
            for d in SEED_LIVMC_VOICE_PROCEDURES:
                upsert_livmc_voice_procedure(conn, d)
                livmc_vp += 1

            # Transparencia
            trans_issuer = 0
            for d in SEED_TRANSPARENCY_ISSUERS:
                upsert_transparency_issuer(conn, d)
                trans_issuer += 1
            trans_ri = 0
            for d in SEED_TRANSPARENCY_REGULATED_INFO:
                upsert_transparency_regulated_info(conn, d)
                trans_ri += 1
            trans_vr = 0
            for d in SEED_TRANSPARENCY_VOTING_RIGHTS:
                upsert_transparency_voting_rights(conn, d)
                trans_vr += 1
            trans_ir = 0
            for d in SEED_TRANSPARENCY_INTERNAL_RULES:
                upsert_transparency_internal_rule(conn, d)
                trans_ir += 1

            total = (mifid_cc + mifid_sr + mifid_be + mifid_coi + mifid_pg +
                     mifid_or + mifid_il + mifid_cp + mar_it + mar_str +
                     mar_mmi + mar_ic + dora_tic + dora_tpp + dora_ict +
                     dora_pt + dora_icf + priips_kid + priips_prod + livmc_cp +
                     livmc_vp + trans_issuer + trans_ri + trans_vr + trans_ir)

            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=total,
                documentos_upserted=total,
                started_at=sync_start,
            )

        return {
            "mifid_client_categories": mifid_cc,
            "mifid_suitability_reports": mifid_sr,
            "mifid_best_execution": mifid_be,
            "mifid_conflicts": mifid_coi,
            "mifid_product_governance": mifid_pg,
            "mifid_orders": mifid_or,
            "mifid_insider_lists": mifid_il,
            "mifid_compensation_policies": mifid_cp,
            "mar_insider_transactions": mar_it,
            "mar_str": mar_str,
            "mar_manipulation_indicators": mar_mmi,
            "mar_insider_communications": mar_ic,
            "dora_tic_incidents": dora_tic,
            "dora_third_party_providers": dora_tpp,
            "dora_ict_risks": dora_ict,
            "dora_penetration_tests": dora_pt,
            "dora_classification_frameworks": dora_icf,
            "priips_kids": priips_kid,
            "priips_products": priips_prod,
            "livmc_client_protections": livmc_cp,
            "livmc_voice_procedures": livmc_vp,
            "transparency_issuers": trans_issuer,
            "transparency_regulated_info": trans_ri,
            "transparency_voting_rights": trans_vr,
            "transparency_internal_rules": trans_ir,
        }
    except Exception as exc:
        entity_id = "mifid_mar_dora"
        if not handle_worker_failure(engine, "mifid_mar_dora", entity_id, "sync_entity", exc):
            logger.warning("Entity mifid_mar_dora moved to dead-letter")
            return {}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MiFID II/MAR/DORA/PRIIPs/Transparencia worker"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("mifid_mar_dora")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-mifid-mar-dora-weekly")
        print(f"[run-once] MiFID CC: {result['mifid_client_categories']}, "
              f"MAR IT: {result['mar_insider_transactions']}, "
              f"DORA TIC: {result['dora_tic_incidents']}, "
              f"PRIIPs: {result['priips_kids']}, "
              f"Transparency: {result['transparency_issuers']}")
    else:
        print(f"Starting MiFID/MAR/DORA worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"Sync complete: {sum(result.values())} total rows")
            time.sleep(interval)
