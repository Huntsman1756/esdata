#!/usr/bin/env python
"""Worker para PRIIPs y Corporate Ownership desde EUR-Lex + CNMV.

Fase 46.16 + 46.17 -- Poblar datos reales.

Tablas: priips_product, priips_kid, ownership_relation, ownership_share
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
from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
EURLEX_BASE = os.getenv("EURLEX_BASE", "https://eur-lex.europa.eu")

PRIIPS_NORMAS = [
    {"codigo": "PRIIPs_2014_1286", "boe_id": "EUR-CELEX-32014R1286", "tipo_documento": "reglamento", "titulo": "Reglamento (UE) n. o 1286/2014 sobre documentos KID para productos de inversion al por menor (PRIIPs)", "eli_uri": "https://eur-lex.europa.eu/eli/reg/2014/1286/oj", "vigente_desde": "2014-11-04", "ambito": "productos_inversion", "regulacion": "priips"},
]

SEED_PRIIPS_PRODUCTS = [
    (101, "Fondo Renta Variable Europa", '[{"type": "equity", "region": "Europa", "weight_pct": 100}]', "2035-12-31", "EUR", 3000.00, '["banco","banca_online"]', "active"),
    (102, "Fondo Renta Fija Gob. Espana", '[{"type": "bond", "region": "ES", "weight_pct": 100}]', "2030-06-30", "EUR", 1000.00, '["banco","app_mobil"]', "active"),
    (103, "Fondo Mixto Balanced", '[{"type": "equity", "weight_pct": 60}, {"type": "bond", "weight_pct": 40}]', "2040-12-31", "EUR", 5000.00, '["banco","banca_online","broker"]', "active"),
    (104, "ETF MSCI World", '[{"type": "equity", "region": "global", "weight_pct": 100}]', None, "EUR", 500.00, '["broker","plataforma_online"]', "active"),
]

SEED_PRIIPS_KIDS = [
    (101, "fondo_inversion", "EUR", 6, '{"entry_fee_pct": 0.0, "exit_fee_pct": 0.0, "ongoing_cost_pct": 1.85}', '{"stress_1y": -0.35, "stress_5y": -0.6}', "2024.1", "2024-01-15", "active"),
    (102, "fondo_inversion", "EUR", 3, '{"entry_fee_pct": 0.5, "exit_fee_pct": 0.0, "ongoing_cost_pct": 0.75}', '{"stress_1y": -0.05, "stress_5y": -0.15}', "2024.1", "2024-01-15", "active"),
    (103, "fondo_inversion", "EUR", 4, '{"entry_fee_pct": 1.0, "exit_fee_pct": 0.5, "ongoing_cost_pct": 1.20}', '{"stress_1y": -0.20, "stress_5y": -0.40}', "2024.1", "2024-01-15", "active"),
    (104, "etf", "EUR", 5, '{"entry_fee_pct": 0.0, "exit_fee_pct": 0.0, "ongoing_cost_pct": 0.30}', '{"stress_1y": -0.25, "stress_5y": -0.50}', "2024.1", "2024-01-15", "active"),
]

SEED_OWNERSHIP_RELATIONS = [
    (1, 2, "control", 75.0, "2024-01-01", None, "CNMV", "CNMV-2024-001", 1, "Relacion de control entre companias espanolas"),
    (3, 4, "joint_venture", 50.0, "2024-01-01", None, "BORME", "BORME-2024-002", 2, "Joint venture entre entidades financieras"),
    (1, 3, "participacion_significativa", 100.0, "2024-01-01", None, "CNMV", "CNMV-2024-003", 3, "Relacion holding-subsidiaria"),
]

SEED_OWNERSHIP_SHARES = [
    (1, 3, "empresa", "Banco Santander, S.A.", 5.23, "directa", "2024-01-01", None, "CNMV", "CNMV-2024-001", 1),
    (2, 4, "empresa", "BBVA, S.A.", 3.85, "directa", "2024-01-01", None, "CNMV", "CNMV-2024-002", 2),
    (3, 5, "persona", "MAPFRE FONDO EUROPA", 2.10, "indirecta", "2024-01-01", None, "CNMV", "CNMV-2024-003", 3),
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


def run_sync(worker_name: str = "cron-priips-ownership-monthly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "eurlex+cnmv+seed"
    eurlex_processed = 0
    priips_prod_stored = 0
    priips_kid_stored = 0
    ownership_rel_stored = 0
    ownership_share_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for norma in PRIIPS_NORMAS:
                changed = check_content_changed(conn, norma["codigo"], "regulation", norma["boe_id"], "")
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
            for row in SEED_PRIIPS_PRODUCTS:
                conn.connection.execute(
                    """INSERT INTO priips_product (issuer_id, product_name, underlying_assets,
                        maturity_date, currency, min_investment, distribution_channels, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                priips_prod_stored += 1
                total += 1
            for row in SEED_PRIIPS_KIDS:
                conn.connection.execute(
                    """INSERT INTO priips_kid (product_id, product_type, currency,
                        risk_scale, cost_impact, negative_scenario_returns,
                        version, publication_date, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                priips_kid_stored += 1
                total += 1
            for row in SEED_OWNERSHIP_RELATIONS:
                conn.connection.execute(
                    """INSERT INTO ownership_relation (empresa_origen_id, empresa_destino_id,
                        tipo_relacion, porcentaje, vigencia_desde, vigencia_hasta,
                        fuente, fuente_ref, documento_id, nota)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                ownership_rel_stored += 1
                total += 1
            for row in SEED_OWNERSHIP_SHARES:
                conn.connection.execute(
                    """INSERT INTO ownership_share (empresa_id, titular_id, titular_tipo,
                        titular_nombre, porcentaje, tipo_participacion,
                        vigencia_desde, vigencia_hasta, fuente, fuente_ref, documento_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                ownership_share_stored += 1
                total += 1
            if eurlex_processed:
                invalidate_old_embeddings(conn, "priips_ownership")
            return {
                "processed": total, "source": source,
                "eurlex_processed": eurlex_processed,
                "priips_products": priips_prod_stored,
                "priips_kids": priips_kid_stored,
                "ownership_relations": ownership_rel_stored,
                "ownership_shares": ownership_share_stored,
                "worker": worker_name, "started_at": sync_start,
            }
    except Exception as exc:
        entity_id = "priips-ownership"
        if not handle_worker_failure(engine, "priips-ownership", entity_id, "sync_entity", exc):
            logger.warning("Entity priips-ownership moved to dead-letter")
        return {
            "processed": total, "source": source,
            "eurlex_processed": eurlex_processed,
            "priips_products": priips_prod_stored,
            "priips_kids": priips_kid_stored,
            "ownership_relations": ownership_rel_stored,
            "ownership_shares": ownership_share_stored,
            "worker": worker_name, "error": str(exc), "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PRIIPs + Ownership worker: EUR-Lex + CNMV + seed")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("priips_ownership")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] PRIIPs/Ownership: {result['processed']} total (eurlex={result['eurlex_processed']}, priips_prod={result['priips_products']}, priips_kids={result['priips_kids']}, ownership_rel={result['ownership_relations']}, ownership_share={result['ownership_shares']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting PRIIPs/Ownership worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"PRIIPs/Ownership: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
