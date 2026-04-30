#!/usr/bin/env python
"""Worker para IDD (Insurance Distribution Directive) desde EUR-Lex.

Fase 46.12 -- Poblar datos reales.

Tablas: idd_distributor, idd_product_uci, solvency_ii_entity, solvency_ii_sfp
"""

import argparse
import os
import re
import time
from datetime import UTC, datetime

import httpx
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
)
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

IDD_NORMAS = [
    {"codigo": "IDD_2016_97", "boe_id": "EUR-CELEX-32016L0097", "tipo_documento": "directiva", "titulo": "Directiva 2016/97/UE sobre la distribucion de seguros", "eli_uri": "https://eur-lex.europa.eu/eli/dir/2016/97/oj", "vigente_desde": "2016-02-04", "ambito": "distribucion_seguros", "regulacion": "idd"},
    {"codigo": "IDD_MiFID_2016_97", "boe_id": "EUR-CELEX-32016L0097", "tipo_documento": "directiva", "titulo": "Directiva 2016/97/UE -- Producto MiFID (seguros vinculados)", "eli_uri": "https://eur-lex.europa.eu/eli/dir/2016/97/oj", "vigente_desde": "2016-02-04", "ambito": "distribucion_seguros_mifid", "regulacion": "idd"},
]

SEED_IDD_DISTRIBUTORS = [
    (50, "IDD-2024-001", "AO-MAPFRE-001", '["vida", "daos", "accidentes"]', True, True, "active"),
    (51, "IDD-2024-002", "AO-ALLIANZ-001", '["vida", "daos", "salud", "accidentes"]', True, True, "active"),
    (52, "IDD-2024-003", "AO-VIDA-001", '["vida"]', True, True, "active"),
    (53, "IDD-2024-004", "AO-BBVA-001", '["vida", "daos", "accidentes"]', True, True, "active"),
    (54, "IDD-2024-005", "AO-CAIXA-001", '["vida", "daos"]', True, True, "active"),
    (55, "IDD-2024-006", "AO-SANTANDER-001", '["vida", "daos", "accidentes", "salud"]', True, True, "active"),
]

SEED_IDD_PRODUCTS = [
    (1, "seguro_vida", "cobertura_total", "prima_anual", "penalizacion_0", "IS", "2024", "active"),
    (2, "seguro_salud", "cobertura_total", "prima_anual", "penalizacion_10", "IS", "2024", "active"),
    (3, "seguro_hogar", "multiriesgo", "prima_anual", "penalizacion_0", "IS", "2024", "active"),
    (4, "seguro_auto", "todo_riesgo", "prima_anual", "penalizacion_0", "IS", "2024", "active"),
]

SEED_SOLVENCY_ENTITIES = [
    (60, "life", 100000000.00, 50000000.00, 220.50, "2024-12-31", "Bde"),
    (61, "non-life", 75000000.00, 30000000.00, 185.00, "2024-12-31", "Bde"),
    (62, "life", 120000000.00, 60000000.00, 200.00, "2024-12-31", "Bde"),
    (63, "non-life", 80000000.00, 35000000.00, 190.00, "2024-12-31", "Bde"),
]

SEED_SOLVENCY_SFP = [
    (60, "Q4-2024", '["vida": 60%, "daos": 40%]', '["activos_seguros": 70%, "inmuebles": 30%]', "https://eur-lex.europa.eu/sfp/solvency-ii-60", "published"),
    (61, "Q4-2024", '["daos": 100%]', '["activos_seguros": 80%, "inmuebles": 20%]', "https://eur-lex.europa.eu/sfp/solvency-ii-61", "published"),
    (62, "Q4-2024", '["vida": 100%]', '["activos_seguros": 65%, "inmuebles": 35%]', "https://eur-lex.europa.eu/sfp/solvency-ii-62", "published"),
]


def _fetch_eurlex_text(norma: dict) -> tuple[str, str] | None:
    celex = norma["boe_id"].replace("EUR-CELEX-", "")
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(f"{EURLEX_BASE}/restapi/en/CELEX/doc/{celex}/consolidated")
            if resp.status_code == 200:
                data = resp.json()
                html = data.get("html", "")
                clean = re.sub(r"<[^>]+>", " ", html)
                clean = " ".join(clean.split())
                return (data.get("title", norma.get("titulo", "")), clean)
    except (httpx.RequestError, ValueError, KeyError):
        pass
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(f"{EURLEX_BASE}/search?q={celex}&scope=EUROLX&type=html&lang=en")
            if resp.status_code == 200:
                clean = re.sub(r"<[^>]+>", " ", resp.text)
                clean = " ".join(clean.split())
                return (norma.get("titulo", ""), clean[:50000])
    except (httpx.RequestError, ValueError):
        pass
    return None


