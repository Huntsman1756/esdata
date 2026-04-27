#!/usr/bin/env python
"""Seed tipos IVA 2025 — peninsular, Canarias (IGIC), Ceuta y Melilla (IPSI).

Fuente: Ley 37/1992 (LIVA) + Ley 20/1991 (IGIC) + Ley 8/1991 (IPSI)
verified_date: 2026-03-20
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    # Tipos IVA peninsular
    ivas = [
        (2025, "peninsular", "general", 21.00, None, "Ley 37/1992, art. 90"),
        (2025, "peninsular", "reducido", 10.00, "Alimentos no basicos, hosteleria, transporte, obras vivienda, productos sanitarios, aceites de semilla, pasta", "Ley 37/1992, art. 91.Uno"),
        (2025, "peninsular", "superreducido", 4.00, "Pan, leche, huevos, fruta, verdura, cereales, queso, aceite de oliva, libros, medicamentos, vivienda proteccion oficial, protesis, leches fermentadas", "Ley 37/1992, art. 91.Dos; RDL 4/2024 art. 2 (aceite oliva permanente)"),
    ]

    for row in ivas:
        cur.execute(
            """INSERT INTO iva_rates (year, territory, rate_type, rate, applies_to, source)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (year, territory, rate_type) DO UPDATE SET
                   rate = EXCLUDED.rate, applies_to = EXCLUDED.applies_to, source = EXCLUDED.source""",
            row,
        )

    # Recargos IVA peninsular
    surcharges = [
        (2025, 21.00, None, 5.20, "Ley 37/1992, art. 161.Dos"),
        (2025, 10.00, None, 1.40, "Ley 37/1992, art. 161.Dos"),
        (2025, 4.00, None, 0.50, "Ley 37/1992, art. 161.Dos"),
        (2025, None, "tabaco", 1.75, "Ley 37/1992, art. 161.Cinco"),
    ]

    for row in surcharges:
        cur.execute(
            """INSERT INTO iva_surcharges (year, vat_rate, vat_rate_label, surcharge_rate, source)
               VALUES (%s, %s, %s, %s, %s)""",
            row,
        )

    # Exenciones IVA
    exemptions = [
        (2025, "Servicios medicos y sanitarios", "Ley 37/1992, art. 20.Uno.3"),
        (2025, "Ensenanza", "Ley 37/1992, art. 20.Uno.9"),
        (2025, "Operaciones de seguro", "Ley 37/1992, art. 20.Uno.16"),
        (2025, "Servicios financieros", "Ley 37/1992, art. 20.Uno.18"),
        (2025, "Arrendamiento de vivienda", "Ley 37/1992, art. 20.Uno.23"),
    ]

    for row in exemptions:
        cur.execute(
            """INSERT INTO iva_exemptions (year, category, source)
               VALUES (%s, %s, %s)
               ON CONFLICT (year, category) DO UPDATE SET source = EXCLUDED.source""",
            row,
        )

    # IGIC Canarias
    igic = [
        (2025, "canarias", "general", 7.00, None, "Ley 20/1991"),
        (2025, "canarias", "reducido", 3.00, None, "Ley 20/1991"),
        (2025, "canarias", "cero", 0.00, None, "Ley 20/1991"),
        (2025, "canarias", "incrementado", 9.50, None, "Ley 20/1991"),
        (2025, "canarias", "especial_incrementado", 15.00, None, "Ley 20/1991"),
    ]

    for row in igic:
        cur.execute(
            """INSERT INTO iva_rates (year, territory, rate_type, rate, source)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (year, territory, rate_type) DO UPDATE SET rate = EXCLUDED.rate""",
            row,
        )

    # IPSI Ceuta y Melilla
    cur.execute(
        """INSERT INTO iva_rates (year, territory, rate_type, rate, applies_to, source)
           VALUES (2025, 'ceuta_melilla', 'rango', 0.5, 'Rango 0.5% - 10%', 'Ley 8/1991')
           ON CONFLICT (year, territory, rate_type) DO UPDATE SET applies_to = EXCLUDED.applies_to""",
    )

    conn.commit()
    total = len(ivas) + len(surcharges) + len(exemptions) + len(igic) + 1
    print(f"OK: {total} registros de tipos IVA/IGIC/IPSI insertados")
    conn.close()


if __name__ == "__main__":
    main()
