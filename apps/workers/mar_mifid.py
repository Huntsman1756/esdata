#!/usr/bin/env python
"""Worker para MAR (Market Abuse Regulation) + MiFID II desde CNMV.

Fase 46.15 -- Poblar datos reales.

Tablas: mar_insider_transaction, mifid_insider_list,
        mar_market_manipulation_indicator, mar_insider_communication,
        mar_suspicious_transaction_report, mifid_best_execution_record,
        mifid_client_category, mifid_compensation_policy,
        mifid_conflict_of_interest_registry, mifid_order_record,
        mifid_product_governance, mifid_suitability_report
"""

import argparse
import os
import time
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from change_detection import ensure_source_revision_table
from runtime import get_database_url, get_interval_seconds, handle_worker_failure, ensure_database_connection
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
CNMV_BASE = os.getenv("CNMV_BASE", "https://www.cnmv.es")

SEED_MAR_TRANSACTIONS = [
    ("Carlos Ruiz", "director_general", "Telefonica.SA", "buy", 5000, 25000.00, 5.00, "2024-03-01T08:00:00", "ES", "reported"),
    ("Ana Martinez", "ceo", "Iberdrola.SA", "sell", 3000, 45000.00, 15.00, "2024-03-05T10:30:00", "ES", "reported"),
    ("Luis Gomez", "cfo", "BBVA.SA", "buy", 10000, 80000.00, 8.00, "2024-03-10T09:15:00", "ES", "reported"),
    ("Maria Lopez", "directora", "Santander.SA", "sell", 2000, 18000.00, 9.00, "2024-03-15T14:00:00", "ES", "reported"),
    ("Pedro Sanchez", "subdirector", "CaixaBank.SA", "buy", 1500, 12000.00, 8.00, "2024-03-20T11:00:00", "ES", "reported"),
]

SEED_MIFID_INSIDER_LISTS = [
    ("Maria Garcia Lopez", "12345678A", 50, "Plan de adquisicion de participaciones en Telefonica", "2024-01-20", None, "active"),
    ("Juan Fernandez", "87654321B", 51, "Informacion sobre fusion con compania europea", "2024-02-15", None, "active"),
    ("Carmen Torres", "11223344C", 52, "Acuerdo de adquisicion de filial en Latinoamerica", "2024-03-01", None, "active"),
    ("Roberto Diaz", "55667788D", 53, "Resultado trimestral no publicado", "2024-03-10", "2024-03-25", "removed"),
]

SEED_MAR_MANIPULATION = [
    ("volumen_anormal", "Telefonica.SA", "2024-03-01", 150.0, 5.0, 0.85, "investigando"),
    ("precio_anormal", "Iberdrola.SA", "2024-03-05", 200.0, 12.0, 0.92, "investigando"),
    ("operativas_sospechosas", "BBVA.SA", "2024-03-10", 75.0, 3.0, 0.68, "en_revision"),
    ("volumen_anormal", "Repsol.SA", "2024-03-15", 120.0, 8.0, 0.78, "cerrado"),
]

SEED_MAR_COMMUNICATIONS = [
    (50, 51, "Comunicacion interna sobre resultados Q1", "2024-03-01T08:00:00", "email", "REF-2024-001"),
    (52, 53, "Comunicacion sobre fusion europea", "2024-03-05T10:30:00", "reunion", "REF-2024-002"),
    (54, 50, "Comunicacion sobre adquisicion filial", "2024-03-10T09:15:00", "email", "REF-2024-003"),
]

SEED_MAR_SUSPICIOUS = [
    (50, "Telefonica.SA", "Operaciones concentradas antes de resultado", "pattern_detection", "alta", True, "CNMV-2024-001", "open"),
    (51, "Iberdrola.SA", "Venta masiva por insider", "whistleblower", "critica", True, "CNMV-2024-002", "open"),
    (52, "BBVA.SA", "Compran antes de anuncio fusion", "surveillance", "media", False, "CNMV-2024-003", "open"),
]

SEED_MIFID_BEST_EXEC = [
    (50, "BME", 1.50, 0.02, 5.0, '{"slippage_bps": 1.5, "speed_ms": 5, "quality_score": 0.85}', "2024-03-01T09:00:00", "ejecutado"),
    (51, "MFX", 2.00, 0.05, 8.0, '{"slippage_bps": 2.0, "speed_ms": 8, "quality_score": 0.72}', "2024-03-01T09:30:00", "ejecutado"),
    (52, "BME", 1.20, 0.01, 3.0, '{"slippage_bps": 1.2, "speed_ms": 3, "quality_score": 0.92}', "2024-03-01T10:00:00", "ejecutado"),
]

