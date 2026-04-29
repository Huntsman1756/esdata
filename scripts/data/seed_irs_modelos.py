"""Seed data para modelos IRS (Internal Revenue Service)."""

import os

import psycopg

MODELOS = [
    ("1040", "Individual Income Tax Return", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1040"),
    ("1120", "Corporate Income Tax Return", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1120"),
    ("1065", "U.S. Return of Partnership Income", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1065"),
    ("941", "Quarterly Federal Tax Return", "trimestral", "Payroll Tax", "https://www.irs.gov/forms-pubs/about-form-941"),
    ("940", "Annual Federal Unemployment Tax Return", "anual", "Payroll Tax", "https://www.irs.gov/forms-pubs/about-form-940"),
    ("1099-NEC", "Nonemployee Compensation", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1099-nec"),
    ("1099-MISC", "Miscellaneous Income", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1099-misc"),
    ("1099-DIV", "Dividends and Distributions", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1099-div"),
    ("1099-INT", "Interest Income", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-1099-int"),
    ("700", "Exempt Organization Return", "anual", "Income Tax", "https://www.irs.gov/forms-pubs/about-form-700"),
]


def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for codigo, nombre, periodo, impuesto, url_info in MODELOS:
                cur.execute(
                    """INSERT INTO irs_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                       VALUES (%s, %s, %s, %s, %s, true)
                       ON CONFLICT (codigo) DO UPDATE SET
                           nombre = EXCLUDED.nombre,
                           periodo = EXCLUDED.periodo,
                           impuesto = EXCLUDED.impuesto,
                           url_info = EXCLUDED.url_info,
                           activo = EXCLUDED.activo""",
                    (codigo, nombre, periodo, impuesto, url_info),
                )
            print(f"Seeded {len(MODELOS)} IRS models")


if __name__ == "__main__":
    main()
