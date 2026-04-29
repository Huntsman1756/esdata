#!/usr/bin/env python3
"""Seed MAR/MiFID — Mercado valores, insider trading, ejecucion óptima, conflictos.

Crea datos de MAR (Market Abuse Regulation) y MiFID II conforme a regulacion CNMV.

Uso:
    python scripts/data/seed_mar.py [--dry-run] [--database-url URL]
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

# === MiFID II ===

MIFID_CLIENTS_DATA = [
    {"entity_id": None, "category": "retail", "assessment_date": "2024-01-15", "knowledge_level": "limited", "experience_level": "limited", "status": "active"},
    {"entity_id": None, "category": "professional", "assessment_date": "2024-02-20", "knowledge_level": "adequate", "experience_level": "adequate", "status": "active"},
    {"entity_id": None, "category": "professional", "assessment_date": "2024-03-10", "knowledge_level": "advanced", "experience_level": "advanced", "status": "active"},
    {"entity_id": None, "category": "counterparty", "assessment_date": "2024-04-05", "knowledge_level": "advanced", "experience_level": "advanced", "status": "active"},
    {"entity_id": None, "category": "retail", "assessment_date": "2024-05-12", "knowledge_level": "basic", "experience_level": "basic", "status": "active"},
]

MIFID_SUITABILITY_DATA = [
    {"client_id": None, "product_id": None, "assessment_date": "2024-06-01", "suitability_score": 72, "recommendation": "Apto para productos de riesgo moderado con perfil conservador", "advisor_id": None, "status": "active"},
    {"client_id": None, "product_id": None, "assessment_date": "2024-07-15", "suitability_score": 95, "recommendation": "Apto para productos de inversion complejos y derivados", "advisor_id": None, "status": "active"},
    {"client_id": None, "product_id": None, "assessment_date": "2024-08-20", "suitability_score": 45, "recommendation": "No apto para productos estructurados — solo productos de bajo riesgo", "advisor_id": None, "status": "active"},
    {"client_id": None, "product_id": None, "assessment_date": "2024-09-10", "suitability_score": 80, "recommendation": "Apto para fondos de renta variable internacional", "advisor_id": None, "status": "active"},
]

MIFID_BEST_EXEC_DATA = [
    {"order_id": None, "venue": "BME Spanish Exchanges", "execution_price": 85.420000, "market_impact": 0.0012, "speed_ms": 45, "quality_metrics": {"slippage_bps": 1.2, "fill_rate": 0.98, "rejection_rate": 0.02}, "execution_timestamp": "2025-03-15 10:30:00+00", "status": "active"},
    {"order_id": None, "venue": "LSE", "execution_price": 85.380000, "market_impact": 0.0018, "speed_ms": 120, "quality_metrics": {"slippage_bps": 1.8, "fill_rate": 0.95, "rejection_rate": 0.05}, "execution_timestamp": "2025-03-15 10:30:05+00", "status": "active"},
    {"order_id": None, "venue": "XETRA", "execution_price": 85.400000, "market_impact": 0.0015, "speed_ms": 85, "quality_metrics": {"slippage_bps": 1.5, "fill_rate": 0.97, "rejection_rate": 0.03}, "execution_timestamp": "2025-03-15 10:30:02+00", "status": "active"},
    {"order_id": None, "venue": "BME Spanish Exchanges", "execution_price": 142.560000, "market_impact": 0.0008, "speed_ms": 32, "quality_metrics": {"slippage_bps": 0.8, "fill_rate": 0.99, "rejection_rate": 0.01}, "execution_timestamp": "2025-04-20 14:15:00+00", "status": "active"},
]

MIFID_COI_DATA = [
    {"department": "Investment Banking", "conflict_type": "fee_income", "description": "Comisiones de colocacion pueden influir en recomendaciones de inversion", "mitigation_measure": "Chinese wall entre IB y Research", "identified_date": "2024-01-01", "review_date": "2025-01-01", "status": "active"},
    {"department": "Proprietary Trading", "conflict_type": "principal_trading", "description": "Trading en cuenta propia puede preceder a ordenes de clientes", "mitigation_measure": "Pre-trade controls y monitoring automatizado", "identified_date": "2024-01-01", "review_date": "2025-01-01", "status": "active"},
    {"department": "Research", "conflict_type": "external_benefits", "description": "Acceso a investigacion de terceros puede crear sesgo", "mitigation_measure": "Politica estricta de beneficios externos", "identified_date": "2024-03-15", "review_date": "2025-03-15", "status": "active"},
    {"department": "Asset Management", "conflict_type": "cross_selling", "description": "Priorizar productos con mayor comision sobre interes del cliente", "mitigation_measure": "Politica de mejor ejecucion y transparencia", "identified_date": "2024-06-01", "review_date": "2025-06-01", "status": "active"},
]

MIFID_PG_DATA = [
    {"product_id": None, "target_market": "Retail investors with moderate risk tolerance", "distribution_channels": ["bank_advisor", "online_platform", "phone"], "key_features": "Fondo de renta fija con perfil bajo-medio riesgo", "risk_level": 3, "review_date": "2025-12-31", "status": "active"},
    {"product_id": None, "target_market": "Professional investors only", "distribution_channels": ["institutional_platform", "direct"], "key_features": "Derivados complejos para inversionistas profesionales", "risk_level": 8, "review_date": "2025-12-31", "status": "active"},
    {"product_id": None, "target_market": "Retail and professional investors", "distribution_channels": ["bank_advisor", "online_platform", "exchange", "broker"], "key_features": "ETF diversificado de renta variable global", "risk_level": 5, "review_date": "2025-12-31", "status": "active"},
]

MIFID_ORDERS_DATA = [
    {"client_id": None, "instrument": "IBE.MC (Iberdrola)", "direction": "buy", "quantity": 500.0000, "price": 18.450000, "timestamp": "2025-04-10 09:30:00+00", "venue": "BME Spanish Exchanges", "status": "filled", "retention_until": "2030-04-10"},
    {"client_id": None, "instrument": "SAN.MC (Banco Sabadell)", "direction": "sell", "quantity": 1000.0000, "price": 4.120000, "timestamp": "2025-04-10 10:15:00+00", "venue": "BME Spanish Exchanges", "status": "filled", "retention_until": "2030-04-10"},
    {"client_id": None, "instrument": "TEF.MC (Telefonica)", "direction": "buy", "quantity": 750.0000, "price": 4.280000, "timestamp": "2025-04-11 11:00:00+00", "venue": "BME Spanish Exchanges", "status": "filled", "retention_until": "2030-04-11"},
    {"client_id": None, "instrument": "ITX.MC (Iberdrola)", "direction": "buy", "quantity": 200.0000, "price": 18.520000, "timestamp": "2025-04-12 09:45:00+00", "venue": "Euronext Lisbon", "status": "partially_filled", "retention_until": "2030-04-12"},
    {"client_id": None, "instrument": "BBVA.MC (Banco Bilbao Vizcaya)", "direction": "sell", "quantity": 300.0000, "price": 9.870000, "timestamp": "2025-04-14 15:30:00+00", "venue": "BME Spanish Exchanges", "status": "filled", "retention_until": "2030-04-14"},
]

MIFID_INSIDER_DATA = [
    {"insider_name": "Carlos Rodriguez del Val", "insider_tin": "ESA11223344", "entity_id": None, "inside_information_description": "Adquisicion propuesta de empresa alemana de energias renovables", "date_created": "2025-02-10", "date_removed": None, "status": "active"},
    {"insider_name": "Maria Isabel Gutierrez", "insider_tin": "ESA55667788", "entity_id": None, "inside_information_description": "Resultados trimestrales superiores a expectativas Q4 2024", "date_created": "2025-01-15", "date_removed": "2025-02-28", "status": "removed"},
    {"insider_name": "Javier Moreno Solis", "insider_tin": "ESA99887766", "entity_id": None, "inside_information_description": "Negociacion acuerdo fusion con entidad portuguesa", "date_created": "2025-03-01", "date_removed": None, "status": "active"},
    {"insider_name": "Ana Lucia Fernandez", "insider_tin": "ESA33445566", "entity_id": None, "inside_information_description": "Lanzamiento nueva plataforma digital de banca online", "date_created": "2025-04-01", "date_removed": None, "status": "active"},
]

MIFID_COMP_DATA = [
    {"entity_id": None, "policy_version": "2025-v1", "alignment_score": 85, "risk_adjustment_applied": True, "approval_date": "2025-01-15", "next_review": "2026-01-15", "status": "active"},
    {"entity_id": None, "policy_version": "2024-v3", "alignment_score": 78, "risk_adjustment_applied": True, "approval_date": "2024-01-20", "next_review": "2025-01-20", "status": "archived"},
]

# === MAR ===

MAR_INSIDER_TXN_DATA = [
    {"ppi_name": "Carlos Rodriguez del Val", "ppi_role": "director_general", "instrument": "IBE.MC", "transaction_type": "purchase", "quantity": 5000.0000, "value_eur": 92250.00, "price": 18.450000, "date_time": "2025-02-12 10:30:00+00", "country": "ES", "status": "reported"},
    {"ppi_name": "Maria Isabel Gutierrez", "ppi_role": "cfo", "instrument": "SAN.MC", "transaction_type": "sale", "quantity": 3000.0000, "value_eur": 12360.00, "price": 4.120000, "date_time": "2025-01-20 14:00:00+00", "country": "ES", "status": "reported"},
    {"ppi_name": "Javier Moreno Solis", "ppi_role": "ceo", "instrument": "TEF.MC", "transaction_type": "purchase", "quantity": 10000.0000, "value_eur": 42800.00, "price": 4.280000, "date_time": "2025-03-05 09:15:00+00", "country": "ES", "status": "reported"},
    {"ppi_name": "Ana Lucia Fernandez", "ppi_role": "director_inversion", "instrument": "BBVA.MC", "transaction_type": "purchase", "quantity": 2000.0000, "value_eur": 19740.00, "price": 9.870000, "date_time": "2025-04-02 11:00:00+00", "country": "ES", "status": "reported"},
]

MAR_STR_DATA = [
    {"entity_id": None, "instrument": "IBE.MC", "pattern_description": "Aumento anomalo de volumen 48 horas antes de anuncio de resultados positivos", "detection_method": "pattern_recognition_ml", "severity": "high", "submitted_to_cnmv": True, "cnmv_reference": "STR-MAR-2025-00145", "status": "escalated"},
    {"entity_id": None, "instrument": "SAN.MC", "pattern_description": "Ventas en cascada con ordenes canceladas antes de ejecucion", "detection_method": "rule_based_monitoring", "severity": "medium", "submitted_to_cnmv": True, "cnmv_reference": "STR-MAR-2025-00287", "status": "under_review"},
    {"entity_id": None, "instrument": "TEF.MC", "pattern_description": "Posible insider trading — compra coordinada antes de noticia", "detection_method": "anomaly_detection", "severity": "critical", "submitted_to_cnmv": True, "cnmv_reference": "STR-MAR-2025-00512", "status": "escalated"},
    {"entity_id": None, "instrument": "ITX.MC", "pattern_description": "Wash trading detectado en sesiones de baja liquidez", "detection_method": "volume_anomaly", "severity": "high", "submitted_to_cnmv": True, "cnmv_reference": "STR-MAR-2025-00789", "status": "under_review"},
]

MAR_MMI_DATA = [
    {"pattern_type": "spoofing", "instrument": "IBE.MC", "time_window": "2025-04-10 09:25-09:35", "volume_anomaly_pct": 350.00, "price_anomaly_pct": 2.50, "confidence_score": 0.7800, "status": "investigating"},
    {"pattern_type": "pump_and_dump", "instrument": "small_cap_stock", "time_window": "2025-03-20 14:00-15:00", "volume_anomaly_pct": 800.00, "price_anomaly_pct": 15.00, "confidence_score": 0.9200, "status": "escalated"},
    {"pattern_type": "layering", "instrument": "SAN.MC", "time_window": "2025-04-14 10:00-10:10", "volume_anomaly_pct": 220.00, "price_anomaly_pct": 1.20, "confidence_score": 0.6500, "status": "active"},
]

MAR_IC_DATA = [
    {"sender_id": None, "receiver_id": None, "content_summary": "Email sobre resultados Q4 2024 superiores a expectativas", "timestamp": "2025-01-10 16:30:00+00", "channel": "email", "inside_info_reference": "RES-Q4-2024-BEAT"},
    {"sender_id": None, "receiver_id": None, "content_summary": "Llamada sobre adquisicion propuesta de empresa alemana", "timestamp": "2025-02-08 11:00:00+00", "channel": "phone", "inside_info_reference": "ACQ-DE-RENEWABLES"},
    {"sender_id": None, "receiver_id": None, "content_summary": "Mensaje confidencial sobre lanzamiento plataforma digital", "timestamp": "2025-03-28 09:00:00+00", "channel": "messaging", "inside_info_reference": "DIGITAL-PLATFORM-LAUNCH"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed MAR/MiFID data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(MIFID_CLIENTS_DATA)} MiFID client categories")
        print(f"[DRY RUN] Would insert {len(MIFID_SUITABILITY_DATA)} suitability reports")
        print(f"[DRY RUN] Would insert {len(MIFID_BEST_EXEC_DATA)} best execution records")
        print(f"[DRY RUN] Would insert {len(MIFID_COI_DATA)} conflicts of interest")
        print(f"[DRY RUN] Would insert {len(MIFID_PG_DATA)} product governance")
        print(f"[DRY RUN] Would insert {len(MIFID_ORDERS_DATA)} order records")
        print(f"[DRY RUN] Would insert {len(MIFID_INSIDER_DATA)} insider lists")
        print(f"[DRY RUN] Would insert {len(MIFID_COMP_DATA)} compensation policies")
        print(f"[DRY RUN] Would insert {len(MAR_INSIDER_TXN_DATA)} MAR insider transactions")
        print(f"[DRY RUN] Would insert {len(MAR_STR_DATA)} MAR suspicious transaction reports")
        print(f"[DRY RUN] Would insert {len(MAR_MMI_DATA)} market manipulation indicators")
        print(f"[DRY RUN] Would insert {len(MAR_IC_DATA)} MAR insider communications")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # MiFID client categories
    for c in MIFID_CLIENTS_DATA:
        cur.execute(
            """INSERT INTO mifid_client_category (entity_id, category, assessment_date,
               knowledge_level, experience_level, status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (c["entity_id"], c["category"], c["assessment_date"], c["knowledge_level"],
             c["experience_level"], c["status"]),
        )

    # MiFID suitability reports
    for s in MIFID_SUITABILITY_DATA:
        cur.execute(
            """INSERT INTO mifid_suitability_report (client_id, product_id, assessment_date,
               suitability_score, recommendation, advisor_id, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (s["client_id"], s["product_id"], s["assessment_date"], s["suitability_score"],
             s["recommendation"], s["advisor_id"], s["status"]),
        )

    # MiFID best execution
    for be in MIFID_BEST_EXEC_DATA:
        cur.execute(
            """INSERT INTO mifid_best_execution_record (order_id, venue, execution_price,
               market_impact, speed_ms, quality_metrics, execution_timestamp, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (be["order_id"], be["venue"], float(be["execution_price"]), float(be["market_impact"]),
             be["speed_ms"], json.dumps(be["quality_metrics"]), be["execution_timestamp"],
             be["status"]),
        )

    # MiFID conflict of interest
    for coi in MIFID_COI_DATA:
        cur.execute(
            """INSERT INTO mifid_conflict_of_interest_registry (department, conflict_type,
               description, mitigation_measure, identified_date, review_date, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (coi["department"], coi["conflict_type"], coi["description"],
             coi["mitigation_measure"], coi["identified_date"], coi["review_date"],
             coi["status"]),
        )

    # MiFID product governance
    for pg in MIFID_PG_DATA:
        cur.execute(
            """INSERT INTO mifid_product_governance (product_id, target_market,
               distribution_channels, key_features, risk_level, review_date, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (pg["product_id"], pg["target_market"], json.dumps(pg["distribution_channels"]),
             pg["key_features"], pg["risk_level"], pg["review_date"], pg["status"]),
        )

    # MiFID order records
    for o in MIFID_ORDERS_DATA:
        cur.execute(
            """INSERT INTO mifid_order_record (client_id, instrument, direction, quantity,
               price, timestamp, venue, status, retention_until)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (o["client_id"], o["instrument"], o["direction"], float(o["quantity"]),
             float(o["price"]), o["timestamp"], o["venue"], o["status"], o["retention_until"]),
        )

    # MiFID insider lists
    for il in MIFID_INSIDER_DATA:
        cur.execute(
            """INSERT INTO mifid_insider_list (insider_name, insider_tin, entity_id,
               inside_information_description, date_created, date_removed, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (il["insider_name"], il["insider_tin"], il["entity_id"],
             il["inside_information_description"], il["date_created"], il["date_removed"],
             il["status"]),
        )

    # MiFID compensation policy
    for cp in MIFID_COMP_DATA:
        cur.execute(
            """INSERT INTO mifid_compensation_policy (entity_id, policy_version,
               alignment_score, risk_adjustment_applied, approval_date, next_review, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (cp["entity_id"], cp["policy_version"], cp["alignment_score"],
             cp["risk_adjustment_applied"], cp["approval_date"], cp["next_review"],
             cp["status"]),
        )

    # MAR insider transactions
    for it in MAR_INSIDER_TXN_DATA:
        cur.execute(
            """INSERT INTO mar_insider_transaction (ppi_name, ppi_role, instrument,
               transaction_type, quantity, value_eur, price, date_time, country, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (it["ppi_name"], it["ppi_role"], it["instrument"], it["transaction_type"],
             float(it["quantity"]), float(it["value_eur"]), float(it["price"]),
             it["date_time"], it["country"], it["status"]),
        )

    # MAR suspicious transaction reports
    for str_ in MAR_STR_DATA:
        cur.execute(
            """INSERT INTO mar_suspicious_transaction_report (entity_id, instrument,
               pattern_description, detection_method, severity, submitted_to_cnmv,
               cnmv_reference, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (str_["entity_id"], str_["instrument"], str_["pattern_description"],
             str_["detection_method"], str_["severity"], str_["submitted_to_cnmv"],
             str_["cnmv_reference"], str_["status"]),
        )

    # MAR market manipulation indicators
    for mmi in MAR_MMI_DATA:
        cur.execute(
            """INSERT INTO mar_market_manipulation_indicator (pattern_type, instrument,
               time_window, volume_anomaly_pct, price_anomaly_pct, confidence_score, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (mmi["pattern_type"], mmi["instrument"], mmi["time_window"],
             float(mmi["volume_anomaly_pct"]), float(mmi["price_anomaly_pct"]),
             float(mmi["confidence_score"]), mmi["status"]),
        )

    # MAR insider communications
    for ic in MAR_IC_DATA:
        cur.execute(
            """INSERT INTO mar_insider_communication (sender_id, receiver_id,
               content_summary, timestamp, channel, inside_info_reference)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (ic["sender_id"], ic["receiver_id"], ic["content_summary"],
             ic["timestamp"], ic["channel"], ic["inside_info_reference"]),
        )

    conn.commit()
    total = (len(MIFID_CLIENTS_DATA) + len(MIFID_SUITABILITY_DATA) + len(MIFID_BEST_EXEC_DATA)
             + len(MIFID_COI_DATA) + len(MIFID_PG_DATA) + len(MIFID_ORDERS_DATA)
             + len(MIFID_INSIDER_DATA) + len(MIFID_COMP_DATA)
             + len(MAR_INSIDER_TXN_DATA) + len(MAR_STR_DATA)
             + len(MAR_MMI_DATA) + len(MAR_IC_DATA))
    print(f"OK: {total} registros MAR/MiFID insertados ({len(MIFID_CLIENTS_DATA)} clients, {len(MIFID_SUITABILITY_DATA)} suitability, {len(MIFID_BEST_EXEC_DATA)} best exec, {len(MIFID_COI_DATA)} COI, {len(MIFID_PG_DATA)} PG, {len(MIFID_ORDERS_DATA)} orders, {len(MIFID_INSIDER_DATA)} insiders, {len(MIFID_COMP_DATA)} comp, {len(MAR_INSIDER_TXN_DATA)} MAR txn, {len(MAR_STR_DATA)} STR, {len(MAR_MMI_DATA)} MMI, {len(MAR_IC_DATA)} comms)")
    conn.close()


if __name__ == "__main__":
    main()