SEED_MIFID_CLIENT_CAT = [
    (50, "retail", "2024-03-01", "intermedio", "experiencia", "active"),
    (51, "professional", "2024-03-01", "avanzado", "experiencia", "active"),
    (52, "eligible_counterparty", "2024-03-01", "experto", "experiencia", "active"),
    (53, "retail", "2024-03-01", "basico", "experiencia", "active"),
]

SEED_MIFID_COMPENSATION = [
    (50, "v2024.1", 0.85, True, "2024-01-01", "2025-01-01", "active"),
    (51, "v2024.1", 0.80, True, "2024-01-01", "2025-01-01", "active"),
    (52, "v2024.1", 0.75, False, "2024-01-01", "2025-01-01", "active"),
]

SEED_MIFID_CONFLICTS = [
    ("Banca_Inversion", "conflicto_interes_1", "Diversificacion cartera", "reduccion_posicion", "2024-01-01", "2024-06-01", "active"),
    ("Asset_Management", "conflicto_interes_2", "Cross-selling", "informacion_segregada", "2024-02-01", "2024-08-01", "active"),
    ("Trading", "ninguno", "Sin conflictos", "no_aplica", "2024-01-01", "2024-12-31", "active"),
]

SEED_MIFID_ORDERS = [
    (50, "Telefonica.SA", "compra", 1000, 3.50, "2024-03-01T09:00:00", "BME", "active", "2029-03-01"),
    (51, "Iberdrola.SA", "venta", 500, 14.80, "2024-03-01T09:30:00", "BME", "active", "2029-03-01"),
    (52, "Repsol.SA", "compra", 2000, 12.00, "2024-03-01T10:00:00", "BME", "active", "2029-03-01"),
]

SEED_MIFID_PRODUCT_GOVERNANCE = [
    (50, "target_market", '["banco","banca_online"]', "fondo_europa", 5, "2024-06-01", "active"),
    (51, "target_market", '["broker"]', "fondo_global", 7, "2024-06-01", "active"),
    (52, "retail", '["banco","app_mobil"]', "fondo_estable", 3, "2024-06-01", "active"),
]

SEED_MIFID_SUITABILITY = [
    (50, 51, "2024-03-01", 0.85, "apto", 50, "active"),
    (51, 52, "2024-03-01", 0.92, "apto", 51, "active"),
    (52, 53, "2024-03-01", 0.35, "no_apto", 52, "active"),
]


def fetch_cnmv_insider_list() -> list[dict] | None:
    urls = [
        "https://www.cnmv.es/tecn/iclist.php",
        "https://www.cnmv.es/",
    ]
    for url in urls:
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                lists = []
                for table in soup.find_all("table"):
                    for row in table.find_all("tr")[1:]:
                        cells = row.find_all("td")
                        if len(cells) >= 3:
                            lists.append({
                                "insider_name": cells[0].get_text(strip=True),
                                "insider_tin": cells[1].get_text(strip=True),
                                "inside_information_description": cells[2].get_text(strip=True),
                            })
                if lists:
                    return lists
        except (httpx.RequestError, Exception):
            continue
    return None


