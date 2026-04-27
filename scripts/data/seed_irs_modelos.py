"""Seed data para modelos IRS (Internal Revenue Service).

Cubre 10 modelos principales:
- 1040: Individual Income Tax Return
- 1120: Corporate Income Tax Return
- 1065: Partnership Return
- 941: Quarterly Federal Tax Return
- 940: Annual Federal Unemployment Tax Return
- 1099-NEC: Nonemployee Compensation
- 1099-MISC: Miscellaneous Income
- 1099-DIV: Dividends and Distributions
- 1099-INT: Interest Income
- 700: Exempt Organization
"""

from datetime import date

MODELOS = [
    {
        "codigo": "1040",
        "nombre": "Individual Income Tax Return",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1040",
        "activo": True,
    },
    {
        "codigo": "1120",
        "nombre": "Corporate Income Tax Return",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1120",
        "activo": True,
    },
    {
        "codigo": "1065",
        "nombre": "U.S. Return of Partnership Income",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1065",
        "activo": True,
    },
    {
        "codigo": "941",
        "nombre": "Quarterly Federal Tax Return",
        "periodo": "trimestral",
        "impuesto": "Payroll Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-941",
        "activo": True,
    },
    {
        "codigo": "940",
        "nombre": "Annual Federal Unemployment Tax Return",
        "periodo": "anual",
        "impuesto": "Payroll Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-940",
        "activo": True,
    },
    {
        "codigo": "1099-NEC",
        "nombre": "Nonemployee Compensation",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1099-nec",
        "activo": True,
    },
    {
        "codigo": "1099-MISC",
        "nombre": "Miscellaneous Income",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1099-misc",
        "activo": True,
    },
    {
        "codigo": "1099-DIV",
        "nombre": "Dividends and Distributions",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1099-div",
        "activo": True,
    },
    {
        "codigo": "1099-INT",
        "nombre": "Interest Income",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-1099-int",
        "activo": True,
    },
    {
        "codigo": "700",
        "nombre": "Exempt Organization Return",
        "periodo": "anual",
        "impuesto": "Income Tax",
        "url_info": "https://www.irs.gov/forms-pubs/about-form-700",
        "activo": True,
    },
]


def seed_irs_models():
    """Inserta modelos IRS en irs_modelo."""
    from pathlib import Path

    from sqlalchemy import create_engine, text

    db_url = (
        Path(__file__).resolve().parents[2]
        / ".env"
    )
    try:
        import dotenv
        dotenv.load_dotenv(db_url)
    except ImportError:
        pass

    db_url = Path(__file__).resolve().parents[3] / ".env"
    import os

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/esdata",
    )

    engine = create_engine(db_url)

    with engine.begin() as conn:
        for modelo in MODELOS:
            conn.execute(
                text(
                    """
                    INSERT INTO irs_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                    VALUES (:codigo, :nombre, :periodo, :impuesto, :url_info, :activo)
                    ON CONFLICT (codigo) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        periodo = COALESCE(EXCLUDED.periodo, irs_modelo.periodo),
                        impuesto = COALESCE(EXCLUDED.impuesto, irs_modelo.impuesto),
                        url_info = EXCLUDED.url_info,
                        activo = EXCLUDED.activo,
                        actualizado_en = now()
                    """
                ),
                modelo,
            )

    print(f"Seeded {len(MODELOS)} IRS models")


if __name__ == "__main__":
    seed_irs_models()
