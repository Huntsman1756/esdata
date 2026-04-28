#!/usr/bin/env python
"""Seed SFDR (Sustainable Finance Disclosure Regulation) data.

Fase 31.9.1 — Expansion regulatoria: SFDR.

Tablas: sfdr_product, sfdr_paci_indicator, sfdr_entity_paci,
        sfdr_pre_contractual, sfdr_annual_report

Fuente: ESAP (European Single Access Point) + CNMV
verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

SFDR_PRODUCTS = [
    (
        "Green Equity Fund SRI",
        "art-8",
        "Inversion sostenible con criterios ESG integrados",
        "true",
        '{"sa_1_co2": 150.5, "sa_2_carbon_intensity": 85.2}',
        "https://www.esap-finance.eu/sfdr/paci/green-equity-sri",
        '["ES", "FR", "DE", "PT"]',
        "active",
    ),
    (
        "EU Climate Transition ETF",
        "art-8",
        "Indice alineado con transicion climatica EU",
        "true",
        '{"sa_1_co2": 95.0, "sa_3_fossil": 0.05}',
        "https://www.esap-finance.eu/sfdr/paci/climate-transition-etf",
        '["ES", "DE", "NL", "BE"]',
        "active",
    ),
    (
        "Global Impact Fund",
        "art-9",
        "Inversion de impacto con objetivos ODS",
        "true",
        '{"sa_1_co2": 50.0, "sa_5_water": 0.02}',
        "https://www.esap-finance.eu/sfdr/paci/global-impact",
        '["ES", "FR", "IT", "PT"]',
        "active",
    ),
    (
        "ESR Equities Europe",
        "art-8",
        "Acciones Europa con consideracion PCAI",
        "true",
        '{"sa_1_co2": 120.0}',
        "https://www.esap-finance.eu/sfdr/paci/esr-europe",
        '["ES", "FR", "DE"]',
        "active",
    ),
    (
        "Standard Euro Bond Fund",
        "art-6",
        None,
        "false",
        None,
        None,
        '["ES"]',
        "active",
    ),
]

SFDR_PACAI_INDICATORS = [
    (1, "sa.1", "Greenhouse gas emissions", 150.5, "tCO2e", "2024", "Scope 1+2", "active"),
    (1, "sa.2", "Carbon footprint", 85.2, "tCO2e/M EUR", "2024", "Total portfolio", "active"),
    (1, "sa.4", "Exposure to fossil gas companies", 0.02, "% NAV", "2024", "Revenue threshold 1%", "active"),
    (2, "sa.1", "Greenhouse gas emissions", 95.0, "tCO2e", "2024", "Scope 1+2+3", "active"),
    (2, "sa.3", "Exposure to fossil gas", 0.05, "% NAV", "2024", "Revenue threshold 5%", "active"),
    (3, "sa.1", "Greenhouse gas emissions", 50.0, "tCO2e", "2024", "Scope 1+2", "active"),
    (3, "sa.5", "Water and marine pollution", 0.02, "% NAV", "2024", "Portfolio weighted", "active"),
    (4, "sa.1", "Greenhouse gas emissions", 120.0, "tCO2e", "2024", "Scope 1+2", "active"),
]

SFDR_ENTITY_PACI = [
    (1, 2024, '{"total_paci_score": 72.5, "sectors_covered": 12}', '{"decarbonization_rate": 15.2, "target_year": 2030}', "active"),
    (2, 2024, '{"total_paci_score": 68.0, "sectors_covered": 8}', '{"decarbonization_rate": 22.0, "target_year": 2028}', "active"),
]

SFDR_PRE_CONTRACTUAL = [
    (1, "KID", "https://www.esap-finance.eu/sfdr/kid/green-equity-sri", "2025-01-15", "v2.1", "active"),
    (1, "PPI", "https://www.esap-finance.eu/sfdr/ppi/green-equity-sri", "2025-01-15", "v2.1", "active"),
    (2, "KID", "https://www.esap-finance.eu/sfdr/kid/climate-transition-etf", "2025-02-01", "v1.0", "active"),
    (3, "KID", "https://www.esap-finance.eu/sfdr/kid/global-impact", "2025-03-10", "v3.0", "active"),
    (3, "PPI", "https://www.esap-finance.eu/sfdr/ppi/global-impact", "2025-03-10", "v3.0", "active"),
    (4, "KID", "https://www.esap-finance.eu/sfdr/kid/esr-europe", "2024-11-20", "v1.5", "active"),
]

SFDR_ANNUAL_REPORTS = [
    (1, 2024, '{"paci_score": 72.5, "indicators_measured": 12}', '{"engagement_companies": 45, "proxy_voting_yes_pct": 82}', "Best practice: exclusion of thermal coal producers", "https://www.esap-finance.eu/sfdr/ar/green-equity-sri-2024", "2025-04-30", "active"),
    (2, 2024, '{"paci_score": 68.0, "indicators_measured": 9}', '{"engagement_companies": 30, "proxy_voting_yes_pct": 75}', "Best practice: climate alignment monitoring", "https://www.esap-finance.eu/sfdr/ar/climate-transition-2024", "2025-03-31", "active"),
]


def _upsert_product(cur, row):
    cur.execute(
        """INSERT INTO sfdr_product
           (product_name, product_type, sustainability_strategy, principal_adverse_impact,
            paci_aggregated, paci_detailed_url, distribution_country, status)
           VALUES (%s, %s, %s, %s, %s::json, %s, %s::json, %s)
           ON CONFLICT (product_name) DO UPDATE SET
             paci_aggregated = EXCLUDED.paci_aggregated,
             paci_detailed_url = EXCLUDED.paci_detailed_url,
             distribution_country = EXCLUDED.distribution_country,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_pacai(cur, row):
    cur.execute(
        """INSERT INTO sfdr_paci_indicator
           (product_id, indicator_code, indicator_name, value, unit,
            reference_period, methodology, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (product_id, indicator_code) DO UPDATE SET
             reference_period = EXCLUDED.reference_period,
             methodology = EXCLUDED.methodology,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_entity_paci(cur, row):
    cur.execute(
        """INSERT INTO sfdr_entity_paci
           (entity_id, reporting_year, aggregated_paci, sectoral_decarbonization, status)
           VALUES (%s, %s, %s::json, %s::json, %s)
           ON CONFLICT (entity_id, reporting_year) DO UPDATE SET
             aggregated_paci = EXCLUDED.aggregated_paci,
             sectoral_decarbonization = EXCLUDED.sectoral_decarbonization,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_pre_contractual(cur, row):
    cur.execute(
        """INSERT INTO sfdr_pre_contractual
           (product_id, document_type, url, published_date, version, status)
           VALUES (%s, %s, %s, %s::date, %s, %s)
           ON CONFLICT (product_id, document_type) DO UPDATE SET
             url = EXCLUDED.url,
             version = EXCLUDED.version,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_annual_report(cur, row):
    cur.execute(
        """INSERT INTO sfdr_annual_report
           (entity_id, reporting_year, paci_results, engagement_activities,
            good_practice_examples, url, published_date, status)
           VALUES (%s, %s, %s::json, %s::json, %s, %s, %s::date, %s)
           ON CONFLICT (entity_id, reporting_year) DO UPDATE SET
             url = EXCLUDED.url,
             published_date = EXCLUDED.published_date,
             status = EXCLUDED.status""",
        row,
    )


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for row in SFDR_PRODUCTS:
        _upsert_product(cur, row)

    for row in SFDR_PACAI_INDICATORS:
        _upsert_pacai(cur, row)

    for row in SFDR_ENTITY_PACI:
        _upsert_entity_paci(cur, row)

    for row in SFDR_PRE_CONTRACTUAL:
        _upsert_pre_contractual(cur, row)

    for row in SFDR_ANNUAL_REPORTS:
        _upsert_annual_report(cur, row)

    conn.commit()
    total = len(SFDR_PRODUCTS) + len(SFDR_PACAI_INDICATORS) + len(SFDR_ENTITY_PACI) + len(SFDR_PRE_CONTRACTUAL) + len(SFDR_ANNUAL_REPORTS)
    print(f"OK: {total} registros SFDR insertados ({len(SFDR_PRODUCTS)} products, {len(SFDR_PACAI_INDICATORS)} PACAI, {len(SFDR_ENTITY_PACI)} entity PACI, {len(SFDR_PRE_CONTRACTUAL)} pre-contractual, {len(SFDR_ANNUAL_REPORTS)} annual reports)")
    conn.close()


if __name__ == "__main__":
    main()
