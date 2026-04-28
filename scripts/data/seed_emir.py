#!/usr/bin/env python
"""Seed EMIR (European Market Infrastructure Regulation) data.

Fase 31.9.4 — Expansion regulatoria: CRD V/CRR, BRRD, EMIR.

Tablas: emir_trade_report, emir_clearing_member

Fuente: CNMV + ESMA trade repositories
verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

EMIR_TRADES = [
    ("EMIR-2025-001-TR-001", "credit", "credit default swap", True, 1, "financial", "reported"),
    ("EMIR-2025-001-TR-002", "interest-rate", "interest rate swap", True, 0, "financial", "reported"),
    ("EMIR-2025-001-TR-003", "equity", "total return swap", False, 2, "non-financial", "reported"),
    ("EMIR-2025-002-TR-001", "energy", "power futures", True, 0, "financial", "reported"),
    ("EMIR-2025-002-TR-002", "fx", "cross currency swap", True, 1, "financial", "reported"),
    ("EMIR-2025-002-TR-003", "commodity", "oil swap", False, 3, "non-financial", "reported"),
    ("EMIR-2025-003-TR-001", "credit", "credit default swap", True, 0, "financial", "reported"),
    ("EMIR-2025-003-TR-002", "interest-rate", "basis swap", True, 0, "financial", "reported"),
    ("EMIR-2025-003-TR-003", "equity", "equity option", False, 1, "other", "reported"),
    ("EMIR-2025-003-TR-004", "fx", "fx forward", False, 0, "financial", "reported"),
]

EMIR_CLEARING_MEMBERS = [
    (1, "EMIR-CM-2019-001", "central", "active"),
    (2, "EMIR-CM-2020-002", "central", "active"),
    (3, "EMIR-CM-2018-003", "otc", "active"),
]


def _upsert_trade(cur, row):
    cur.execute(
        """INSERT INTO emir_trade_report
           (trade_id, asset_class, instrument_class, clearing_obligation_applied,
            reporting_delay_days, counterparty_type, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (trade_id) DO UPDATE SET
             asset_class = EXCLUDED.asset_class,
             instrument_class = EXCLUDED.instrument_class,
             clearing_obligation_applied = EXCLUDED.clearing_obligation_applied,
             reporting_delay_days = EXCLUDED.reporting_delay_days,
             counterparty_type = EXCLUDED.counterparty_type,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_clearing_member(cur, row):
    cur.execute(
        """INSERT INTO emir_clearing_member
           (entity_id, emir_registration, clearing_type, status)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (entity_id) DO UPDATE SET
             emir_registration = EXCLUDED.emir_registration,
             clearing_type = EXCLUDED.clearing_type,
             status = EXCLUDED.status""",
        row,
    )


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for row in EMIR_TRADES:
        _upsert_trade(cur, row)

    for row in EMIR_CLEARING_MEMBERS:
        _upsert_clearing_member(cur, row)

    conn.commit()
    total = len(EMIR_TRADES) + len(EMIR_CLEARING_MEMBERS)
    print(f"OK: {total} registros EMIR insertados ({len(EMIR_TRADES)} trade reports, {len(EMIR_CLEARING_MEMBERS)} clearing members)")
    conn.close()


if __name__ == "__main__":
    main()
