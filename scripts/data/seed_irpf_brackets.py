#!/usr/bin/env python
"""Seed tramos IRPF 2025 — escalas estatal, minimos personales, reduccion rendimientos trabajo.

Fuente: Ley 35/2006 (LIRPF) + Ley 7/2024 + Ley 5/2025
verified_date: 2026-03-20
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    try:
        general_brackets = [
            (2025, "general", "state", 0, 12450, 9.50, "Ley 35/2006, art. 63.1. Escala estatal vigente desde 2021"),
            (2025, "general", "state", 12450, 20200, 12.00, "Ley 35/2006, art. 63.1"),
            (2025, "general", "state", 20200, 35200, 15.00, "Ley 35/2006, art. 63.1"),
            (2025, "general", "state", 35200, 60000, 18.50, "Ley 35/2006, art. 63.1"),
            (2025, "general", "state", 60000, 300000, 22.50, "Ley 35/2006, art. 63.1"),
            (2025, "general", "state", 300000, None, 24.50, "Ley 35/2006, art. 63.1"),
        ]

        for row in general_brackets:
            cur.execute(
                """INSERT INTO irpf_brackets (year, bracket_type, territory, from_amount, to_amount, rate, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (year, bracket_type, territory, from_amount, to_amount) DO UPDATE SET
                       rate = EXCLUDED.rate, source = EXCLUDED.source""",
                row,
            )

        savings_brackets = [
            (2025, "savings", "state", 0, 6000, 9.50, "Ley 35/2006, art. 66. Modificado por Ley 7/2024: tramo >300K pasa de 14% a 15% estatal (28% a 30% total) desde 2025"),
            (2025, "savings", "state", 6000, 50000, 10.50, "Ley 35/2006, art. 66"),
            (2025, "savings", "state", 50000, 200000, 11.50, "Ley 35/2006, art. 66"),
            (2025, "savings", "state", 200000, 300000, 13.50, "Ley 35/2006, art. 66"),
            (2025, "savings", "state", 300000, None, 15.00, "Ley 35/2006, art. 66. Ley 7/2024"),
        ]

        for row in savings_brackets:
            cur.execute(
                """INSERT INTO irpf_brackets (year, bracket_type, territory, from_amount, to_amount, rate, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (year, bracket_type, territory, from_amount, to_amount) DO UPDATE SET
                       rate = EXCLUDED.rate, source = EXCLUDED.source""",
                row,
            )

        personal_minimums = [
            (2025, "taxpayer", "general", 5550, "Ley 35/2006, art. 57"),
            (2025, "taxpayer", "age_65_plus", 6700, "Ley 35/2006, art. 57"),
            (2025, "taxpayer", "age_75_plus", 8100, "Ley 35/2006, art. 57"),
            (2025, "descendants", "first", 2400, "Ley 35/2006, art. 58"),
            (2025, "descendants", "second", 2700, "Ley 35/2006, art. 58"),
            (2025, "descendants", "third", 4000, "Ley 35/2006, art. 58"),
            (2025, "descendants", "fourth_and_beyond", 4500, "Ley 35/2006, art. 58"),
            (2025, "descendants", "under_3_additional", 2800, "Ley 35/2006, art. 58"),
            (2025, "ascendants", "age_65_plus", 1150, "Ley 35/2006, art. 59"),
            (2025, "ascendants", "age_75_plus", 2550, "Ley 35/2006, art. 59"),
            (2025, "disability", "33_to_65_percent", 3000, "Ley 35/2006, art. 60"),
            (2025, "disability", "65_plus_percent", 9000, "Ley 35/2006, art. 60"),
            (2025, "disability", "mobility_assistance", 3000, "Ley 35/2006, art. 60"),
        ]

        for row in personal_minimums:
            cur.execute(
                """INSERT INTO irpf_personal_minimums (year, category, subcategory, amount, source)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (year, category, subcategory) DO UPDATE SET
                       amount = EXCLUDED.amount, source = EXCLUDED.source""",
                row,
            )

        work_reductions = [
            (2025, "scale", None, None, 14852, None, 7302, None, None, "Ley 35/2006, art. 20. RDL 4/2024 (coeficientes 1.75 y 1.14, vigentes desde 2024)"),
            (2025, "scale", 14852, 17673.52, None, "7302 - 1.75 * (net_income - 14852)", None, None, None, "Ley 35/2006, art. 20"),
            (2025, "scale", 17673.52, 19747.50, None, "2364.34 - 1.14 * (net_income - 17673.52)", None, None, None, "Ley 35/2006, art. 20"),
            (2025, "scale", None, 19747.50, None, None, 0, None, None, "Ley 35/2006, art. 20"),
            (2025, "new_deduction", None, None, None, None, 340, 16576, None, "Ley 5/2025, de 24 de julio. DA 61.a LIRPF"),
        ]

        for row in work_reductions:
            cur.execute(
                """INSERT INTO irpf_work_income_reduction (year, rule_type, net_income_up_to, net_income_from,
                   reduction, reduction_formula, other_income_max, phase_out_limit, phase_out_formula, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (year, rule_type) DO UPDATE SET
                       reduction = EXCLUDED.reduction,
                       reduction_formula = EXCLUDED.reduction_formula,
                       source = EXCLUDED.source""",
                row,
            )

        conn.commit()
        total = len(general_brackets) + len(savings_brackets) + len(personal_minimums) + len(work_reductions)
        print(f"OK: {total} registros IRPF 2025 insertados (tramos, minimos, reducciones)")
    except Exception as e:
        conn.rollback()
        print(f"SKIP: irpf_brackets tables not found — {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
