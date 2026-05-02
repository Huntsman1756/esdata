#!/usr/bin/env python3
"""Seed AEAT tax models into aeat_modelo table.

Idempotent: ON CONFLICT (codigo) DO NOTHING.
Run with: python scripts/ops/seed_aeat_modelos.py

Preconditions:
  - DATABASE_URL env var or defaults to postgresql+psycopg://esdata:change-me@postgres:5432/esdata
  - aeat_modelo table must exist (migration already ran)

AEAT URL structure changed in 2026 — old /Sede/modelos/XXX-YYYY.html no longer work.
New structure organizes by tax type: /Sede/irpf.html, /Sede/iva.html, etc.
"""

import os
import sys

from sqlalchemy import create_engine, text

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://esdata:change-me@postgres:5432/esdata",
)

# (codigo, nombre, periodo, impuesto, url_info)
# URL structure changed in 2026 — AEAT now organizes by tax category
MODELOS = [
    (
        "100", "IRPF — Declaración trimestral", "Trimestral", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf.html",
    ),
    (
        "111", "Retenciones trabajo", "Mensual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf.html",
    ),
    (
        "115", "Retenciones alquiler", "Mensual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf.html",
    ),
    (
        "130", "IRPF — Estimación directa", "Anual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf.html",
    ),
    (
        "180", "Resumen retenciones alquiler", "Anual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf.html",
    ),
    (
        "190", "Resumen retenciones trabajo", "Anual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf.html",
    ),
    (
        "198", "IRPF Operaciones con activos financieros", "Anual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-198.html",
    ),
    (
        "200", "Impuesto Sociedades anual", "Anual", "IS",
        "https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades.html",
    ),
    (
        "202", "IS — Pagos fraccionados", "Trimestral", "IS",
        "https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades.html",
    ),
    (
        "216", "IRNR retenciones", "Trimestral", "IRNR",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes.html",
    ),
    (
        "303", "IVA trimestral", "Trimestral", "IVA",
        "https://sede.agenciatributaria.gob.es/Sede/iva.html",
    ),
    (
        "349", "Operaciones intracomunitarias", "Mensual", "IVA",
        "https://sede.agenciatributaria.gob.es/Sede/iva.html",
    ),
    (
        "390", "IVA resumen anual", "Anual", "IVA",
        "https://sede.agenciatributaria.gob.es/Sede/iva.html",
    ),
    (
        "720", "Bienes en extranjero", "Anual", "IRPF",
        "https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas-otros-impuestos-tasas.html",
    ),
]


def main():
    engine = create_engine(DB_URL, future=True)
    inserted = 0
    skipped = 0

    with engine.begin() as conn:
        for codigo, nombre, periodo, impuesto, url_info in MODELOS:
            result = conn.execute(
                text(
                    "INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info) "
                    "VALUES (:codigo, :nombre, :periodo, :impuesto, :url_info) "
                    "ON CONFLICT (codigo) DO UPDATE SET "
                    "nombre = EXCLUDED.nombre, "
                    "periodo = EXCLUDED.periodo, "
                    "impuesto = EXCLUDED.impuesto, "
                    "url_info = EXCLUDED.url_info"
                ),
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "periodo": periodo,
                    "impuesto": impuesto,
                    "url_info": url_info,
                },
            )
            if result.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

    print(f"Seed aeat_modelo: {inserted} inserted, {skipped} skipped (total {len(MODELOS)})")

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT codigo, nombre, url_info FROM aeat_modelo ORDER BY codigo")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1][:40]} | {row[2][:60] if row[2] else 'NO URL'}")


if __name__ == "__main__":
    main()
