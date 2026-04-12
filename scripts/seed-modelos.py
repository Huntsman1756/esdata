#!/usr/bin/env python
"""
Seed initial AEAT model-article relationships for esdata.

Populates:
- aeat_modelo: top 6 models with metadata
- modelo_articulo: verified relationships with official source

Usage:
    python scripts/seed-modelos.py [--db-url URL] [--dry-run]

Each relationship in MODELO_ARTICULO_DATA must include:
- fuente: official source document name
- url_fuente: URL to the official document

If you cannot verify a relationship with an official source,
do NOT add it here.
"""

import os
import sys
import argparse
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Model metadata — verifiable from AEAT sede pages
# ---------------------------------------------------------------------------
MODELOS = [
    {
        "codigo": "100",
        "nombre": "IRPF Declaración anual",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/index.shtml",
    },
    {
        "codigo": "111",
        "nombre": "IRPF Retenciones e ingresos a cuenta",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/index.shtml",
    },
    {
        "codigo": "115",
        "nombre": "IRPF Retenciones arrendamientos",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/index.shtml",
    },
    {
        "codigo": "130",
        "nombre": "IRPF Pago fraccionado",
        "periodo": "trimestral",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/index.shtml",
    },
    {
        "codigo": "303",
        "nombre": "IVA Autoliquidación",
        "periodo": "trimestral",
        "impuesto": "IVA",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/index.shtml",
    },
    {
        "codigo": "190",
        "nombre": "IRPF Retenciones — rendimientos trabajo y actividades",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-190.html",
    },
    {
        "codigo": "196",
        "nombre": "IRPF Resumen anual retenciones capital mobiliario",
        "periodo": "anual",
        "impuesto": "IRPF",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-196.html",
    },
    {
        "codigo": "390",
        "nombre": "IVA Resumen anual",
        "periodo": "anual",
        "impuesto": "IVA",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/index.shtml",
    },
]

# ---------------------------------------------------------------------------
# Model-article relationships — ONLY with verified official sources.
#
# Format: (modelo_codigo, articulo_norma, articulo_numero, casilla, nota, fuente, url_fuente)
#
# CRITERION: Do NOT add a relationship unless you can point to an official
# AEAT instruction document or BOE norm that explicitly links the model/casilla
# to the specific article.
# ---------------------------------------------------------------------------
MODELO_ARTICULO_DATA = [
    # ------------------------------------------------------------------
    # Modelo 100 — IRPF Declaración anual
    # Fuente: Instrucciones Modelo 100 (PDF AEAT) — mapeo casillas a tipos de rendimiento
    # ------------------------------------------------------------------
    (
        "100", "LIRPF", "2",
        None, "Hecho imponible del IRPF",
        "Instrucciones Modelo 100 2025 — Apartado Características",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "17",
        "0002", "Rendimientos del trabajo",
        "Instrucciones Modelo 100 2025 — Casilla 0002",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "18",
        "0002", "Rendimientos del trabajo en especie",
        "Instrucciones Modelo 100 2025 — Casilla 0002",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "19",
        "0003", "Rendimientos de actividades económicas",
        "Instrucciones Modelo 100 2025 — Casilla 0003",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "22",
        "0004", "Rendimientos del capital mobiliario",
        "Instrucciones Modelo 100 2025 — Casilla 0004",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "24",
        "0005", "Rendimientos del capital inmobiliario",
        "Instrucciones Modelo 100 2025 — Casilla 0005",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "33",
        "0416", "Ganancias patrimoniales",
        "Instrucciones Modelo 100 2025 — Casilla 0416",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100", "LIRPF", "88",
        None, "Base imponible del ahorro",
        "Instrucciones Modelo 100 2025 — Base del ahorro",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 111 — Retenciones IRPF
    # Fuente: Instrucciones Modelo 111 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "111", "LIRPF", "99",
        None, "Obligación de retener",
        "Instrucciones Modelo 111 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml",
    ),
    (
        "111", "LIRPF", "17",
        "01", "Retenciones rendimientos del trabajo",
        "Instrucciones Modelo 111 2025 — Casilla 01",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 115 — Retenciones arrendamientos
    # Fuente: Instrucciones Modelo 115 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "115", "LIRPF", "24",
        "01", "Retenciones rendimientos capital inmobiliario",
        "Instrucciones Modelo 115 2025 — Casilla 01",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-115/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 130 — Pago fraccionado IRPF (estimación objetiva)
    # Fuente: Instrucciones Modelo 130 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "130", "LIRPF", "19",
        None, "Pago fraccionado estimación objetiva",
        "Instrucciones Modelo 130 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-130/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 303 — IVA Autoliquidación
    # Fuente: Instrucciones Modelo 303 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "303", "LIVA", "4",
        None, "Hecho imponible IVA",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),
    (
        "303", "LIVA", "84",
        None, "Sujeción al IVA",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),
    (
        "303", "LIVA", "85",
        None, "Devengo del impuesto",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 390 — IVA Resumen anual
    # Fuente: Instrucciones Modelo 390 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "390", "LIVA", "111",
        None, "Resumen anual IVA",
        "Instrucciones Modelo 390 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 190 — IRPF Retenciones rendimientos trabajo y actividades
    # Fuente: Instrucciones Modelo 190 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "190", "LIRPF", "99",
        None, "Obligación de retener rendimientos trabajo",
        "Instrucciones Modelo 190 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-190/instrucciones/index.shtml",
    ),
    (
        "190", "LIRPF", "100",
        None, "Ingresos a cuenta",
        "Instrucciones Modelo 190 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-190/instrucciones/index.shtml",
    ),
    (
        "190", "LIRPF", "101",
        None, "Retenciones actividades económicas",
        "Instrucciones Modelo 190 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-190/instrucciones/index.shtml",
    ),

    # ------------------------------------------------------------------
    # Modelo 196 — IRPF Resumen anual retenciones capital mobiliario
    # Fuente: Instrucciones Modelo 196 (PDF AEAT)
    # ------------------------------------------------------------------
    (
        "196", "LIRPF", "22",
        None, "Retenciones rendimientos capital mobiliario",
        "Instrucciones Modelo 196 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-196/instrucciones/index.shtml",
    ),
    (
        "196", "LIRPF", "23",
        None, "Retenciones dividendos y participaciones",
        "Instrucciones Modelo 196 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-196/instrucciones/index.shtml",
    ),
    (
        "196", "LIRPF", "25",
        None, "Retenciones ganancias patrimoniales mobiliario",
        "Instrucciones Modelo 196 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-196/instrucciones/index.shtml",
    ),
]

