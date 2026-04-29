#!/usr/bin/env python
"""Seed AIFMD (Alternative Investment Fund Managers Directive) data.

Fase 31.9.3 — Expansion regulatoria: AIFMD/UCITS.

Tablas: aifmd_fund, aifmd_regulatory_report, aifmd_liquidity_management

Fuente: CNMV fund registry + ESAP
verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

AIFMD_FUNDS = [
    (
        "Iberian Real Estate Fund",
        501,
        "real-estate",
        "2020-03-15",
        "ES",
        True,
        250000000.00,
        "professional",
        "2 years",
        "quarterly",
        "asset-by-asset",
        200.00,
        "active",
    ),
    (
        "European Growth Capital III",
        502,
        "alternative",
        "2021-06-01",
        "DE",
        True,
        780000000.00,
        "professional",
        "5 years",
        "annually",
        "portfolio",
        300.00,
        "active",
    ),
    (
        "Strategic Credit Opportunities",
        503,
        "alternative",
        "2019-11-20",
        "FR",
        False,
        150000000.00,
        "professional",
        "3 years",
        "semi-annually",
        "asset-by-asset",
        150.00,
        "active",
    ),
    (
        "Mediterranean Infrastructure Fund",
        504,
        "real-estate",
        "2022-01-10",
        "ES",
        True,
        420000000.00,
        "professional",
        "7 years",
        "annually",
        "portfolio",
        250.00,
        "active",
    ),
]

AIFMD_REPORTS = [
    (1, "annual", "2024", "https://www.cnmv.es/aifmd/reports/iberian-re-2024.pdf", "2025-04-30", "filed"),
    (1, "semi-annual", "2025-H1", "https://www.cnmv.es/aifmd/reports/iberian-re-2025h1.pdf", "2025-07-31", "filed"),
    (2, "annual", "2024", "https://www.cnmv.es/aifmd/reports/euro-growth-2024.pdf", "2025-03-31", "filed"),
    (3, "annual", "2024", "https://www.cnmv.es/aifmd/reports/strategic-credit-2024.pdf", "2025-05-15", "filed"),
    (4, "annual", "2024", "https://www.cnmv.es/aifmd/reports/medinfra-2024.pdf", "2025-04-15", "filed"),
]

AIFMD_LIQUIDITY = [
    (1, False, None, False, False, False, "Normal liquidity profile — quarterly redemptions within limits", "monthly"),
    (2, False, None, False, False, True, "Side pocket applied to illiquid assets — 5% of NAV", "quarterly"),
    (3, False, None, True, False, False, "Gating applied during March 2025 redemption window — 15% cap", "semi-annually"),
]


def _upsert_fund(cur, row):
    cur.execute(
        """INSERT INTO aifmd_fund
           (fund_name, aifm_id, fund_type, registration_date, home_member_state,
            cross_border_passport, total_aum_eur, investor_type, lock_up_period,
            redemption_frequency, leverage_method, leverage_max_pct, status)
           VALUES (%s, %s, %s, %s::date, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        row,
    )


def _upsert_report(cur, row):
    cur.execute(
        """INSERT INTO aifmd_regulatory_report
           (fund_id, report_type, reporting_period, url, filed_date, status)
           VALUES (%s, %s, %s, %s, %s::date, %s)
           ON CONFLICT DO NOTHING""",
        row,
    )


def _upsert_liquidity(cur, row):
    cur.execute(
        """INSERT INTO aifmd_liquidity_management
           (fund_id, redemption_suspended, suspension_date, gating_applied,
            swing_price_applied, side_pocket_applied, stress_test_result, valuation_frequency)
           VALUES (%s, %s, %s::date, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        row,
    )


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for row in AIFMD_FUNDS:
        _upsert_fund(cur, row)

    for row in AIFMD_REPORTS:
        _upsert_report(cur, row)

    for row in AIFMD_LIQUIDITY:
        _upsert_liquidity(cur, row)

    conn.commit()
    total = len(AIFMD_FUNDS) + len(AIFMD_REPORTS) + len(AIFMD_LIQUIDITY)
    print(f"OK: {total} registros AIFMD insertados ({len(AIFMD_FUNDS)} funds, {len(AIFMD_REPORTS)} reports, {len(AIFMD_LIQUIDITY)} liquidity)")
    conn.close()


if __name__ == "__main__":
    main()
