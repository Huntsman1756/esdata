"""LEGACY / NO AUTORITATIVO.

Legacy seed for `modelo_articulo` mappings.

No usar como flujo canonico productivo AEAT. Esta ruta se mantiene solo como
compatibilidad temporal hasta endurecer `modelo_articulo` en Fase 3.2.

Precondiciones: `aeat_modelo`, `norma` y `articulo` deben existir previamente
en la base de datos. Este script realiza escrituras reales sobre `modelo_articulo`.
"""

import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

MAPPINGS = [
    (
        "100",
        "LIRPF",
        "2",
        None,
        "Hecho imponible del IRPF",
        "Instrucciones Modelo 100 2025 — Apartado Características",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "100",
        "LIRPF",
        "17",
        "0002",
        "Rendimientos del trabajo",
        "Instrucciones Modelo 100 2025 — Casilla 0002",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "303",
        "LIVA",
        "4",
        None,
        "Hecho imponible IVA",
        "Instrucciones Modelo 303 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),
    (
        "390",
        "LIVA",
        "111",
        None,
        "Resumen anual IVA",
        "Instrucciones Modelo 390 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-390/instrucciones/index.shtml",
    ),
    (
        "124",
        "IRNR",
        "14",
        None,
        "Rentas obtenidas sin establecimiento permanente — renta regular",
        "Instrucciones Modelo 124 2025",
        "https://sede.agenciatributaria.gob.es/Sede/irpf/retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/modelo-124.html",
    ),
    (
        "216",
        "IRNR",
        "25",
        None,
        "Retenciones capital mobiliario sin EP",
        "Instrucciones Modelo 216 2025",
        "https://sede.agenciatributaria.gob.es/Sede/no-residentes/irnr-sin-establecimiento-permanente/retenciones-irnr-sin-establecimiento-permanente/modelos-declaraciones-retenciones.html",
    ),
    (
        "111",
        "LIRPF",
        "99",
        None,
        "Obligación de retener",
        "Instrucciones Modelo 111 2025",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-111/instrucciones/index.shtml",
    ),
]


def seed():
    import psycopg

    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()
    upserted = 0
    skipped = 0

    for m in MAPPINGS:
        modelo_codigo, norma, numero, casilla, nota, fuente, url_fuente = m

        cur.execute("SELECT id FROM aeat_modelo WHERE codigo = %s", (modelo_codigo,))
        modelo_row = cur.fetchone()
        if not modelo_row:
            print(f"SKIP: modelo {modelo_codigo} not found")
            skipped += 1
            continue

        cur.execute(
            """
            SELECT a.id
            FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE n.codigo = %s AND a.numero = %s
            """,
            (norma, numero),
        )
        articulo_row = cur.fetchone()
        if not articulo_row:
            print(f"SKIP: {norma} art. {numero} not found")
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO modelo_articulo (
                modelo_id,
                articulo_id,
                norma,
                numero,
                casilla,
                nota,
                fuente,
                url_fuente,
                metodo_enlace,
                confianza_enlace
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'manual_official', 1.0)
            ON CONFLICT (modelo_id, articulo_id) DO UPDATE SET
                norma = EXCLUDED.norma,
                numero = EXCLUDED.numero,
                casilla = EXCLUDED.casilla,
                nota = EXCLUDED.nota,
                fuente = EXCLUDED.fuente,
                url_fuente = EXCLUDED.url_fuente,
                metodo_enlace = EXCLUDED.metodo_enlace,
                confianza_enlace = EXCLUDED.confianza_enlace
            """,
            (
                modelo_row[0],
                articulo_row[0],
                norma,
                numero,
                casilla,
                nota,
                fuente,
                url_fuente,
            ),
        )
        upserted += 1

    conn.commit()
    print(f"Seeded {upserted} modelo_articulo mappings ({skipped} skipped)")
    conn.close()


if __name__ == "__main__":
    seed()