# ---------------------------------------------------------------------------
# Modelos excluidos de Fase 1 (documentación para no perder contexto)
#
# 198: Declaración anual operaciones con activos financieros
#      Existe, pero relación con artículos LIRPF menos directa.
#      Aparcado hasta Fase 2.
#
# 289: Declaración informativa cuentas financieras asistencia mutua
#      Intercambio de información entre jurisdicciones, no encaja en
#      la vertical fiscal IRPF/IVA de esta fase.
#
# 290: No verificado como modelo independiente en la sede AEAT.
#      Aparcado hasta confirmar existencia y número exacto.
#
# 296: Retenciones IRNR (Impuesto Renta No Residentes)
#      Otro impuesto (IRNR), fuera de foco por ahora.
# ---------------------------------------------------------------------------


def get_db_url(args_db_url: str | None) -> str:
    if args_db_url:
        return args_db_url
    url = os.getenv("DATABASE_URL")
    if not url:
        url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        print("ERROR: No DATABASE_URL or DATABASE_PUBLIC_URL found.")
        print("Provide --db-url or set env vars.")
        sys.exit(1)
    return url


def connect(db_url: str):
    try:
        return psycopg2.connect(db_url)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        sys.exit(1)


def seed_modelos(conn, dry_run: bool = False):
    with conn.cursor() as cur:
        # --- Insert models ---
        for m in MODELOS:
            if dry_run:
                print(f"[DRY-RUN] Would upsert modelo: {m['codigo']} — {m['nombre']}")
                continue

            cur.execute(
                """
                INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    periodo = EXCLUDED.periodo,
                    impuesto = EXCLUDED.impuesto,
                    url_info = EXCLUDED.url_info
                """,
                (m["codigo"], m["nombre"], m["periodo"], m["impuesto"], m["url_info"]),
            )

        conn.commit()

        if not dry_run:
            print(f"Upserted {len(MODELOS)} models.")

        # --- Insert model-article relationships ---
        inserted = 0
        skipped = 0
        for row in MODELO_ARTICULO_DATA:
            modelo_codigo, norma, numero, casilla, nota, fuente, url_fuente = row

            if not fuente or not fuente.strip():
                print(f"SKIP: {modelo_codigo} → {norma} art. {numero}: no fuente")
                skipped += 1
                continue

            if dry_run:
                print(
                    f"[DRY-RUN] Would insert: {modelo_codigo} → {norma} art. {numero} "
                    f"(casilla={casilla}, fuente={fuente})"
                )
                inserted += 1
                continue

            # Get modelo_id
            cur.execute("SELECT id FROM aeat_modelo WHERE codigo = %s", (modelo_codigo,))
            modelo_row = cur.fetchone()
            if not modelo_row:
                print(f"SKIP: modelo {modelo_codigo} not found in DB")
                skipped += 1
                continue
            modelo_id = modelo_row[0]

            # Get articulo_id
            cur.execute(
                """
                SELECT a.id FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = %s AND a.numero = %s
                """,
                (norma, numero),
            )
            art_row = cur.fetchone()
            if not art_row:
                print(f"SKIP: {norma} art. {numero} not found in DB")
                skipped += 1
                continue
            articulo_id = art_row[0]

            # Upsert relationship
            cur.execute(
                """
                INSERT INTO modelo_articulo (modelo_id, articulo_id, casilla, nota, fuente, url_fuente)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (modelo_id, articulo_id) DO UPDATE SET
                    casilla = EXCLUDED.casilla,
                    nota = EXCLUDED.nota,
                    fuente = EXCLUDED.fuente,
                    url_fuente = EXCLUDED.url_fuente
                """,
                (modelo_id, articulo_id, casilla, nota, fuente, url_fuente),
            )
            inserted += 1

        if not dry_run:
            conn.commit()

        print(f"\nRelationships: {inserted} inserted, {skipped} skipped.")


def main():
    parser = argparse.ArgumentParser(description="Seed AEAT models and relationships")
    parser.add_argument("--db-url", help="Database connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    db_url = get_db_url(args.db_url)
    print(f"Database: {db_url[:40]}...")
    print(f"Dry run: {args.dry_run}")

    conn = connect(db_url)
    try:
        seed_modelos(conn, dry_run=args.dry_run)
    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
