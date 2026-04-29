#!/usr/bin/env python3
"""Seed PRIIPs + LIVMC — KID documents, products y proteccion al cliente.

Crea productos PRIIPs de ejemplo con KID, y datos LIVMC de proteccion al cliente.

Uso:
    python scripts/data/seed_priips.py [--dry-run] [--database-url URL]
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

PRODUCTS_DATA = [
    {
        "product_name": "Fondo Renta Fija Europa",
        "underlying_assets": [{"type": "bond", "issuer": "EU Sovereign", "weight": 0.6}, {"type": "corporate_bond", "issuer": "Euro IG", "weight": 0.4}],
        "maturity_date": "2030-12-31",
        "currency": "EUR",
        "min_investment": 3000.00,
        "distribution_channels": ["bank_advisor", "online_platform", "broker"],
        "status": "active",
    },
    {
        "product_name": "ETF MSCI World UCITS",
        "underlying_assets": [{"type": "equity", "index": "MSCI World", "weight": 1.0}],
        "maturity_date": None,
        "currency": "EUR",
        "min_investment": 100.00,
        "distribution_channels": ["exchange", "online_platform"],
        "status": "active",
    },
    {
        "product_name": "Plan Pensiones Iberbank",
        "underlying_assets": [{"type": "mixed", "equity": 0.4, "fixed_income": 0.6}],
        "maturity_date": "2045-01-01",
        "currency": "EUR",
        "min_investment": 100.00,
        "distribution_channels": ["bank_advisor", "employer"],
        "status": "active",
    },
    {
        "product_name": "Certificado Barrier Reverse Callable",
        "underlying_assets": [{"type": "equity", "issuer": "Iberdrola", "weight": 1.0}],
        "maturity_date": "2027-06-15",
        "currency": "EUR",
        "min_investment": 1000.00,
        "distribution_channels": ["bank_advisor", "broker"],
        "status": "active",
    },
    {
        "product_name": "Fondo Venture Capital Innovacion",
        "underlying_assets": [{"type": "equity", "sector": "tech", "weight": 0.85}, {"type": "cash", "weight": 0.15}],
        "maturity_date": "2032-12-31",
        "currency": "EUR",
        "min_investment": 50000.00,
        "distribution_channels": ["private_bank", "independent_advisor"],
        "status": "active",
    },
]

KID_DATA = [
    {"product_id": None, "product_type": "fund", "currency": "EUR", "risk_scale": 3, "cost_impact": {"entry": 0.0, "annual": 1.25, "total_1y": 1.25, "total_5y": 6.80}, "negative_scenario_returns": {"worst": -15.0, "moderate": -5.0, "best": 2.0}, "version": "2025-v3", "publication_date": "2025-01-15", "status": "active"},
    {"product_id": None, "product_type": "etf", "currency": "EUR", "risk_scale": 5, "cost_impact": {"entry": 0.0, "annual": 0.25, "total_1y": 0.25, "total_5y": 1.30}, "negative_scenario_returns": {"worst": -35.0, "moderate": -15.0, "best": 8.0}, "version": "2025-v1", "publication_date": "2025-03-01", "status": "active"},
    {"product_id": None, "product_type": "pension_product", "currency": "EUR", "risk_scale": 4, "cost_impact": {"entry": 1.0, "annual": 1.75, "total_1y": 2.80, "total_5y": 9.50}, "negative_scenario_returns": {"worst": -20.0, "moderate": -8.0, "best": 4.0}, "version": "2025-v2", "publication_date": "2025-02-20", "status": "active"},
    {"product_id": None, "product_type": "structured_product", "currency": "EUR", "risk_scale": 6, "cost_impact": {"entry": 2.0, "annual": 0.50, "total_1y": 2.55, "total_5y": 13.00}, "negative_scenario_returns": {"worst": -100.0, "moderate": -30.0, "best": 12.0}, "version": "2025-v1", "publication_date": "2025-04-10", "status": "active"},
    {"product_id": None, "product_type": "fund", "currency": "EUR", "risk_scale": 7, "cost_impact": {"entry": 0.5, "annual": 2.50, "total_1y": 3.05, "total_5y": 17.00}, "negative_scenario_returns": {"worst": -100.0, "moderate": -40.0, "best": 15.0}, "version": "2025-v1", "publication_date": "2025-05-01", "status": "active"},
]

LIVMC_PROTECTION_DATA = [
    {"client_id": None, "protection_type": "compensation_scheme", "provider_id": None, "coverage_amount": 20000.00, "status": "active"},
    {"client_id": None, "protection_type": "segregation_assets", "provider_id": None, "coverage_amount": None, "status": "active"},
    {"client_id": None, "protection_type": "fiduciary_duty", "provider_id": None, "coverage_amount": None, "status": "active"},
    {"client_id": None, "protection_type": "suitability_assessment", "provider_id": None, "coverage_amount": None, "status": "active"},
]

LIVMC_VOICE_DATA = [
    {"entity_id": None, "procedure_type": "complaint", "description": "Procedimiento de reclamaciones para productos PRIIPs conforme a Reglamento (UE) 1286/2014", "effective_date": "2024-01-01", "next_review": "2026-01-01", "status": "active"},
    {"entity_id": None, "procedure_type": "voice", "description": "Canal de voz para inversores minoristas sobre productos de inversion", "effective_date": "2024-01-01", "next_review": "2026-01-01", "status": "active"},
    {"entity_id": None, "procedure_type": "dispute_resolution", "description": "Arbitraje de consumo para conflictos en productos PRIIPs", "effective_date": "2024-06-01", "next_review": "2026-06-01", "status": "active"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed PRIIPs + LIVMC data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(PRODUCTS_DATA)} PRIIPs products")
        print(f"[DRY RUN] Would insert {len(KID_DATA)} KID documents")
        print(f"[DRY RUN] Would insert {len(LIVMC_PROTECTION_DATA)} client protections")
        print(f"[DRY RUN] Would insert {len(LIVMC_VOICE_DATA)} voice procedures")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert products
    product_ids = []
    for p in PRODUCTS_DATA:
        cur.execute(
            """INSERT INTO priips_product (product_name, underlying_assets, maturity_date,
               currency, min_investment, distribution_channels, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (p["product_name"], json.dumps(p["underlying_assets"]), p["maturity_date"],
             p["currency"], float(p["min_investment"]), json.dumps(p["distribution_channels"]),
             p["status"]),
        )
        product_ids.append(cur.fetchone()[0])

    # Insert KIDs with product_id references
    for i, k in enumerate(KID_DATA):
        cur.execute(
            """INSERT INTO priips_kid (product_id, product_type, currency, risk_scale,
               cost_impact, negative_scenario_returns, version, publication_date, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (product_ids[i] if i < len(product_ids) else None, k["product_type"], k["currency"],
             k["risk_scale"], json.dumps(k["cost_impact"]), json.dumps(k["negative_scenario_returns"]),
             k["version"], k["publication_date"], k["status"]),
        )

    # Insert LIVMC client protections
    for lp in LIVMC_PROTECTION_DATA:
        cur.execute(
            """INSERT INTO livmc_client_protection (client_id, protection_type, provider_id,
               coverage_amount, status)
               VALUES (%(client_id)s, %(protection_type)s, %(provider_id)s,
                       %(coverage_amount)s, %(status)s)""",
            lp,
        )

    # Insert LIVMC voice procedures
    for lv in LIVMC_VOICE_DATA:
        cur.execute(
            """INSERT INTO livmc_voice_procedure (entity_id, procedure_type, description,
               effective_date, next_review, status)
               VALUES (%(entity_id)s, %(procedure_type)s, %(description)s,
                       %(effective_date)s, %(next_review)s, %(status)s)""",
            lv,
        )

    conn.commit()
    total = len(PRODUCTS_DATA) + len(KID_DATA) + len(LIVMC_PROTECTION_DATA) + len(LIVMC_VOICE_DATA)
    print(f"OK: {total} registros PRIIPs/LIVMC insertados ({len(PRODUCTS_DATA)} products, {len(KID_DATA)} KIDs, {len(LIVMC_PROTECTION_DATA)} protections, {len(LIVMC_VOICE_DATA)} procedures)")
    conn.close()


if __name__ == "__main__":
    main()
