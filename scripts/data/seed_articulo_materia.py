#!/usr/bin/env python3
"""Seed articulo_materia — Vinculos entre articulos y materias regulatorias.

Crea las relaciones articulo↔materia basadas en el contenido de cada articulo.

Uso:
    python scripts/data/seed_articulo_materia.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

MATERIA_MAP = {
    ("LIRNR", "111"): {"materia_id": 8, "relevancia": 1},
    ("LIRNR", "129"): {"materia_id": 8, "relevancia": 1},
    ("LIRNR", "124"): {"materia_id": 9, "relevancia": 1},
    ("LIRNR", "125"): {"materia_id": 9, "relevancia": 1},
    ("LIRNR", "44"): {"materia_id": 15, "relevancia": 1},
    ("LIRNR", "50"): {"materia_id": 15, "relevancia": 1},
    ("LIRNR", "55"): {"materia_id": 15, "relevancia": 1},
    ("LIRNR", "29"): {"materia_id": 15, "relevancia": 1},
    ("LIRNR", "3"): {"materia_id": 1, "relevancia": 2},
    ("LIRNR", "4"): {"materia_id": 1, "relevancia": 2},
    ("LIRNR", "5"): {"materia_id": 1, "relevancia": 2},
    ("LIRNR", "2"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "7"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "8"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "9"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "10"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "11"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "12"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "14"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "15"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "162"): {"materia_id": 17, "relevancia": 1},
    ("LIRNR", "216"): {"materia_id": 15, "relevancia": 1},
    ("LIRNR", "296"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "44"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "65"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "78"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "79"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "9"): {"materia_id": 9, "relevancia": 1},
    ("LIRPF", "100"): {"materia_id": 11, "relevancia": 1},
    ("LIRPF", "190"): {"materia_id": 11, "relevancia": 1},
    ("LIRPF", "95"): {"materia_id": 12, "relevancia": 1},
    ("LIRPF", "1"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "32"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "33"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "35"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "55"): {"materia_id": 15, "relevancia": 1},
    ("LIRPF", "124"): {"materia_id": 9, "relevancia": 1},
    ("LIRPF", "125"): {"materia_id": 9, "relevancia": 1},
    ("LIRPF", "163"): {"materia_id": 14, "relevancia": 1},
    ("LIRPF", "163 bis"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 ter"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 sex"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 quater"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 quinques"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 sept"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 oct"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 duodec"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 non"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "163 undec"): {"materia_id": 1, "relevancia": 2},
    ("LIRPF", "206"): {"materia_id": 10, "relevancia": 1},
    ("LIRPF", "206bis"): {"materia_id": 10, "relevancia": 1},
    ("LIS", "2"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "3"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "4"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "5"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "6"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "7"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "8"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "9"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "11"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "43"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "44"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "59"): {"materia_id": 16, "relevancia": 1},
    ("LIS", "200"): {"materia_id": 16, "relevancia": 1},
    ("LIVA", "1"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "14"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "15"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "16"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "17"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "18"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "19"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "20"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "69"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "70"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "71"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "72"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "73"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "74"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "75"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "76"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "77"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "78"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "79"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "80"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "81"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "82"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "83"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "84"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "85"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "86"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "87"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "88"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "89"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "90"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "91"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "105"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "123"): {"materia_id": 9, "relevancia": 1},
    ("LIVA", "124"): {"materia_id": 9, "relevancia": 1},
    ("LIVA", "125"): {"materia_id": 9, "relevancia": 1},
    ("LIVA", "162"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "163"): {"materia_id": 14, "relevancia": 1},
    ("LIVA", "163 bis"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 ter"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 sex"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 quater"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 quinques"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 sept"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 oct"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 duodec"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 non"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "163 undec"): {"materia_id": 1, "relevancia": 2},
    ("LIVA", "172"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "173"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "174"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "175"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "176"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "177"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "178"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "179"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "180"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "181"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "182"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "183"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "184"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "185"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "186"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "187"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "194"): {"materia_id": 7, "relevancia": 1},
    ("LIVA", "206"): {"materia_id": 10, "relevancia": 1},
    ("LIVA", "206bis"): {"materia_id": 10, "relevancia": 1},
    ("LGT", "2"): {"materia_id": 8, "relevancia": 1},
    ("LGT", "28"): {"materia_id": 15, "relevancia": 1},
    ("LGT", "29"): {"materia_id": 15, "relevancia": 1},
    ("LGT", "35"): {"materia_id": 15, "relevancia": 1},
    ("LGT", "56"): {"materia_id": 15, "relevancia": 1},
    ("LGT", "66"): {"materia_id": 15, "relevancia": 1},
    ("LGT", "109"): {"materia_id": 16, "relevancia": 1},
    ("LGT", "111"): {"materia_id": 16, "relevancia": 1},
    ("LGT", "129"): {"materia_id": 16, "relevancia": 1},
    ("LGT", "162"): {"materia_id": 16, "relevancia": 1},
    ("LGT", "194"): {"materia_id": 16, "relevancia": 1},
    ("DAC6", "206"): {"materia_id": 10, "relevancia": 1},
    ("DAC6", "206bis"): {"materia_id": 10, "relevancia": 1},
    ("DAC6EU", "1"): {"materia_id": 10, "relevancia": 1},
    ("DAC6RD", "1"): {"materia_id": 10, "relevancia": 1},
    ("CNMV", "1"): {"materia_id": 16, "relevancia": 1},
    ("CNMV", "15"): {"materia_id": 16, "relevancia": 1},
    ("HL", "1"): {"materia_id": 17, "relevancia": 1},
    ("IIEE", "1"): {"materia_id": 16, "relevancia": 1},
    ("ITPAJD", "1"): {"materia_id": 11, "relevancia": 1},
    ("ITPAJD", "31"): {"materia_id": 11, "relevancia": 1},
}


def main():
    parser = argparse.ArgumentParser(description="Seed articulo_materia")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    # Build articulo lookup: (norma_slug, numero) -> id
    cur.execute("SELECT id, norma_id, numero FROM articulo")
    articulo_ids = {}
    for art_id, norma_id, numero in cur.fetchall():
        cur.execute("SELECT codigo FROM norma WHERE id = %s", (norma_id,))
        norma_slug = cur.fetchone()[0]
        articulo_ids[(norma_slug, numero)] = art_id

    # Build materia lookup: slug -> id
    cur.execute("SELECT id, slug FROM materia")
    materia_ids = {slug: mid for mid, slug in cur.fetchall()}

    # Insert mappings
    count = 0
    for (norma_slug, numero), mapping in MATERIA_MAP.items():
        key = (norma_slug, numero)
        if key not in articulo_ids:
            continue
        articulo_id = articulo_ids[key]
        cur.execute(
            """INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
               VALUES (%s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (articulo_id, mapping["materia_id"], mapping["relevancia"]),
        )
        count += 1

    conn.commit()
    print(f"OK: {count} articulo_materia mappings inserted")
    conn.close()


if __name__ == "__main__":
    main()