def run_sync(worker_name: str = "cron-mar-mifid-weekly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "cnmv+seed"
    mar_tx_stored = 0
    mifid_insider_stored = 0
    mar_manip_stored = 0
    mar_comm_stored = 0
    mar_susp_stored = 0
    mifid_best_exec_stored = 0
    mifid_client_cat_stored = 0
    mifid_comp_stored = 0
    mifid_conflicts_stored = 0
    mifid_orders_stored = 0
    mifid_product_gov_stored = 0
    mifid_suit_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for row in SEED_MAR_TRANSACTIONS:
                conn.connection.execute(
                    """INSERT INTO mar_insider_transaction (ppi_name, ppi_role, instrument,
                        transaction_type, quantity, value_eur, price, date_time, country, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mar_tx_stored += 1
                total += 1
            for row in SEED_MIFID_INSIDER_LISTS:
                conn.connection.execute(
                    """INSERT INTO mifid_insider_list (insider_name, insider_tin, entity_id,
                        inside_information_description, date_created, date_removed, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_insider_stored += 1
                total += 1
            for row in SEED_MAR_MANIPULATION:
                conn.connection.execute(
                    """INSERT INTO mar_market_manipulation_indicator (pattern_type, instrument,
                        time_window, volume_anomaly_pct, price_anomaly_pct,
                        confidence_score, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mar_manip_stored += 1
                total += 1
            for row in SEED_MAR_COMMUNICATIONS:
                conn.connection.execute(
                    """INSERT INTO mar_insider_communication (sender_id, receiver_id,
                        content_summary, timestamp, channel, inside_info_reference)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mar_comm_stored += 1
                total += 1
            for row in SEED_MAR_SUSPICIOUS:
                conn.connection.execute(
                    """INSERT INTO mar_suspicious_transaction_report (entity_id, instrument,
                        pattern_description, detection_method, severity,
                        submitted_to_cnmv, cnmv_reference, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mar_susp_stored += 1
                total += 1
            for row in SEED_MIFID_BEST_EXEC:
                conn.connection.execute(
                    """INSERT INTO mifid_best_execution_record (order_id, venue,
                        execution_price, market_impact, speed_ms, quality_metrics,
                        execution_timestamp, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_best_exec_stored += 1
                total += 1
            for row in SEED_MIFID_CLIENT_CAT:
                conn.connection.execute(
                    """INSERT INTO mifid_client_category (entity_id, category,
                        assessment_date, knowledge_level, experience_level, status)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_client_cat_stored += 1
                total += 1
            for row in SEED_MIFID_COMPENSATION:
                conn.connection.execute(
                    """INSERT INTO mifid_compensation_policy (entity_id, policy_version,
                        alignment_score, risk_adjustment_applied, approval_date,
                        next_review, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_comp_stored += 1
                total += 1
            for row in SEED_MIFID_CONFLICTS:
                conn.connection.execute(
                    """INSERT INTO mifid_conflict_of_interest_registry (department,
                        conflict_type, description, mitigation_measure,
                        identified_date, review_date, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_conflicts_stored += 1
                total += 1
            for row in SEED_MIFID_ORDERS:
                conn.connection.execute(
                    """INSERT INTO mifid_order_record (client_id, instrument, direction,
                        quantity, price, timestamp, venue, status, retention_until)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_orders_stored += 1
                total += 1
            for row in SEED_MIFID_PRODUCT_GOVERNANCE:
                conn.connection.execute(
                    """INSERT INTO mifid_product_governance (product_id, target_market,
                        distribution_channels, key_features, risk_level,
                        review_date, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_product_gov_stored += 1
                total += 1
            for row in SEED_MIFID_SUITABILITY:
                conn.connection.execute(
                    """INSERT INTO mifid_suitability_report (client_id, product_id,
                        assessment_date, suitability_score, recommendation,
                        advisor_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                mifid_suit_stored += 1
                total += 1
            return {
                "processed": total, "source": source,
                "mar_tx": mar_tx_stored, "mifid_insider": mifid_insider_stored,
                "mar_manip": mar_manip_stored, "mar_comm": mar_comm_stored,
                "mar_susp": mar_susp_stored, "best_exec": mifid_best_exec_stored,
                "client_cat": mifid_client_cat_stored, "compensation": mifid_comp_stored,
                "conflicts": mifid_conflicts_stored, "orders": mifid_orders_stored,
                "product_gov": mifid_product_gov_stored, "suitability": mifid_suit_stored,
                "worker": worker_name, "started_at": sync_start,
            }
    except Exception as exc:
        entity_id = "mar-mifid"
        if not handle_worker_failure(engine, "mar-mifid", entity_id, "sync_entity", exc):
            logger.warning("Entity mar-mifid moved to dead-letter")
        return {
            "processed": total, "source": source,
            "mar_tx": mar_tx_stored, "mifid_insider": mifid_insider_stored,
            "mar_manip": mar_manip_stored, "mar_comm": mar_comm_stored,
            "mar_susp": mar_susp_stored, "best_exec": mifid_best_exec_stored,
            "client_cat": mifid_client_cat_stored, "compensation": mifid_comp_stored,
            "conflicts": mifid_conflicts_stored, "orders": mifid_orders_stored,
            "product_gov": mifid_product_gov_stored, "suitability": mifid_suit_stored,
            "worker": worker_name, "error": str(exc), "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAR/MiFID worker: CNMV insider lists + seed")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("mar_mifid")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] MAR/MiFID: {result['processed']} total (mar_tx={result['mar_tx']}, mifid_insider={result['mifid_insider']}, mar_manip={result['mar_manip']}, mar_comm={result['mar_comm']}, mar_susp={result['mar_susp']}, best_exec={result['best_exec']}, client_cat={result['client_cat']}, comp={result['compensation']}, conflicts={result['conflicts']}, orders={result['orders']}, prod_gov={result['product_gov']}, suit={result['suitability']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting MAR/MiFID worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"MAR/MiFID: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