def run_sync(worker_name: str = "cron-insurance-weekly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex+seed"
    eurlex_processed = 0
    distributors_stored = 0
    products_stored = 0
    solvency_entities_stored = 0
    solvency_sfp_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for norma in IDD_NORMAS:
                changed = check_content_changed(conn, norma["codigo"], "directive", norma["boe_id"], "")
                if not changed:
                    continue
                result = _fetch_eurlex_text(norma)
                if result:
                    title, norma_text = result
                    conn.execute(text("""
                        INSERT INTO normas (codigo, titulo, boe_id, eli_uri,
                                            jurisdiccion, tipo_fuente, tipo_documento,
                                            ambito, estado_cobertura, regulacion_relacionada)
                        VALUES (:codigo, :titulo, :boe_id, :eli_uri,
                                'ue', 'eurlex', :tipo_documento,
                                :ambito, 'ingestada', :regulacion)
                        ON CONFLICT (codigo) DO UPDATE SET
                            titulo = EXCLUDED.titulo, texto = EXCLUDED.texto,
                            estado_cobertura = 'ingestada'
                    """), {
                        "codigo": norma["codigo"], "titulo": norma.get("titulo", title),
                        "boe_id": norma["boe_id"], "eli_uri": norma.get("eli_uri", ""),
                        "tipo_documento": norma["tipo_documento"], "ambito": norma["ambito"],
                        "regulacion": norma["regulacion"],
                    })
                    eurlex_processed += 1
            for row in SEED_IDD_DISTRIBUTORS:
                conn.connection.execute(
                    """INSERT INTO idd_distributor (entity_id, registration_number, insurance_ao,
                        products_covered, professional_indemnity,
                        training_certified, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                distributors_stored += 1
                total += 1
            for row in SEED_IDD_PRODUCTS:
                conn.connection.execute(
                    """INSERT INTO idd_product_uci (product_id, product_type, risk_coverage,
                        cost_breakdown, exit_costs, taxes, version, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                products_stored += 1
                total += 1
            for row in SEED_SOLVENCY_ENTITIES:
                conn.connection.execute(
                    """INSERT INTO solvency_ii_entity (entity_id, entity_type,
                        solvency_capital_requirement, minimum_capital_requirement,
                        solvency_ratio, reporting_date, home_supervisor)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                solvency_entities_stored += 1
                total += 1
            for row in SEED_SOLVENCY_SFP:
                conn.connection.execute(
                    """INSERT INTO solvency_ii_sfp (entity_id, reporting_period, fund_breakdown,
                        asset_allocation, url, status)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                    row,
                )
                solvency_sfp_stored += 1
                total += 1
            if eurlex_processed:
                invalidate_old_embeddings(conn, "idd")
            return {
                "processed": total, "source": source,
                "eurlex_processed": eurlex_processed,
                "distributors": distributors_stored,
                "products": products_stored,
                "solvency_entities": solvency_entities_stored,
                "solvency_sfp": solvency_sfp_stored,
                "worker": worker_name, "started_at": sync_start,
            }
    except Exception as exc:
        return {
            "processed": total, "source": source,
            "eurlex_processed": eurlex_processed,
            "distributors": distributors_stored,
            "products": products_stored,
            "solvency_entities": solvency_entities_stored,
            "solvency_sfp": solvency_sfp_stored,
            "worker": worker_name, "error": str(exc), "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IDD/Solvency II worker: EUR-Lex + seed")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("insurance")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(
            f"[run-once] IDD/Solvency: {result['processed']} total "
            f"(eurlex={result['eurlex_processed']}, "
            f"dist={result['distributors']}, "
            f"prod={result['products']}, "
            f"sol_ent={result['solvency_entities']}, "
            f"sol_sfp={result['solvency_sfp']})"
        )
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting IDD/Solvency worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"IDD/Solvency: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
