#!/usr/bin/env python
"""Seed UCITS (Undertakings for Collective Investment in Transferable Securities) data.

Fase 31.9.3 — Expansion regulatoria: AIFMD/UCITS.

Tablas: ucits_fund, ucits_regulatory_report

Fuente: CNMV fund registry + ESAP
verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

UCITS_FUNDS = [
    (
        "Euro Green Bond Fund",
        "Global Asset Management SA",
        "2018-01-10",
        "LU",
        True,
        1200000000.00,
        601,
        "https://www.esap.europa.eu/ucits/euro-green-bond-krid.pdf",
        "Investment in Euro-denominated green bonds",
        "4/7",
        "active",
    ),
    (
        "Iberian Equity Income",
        "Iberian Capital Management",
        "2015-05-20",
        "ES",
        True,
        450000000.00,
        602,
        "https://www.esap.europa.eu/ucits/iberian-equity-krid.pdf",
        "Iberian dividend-paying equities",
        "5/7",
        "active",
    ),
    (
        "Global Tech Leaders UCITS",
        "European Wealth Partners",
        "2020-09-01",
        "IE",
        True,
        2800000000.00,
        603,
        "https://www.esap.europa.eu/ucits/global-tech-krid.pdf",
        "Global technology sector equities",
        "6/7",
        "active",
    ),
    (
        "Spanish Government Bond UCITS",
        "Banco Sabadell Asset Management",
        "2012-03-15",
        "ES",
        True,
        890000000.00,
        604,
        "https://www.esap.europa.eu/ucits/spanish-govt-krid.pdf",
        "Spanish government bonds and agency debt",
        "2/7",
        "active",
    ),
]

UCITS_REPORTS = [
    (1, "annual", "2024", "https://www.esap.europa.eu/ucits/euro-green-bond-annual-2024.pdf", "2025-04-30", "filed"),
    (1, "semi-annual", "2025-H1", "https://www.esap.europa.eu/ucits/euro-green-bond-semi-2025.pdf", "2025-07-31", "filed"),
    (2, "annual", "2024", "https://www.esap.europa.eu/ucits/iberian-equity-annual-2024.pdf", "2025-03-31", "filed"),
    (3, "annual", "2024", "https://www.esap.europa.eu/ucits/global-tech-annual-2024.pdf", "2025-04-15", "filed"),
    (4, "annual", "2024", "https://www.esap.europa.eu/ucits/spanish-govt-annual-2024.pdf", "2025-05-01", "filed"),
]


def _upsert_fund(cur, row):
    cur.execute(
        """INSERT INTO ucits_fund
           (fund_name, management_company, registration_date, home_member_state,
            cross_border_passport, total_aum_eur, depositary_id, krid_url,
            investment_strategy, risk_profile, status)
           VALUES (%s, %s, %s::date, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (fund_name) DO UPDATE SET
             management_company = EXCLUDED.management_company,
             registration_date = EXCLUDED.registration_date,
             home_member_state = EXCLUDED.home_member_state,
             cross_border_passport = EXCLUDED.cross_border_passport,
             total_aum_eur = EXCLUDED.total_aum_eur,
             depositary_id = EXCLUDED.depositary_id,
             krid_url = EXCLUDED.krid_url,
             investment_strategy = EXCLUDED.investment_strategy,
             risk_profile = EXCLUDED.risk_profile,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_report(cur, row):
    cur.execute(
        """INSERT INTO ucits_regulatory_report
           (fund_id, report_type, reporting_period, url, filed_date, status)
           VALUES (%s, %s, %s, %s, %s::date, %s)
           ON CONFLICT (fund_id, report_type, reporting_period) DO UPDATE SET
             url = EXCLUDED.url,
             filed_date = EXCLUDED.filed_date,
             status = EXCLUDED.status""",
        row,
    )


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for row in UCITS_FUNDS:
        _upsert_fund(cur, row)

    for row in UCITS_REPORTS:
        _upsert_report(cur, row)

    conn.commit()
    total = len(UCITS_FUNDS) + len(UCITS_REPORTS)
    print(f"OK: {total} registros UCITS insertados ({len(UCITS_FUNDS)} funds, {len(UCITS_REPORTS)} reports)")
    conn.close()


if __name__ == "__main__":
    main()
