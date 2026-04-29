#!/usr/bin/env python3
"""Seed documento_articulo — Vinculos entre documentos y articulos legales.

Uso:
    python scripts/data/seed_documento_articulo.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

LINKS = [
    {"documento_id": 1, "articulo_index": 0, "metodo_enlace": "exact_match", "confianza_enlace": 0.95, "nota": "Articulo directo de la LISR"},
    {"documento_id": 1, "articulo_index": 1, "metodo_enlace": "semantic_match", "confianza_enlace": 0.82, "nota": "Interpretacion basada en contexto"},
    {"documento_id": 2, "articulo_index": 2, "metodo_enlace": "exact_match", "confianza_enlace": 0.98, "nota": "Copia literal del articulo"},
    {"documento_id": 2, "articulo_index": 3, "metodo_enlace": "partial_match", "confianza_enlace": 0.70, "nota": "Parcialmente aplicable"},
    {"documento_id": 3, "articulo_index": 4, "metodo_enlace": "exact_match", "confianza_enlace": 0.90, "nota": "Referencia explicita en texto"},
    {"documento_id": 3, "articulo_index": 5, "metodo_enlace": "semantic_match", "confianza_enlace": 0.75, "nota": "Vinculo inferido por semantica"},
    {"documento_id": 4, "articulo_index": 6, "metodo_enlace": "exact_match", "confianza_enlace": 0.99, "nota": "Texto identico al articulo original"},
    {"documento_id": 4, "articulo_index": 7, "metodo_enlace": "partial_match", "confianza_enlace": 0.65, "nota": "Solo secciones aplicables"},
    {"documento_id": 5, "articulo_index": 8, "metodo_enlace": "semantic_match", "confianza_enlace": 0.80, "nota": "Interpretacion doctrinal"},
    {"documento_id": 5, "articulo_index": 9, "metodo_enlace": "exact_match", "confianza_enlace": 0.97, "nota": "Transcripcion directa"},
    {"documento_id": 6, "articulo_index": 10, "metodo_enlace": "exact_match", "confianza_enlace": 0.93, "nota": "Vinculo verificado manualmente"},
    {"documento_id": 6, "articulo_index": 11, "metodo_enlace": "semantic_match", "confianza_enlace": 0.72, "nota": "Relacion contextual"},
    {"documento_id": 12, "articulo_index": 12, "metodo_enlace": "exact_match", "confianza_enlace": 0.96, "nota": "Copia fiel del articulo normativo"},
    {"documento_id": 12, "articulo_index": 13, "metodo_enlace": "partial_match", "confianza_enlace": 0.68, "nota": "Fragmento aplicable seleccionado"},
    {"documento_id": 13, "articulo_index": 14, "metodo_enlace": "semantic_match", "confianza_enlace": 0.85, "nota": "Interpretacion basada en jurisprudencia"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed documento_articulo")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    cur.execute("SELECT id FROM articulo ORDER BY id")
    articulo_ids = [row[0] for row in cur.fetchall()]

    count = 0
    for d in LINKS:
        articulo_idx = d.pop("articulo_index")
        if articulo_idx >= len(articulo_ids):
            continue
        articulo_id = articulo_ids[articulo_idx]
        cur.execute(
            """INSERT INTO documento_articulo (documento_id, articulo_id,
               metodo_enlace, confianza_enlace, nota)
               VALUES (%(documento_id)s, %(articulo_id)s, %(metodo_enlace)s,
                       %(confianza_enlace)s, %(nota)s)
               ON CONFLICT DO NOTHING""",
            {
                "documento_id": d["documento_id"],
                "articulo_id": articulo_id,
                "metodo_enlace": d["metodo_enlace"],
                "confianza_enlace": d["confianza_enlace"],
                "nota": d["nota"],
            },
        )
        count += 1

    conn.commit()
    print(f"OK: {count} documento_articulo records inserted")
    conn.close()


if __name__ == "__main__":
    main()
