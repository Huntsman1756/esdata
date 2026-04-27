#!/usr/bin/env python
"""Seed de tipos Seguridad Social 2025 y 2026.

Fuente: Seguridad Social / REI (Regimen Especial de la Industria)
verified_date: 2026-03-20
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    # SS rates — datos de referencia 2025/2026
    # Nota: las cantidades exactas de bases minimas se actualizan con cada resolution ministerial
    ss_rates = [
        (2025, "general", 2207.40, 26488.80, 23.60, None, None, "Seguridad Social 2025 — base general"),
        (2026, "general", 2207.40, 26488.80, 23.60, None, None, "Seguridad Social 2026 — base general provisional"),
    ]

    for row in ss_rates:
        cur.execute(
            """INSERT INTO ss_rates (year, category, base_monthly, base_annual, rate_common, source)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (year, category) DO UPDATE SET
                   base_monthly = EXCLUDED.base_monthly,
                   base_annual = EXCLUDED.base_annual,
                   rate_common = EXCLUDED.rate_common,
                   source = EXCLUDED.source""",
            row,
        )

    conn.commit()
    total = len(ss_rates)
    print(f"OK: {total} registros SS rates insertados")
    conn.close()


if __name__ == "__main__":
    main()
