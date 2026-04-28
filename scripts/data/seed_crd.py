#!/usr/bin/env python
"""Seed CRD V/CRR (Capital Requirements Directive / Capital Requirements Regulation) data.

Fase 31.9.4 — Expansion regulatoria: CRD V/CRR, BRRD, EMIR.

Tablas: crd_capital_position, crd_stress_test, brrd_bail_in

Fuente: Banco de Espana + ECB supervisory reports
verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

CRD_POSITIONS = [
    (1, "2025-09-30", 14.5, 16.2, 18.7, 8500000000.00, 9500000000.00, 10950000000.00, 5.8, 58600000000.00, "filed"),
    (2, "2025-09-30", 13.2, 15.1, 17.3, 4200000000.00, 4800000000.00, 5500000000.00, 4.9, 32400000000.00, "filed"),
    (3, "2025-06-30", 15.1, 17.0, 19.4, 12300000000.00, 13800000000.00, 15700000000.00, 6.2, 78900000000.00, "filed"),
]

CRD_STRESS_TESTS = [
    (1, "2025-07-15", "ECB Joint EU-wide stress test 2025", -2.8, -2.5, 11.7, "Banco de Espana", "published"),
    (2, "2025-07-15", "ECB Joint EU-wide stress test 2025", -3.1, -2.8, 10.3, "Banco de Espana", "published"),
    (3, "2025-07-15", "ECB Joint EU-wide stress test 2025", -2.2, -2.0, 12.0, "Banco de Espana", "published"),
    (1, "2024-11-20", "Banco de Espana adverse scenario 2024", -4.5, -4.0, 10.0, "Banco de Espana", "published"),
    (2, "2024-11-20", "Banco de Espana adverse scenario 2024", -5.2, -4.8, 8.0, "Banco de Espana", "published"),
]

BRRD_BAIL_IN = [
    (1, 95000000000.00, 55.0, 58.2, 62.0, "compliant", "active"),
    (2, 42000000000.00, 55.0, 54.8, 58.5, "compliant", "active"),
    (3, 120000000000.00, 55.0, 60.1, 65.0, "compliant", "active"),
]


def _upsert_position(cur, row):
    cur.execute(
        """INSERT INTO crd_capital_position
           (entity_id, reporting_date, cet1_ratio, tier1_ratio, total_capital_ratio,
            cet1_amount, tier1_amount, total_capital_amount, leverage_ratio,
            risk_weighted_assets, status)
           VALUES (%s, %s::date, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (entity_id, reporting_date) DO UPDATE SET
             cet1_ratio = EXCLUDED.cet1_ratio,
             tier1_ratio = EXCLUDED.tier1_ratio,
             total_capital_ratio = EXCLUDED.total_capital_ratio,
             cet1_amount = EXCLUDED.cet1_amount,
             tier1_amount = EXCLUDED.tier1_amount,
             total_capital_amount = EXCLUDED.total_capital_amount,
             leverage_ratio = EXCLUDED.leverage_ratio,
             risk_weighted_assets = EXCLUDED.risk_weighted_assets,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_stress_test(cur, row):
    cur.execute(
        """INSERT INTO crd_stress_test
           (entity_id, test_date, scenario_name, cet1_impact_pct, tier1_impact_pct,
            capital_ratio_post_test, competent_authority, status)
           VALUES (%s, %s::date, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (entity_id, test_date, scenario_name) DO UPDATE SET
             cet1_impact_pct = EXCLUDED.cet1_impact_pct,
             tier1_impact_pct = EXCLUDED.tier1_impact_pct,
             capital_ratio_post_test = EXCLUDED.capital_ratio_post_test,
             competent_authority = EXCLUDED.competent_authority,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_bail_in(cur, row):
    cur.execute(
        """INSERT INTO brrd_bail_in
           (entity_id, total_eligible_liabilities, mrel_target_pct, mrel_compliance_pct,
            internal_mrel, resolution_status, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (entity_id) DO UPDATE SET
             total_eligible_liabilities = EXCLUDED.total_eligible_liabilities,
             mrel_target_pct = EXCLUDED.mrel_target_pct,
             mrel_compliance_pct = EXCLUDED.mrel_compliance_pct,
             internal_mrel = EXCLUDED.internal_mrel,
             resolution_status = EXCLUDED.resolution_status,
             status = EXCLUDED.status""",
        row,
    )


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for row in CRD_POSITIONS:
        _upsert_position(cur, row)

    for row in CRD_STRESS_TESTS:
        _upsert_stress_test(cur, row)

    for row in BRRD_BAIL_IN:
        _upsert_bail_in(cur, row)

    conn.commit()
    total = len(CRD_POSITIONS) + len(CRD_STRESS_TESTS) + len(BRRD_BAIL_IN)
    print(f"OK: {total} registros CRD/BRRD insertados ({len(CRD_POSITIONS)} capital positions, {len(CRD_STRESS_TESTS)} stress tests, {len(BRRD_BAIL_IN)} bail-in)")
    conn.close()


if __name__ == "__main__":
    main()
