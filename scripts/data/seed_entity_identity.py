#!/usr/bin/env python3
"""Seed entity identities — LEI identifiers via GLEIF.

Crea identidades de entidad (LEI, nombre legal, pais, estado) para empresas
de ejemplo. Basado en el worker entity_identity.py.

Uso:
    python scripts/data/seed_entity_identity.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

ENTITY_IDENTIFIERS = [
    {
        "empresa_id": 1,
        "lei": "5493001KJTIIGC8Y1R12",
        "nombre_legal": "IBERBANK, S.A.",
        "pais": "ES",
        "estado": "active",
        "vigencia_desde": "2013-01-01",
        "vigencia_hasta": None,
        "fuente_ref": "GLEIF:5493001KJTIIGC8Y1R12",
    },
    {
        "empresa_id": 2,
        "lei": "549300P28J1BQ8D0CF94",
        "nombre_legal": "BANCO SANTANDER, S.A.",
        "pais": "ES",
        "estado": "active",
        "vigencia_desde": "2013-06-01",
        "vigencia_hasta": None,
        "fuente_ref": "GLEIF:549300P28J1BQ8D0CF94",
    },
    {
        "empresa_id": 3,
        "lei": "549300ARDE00000005",
        "nombre_legal": "BBVA, BANCO BILBAO VIZCAYA ARGENTARIA, S.A.",
        "pais": "ES",
        "estado": "active",
        "vigencia_desde": "2014-01-01",
        "vigencia_hasta": None,
        "fuente_ref": "GLEIF:549300ARDE00000005",
    },
    {
        "empresa_id": 4,
        "lei": "969500D3Y43K7W001H94",
        "nombre_legal": "TELEFONICA, S.A.",
        "pais": "ES",
        "estado": "active",
        "vigencia_desde": "2015-03-01",
        "vigencia_hasta": None,
        "fuente_ref": "GLEIF:969500D3Y43K7W001H94",
    },
    {
        "empresa_id": 5,
        "lei": "959800F44Y3LX54D8007",
        "nombre_legal": "INDUSTRIAS TECNOLOGICAS, S.A.",
        "pais": "ES",
        "estado": "active",
        "vigencia_desde": "2018-07-01",
        "vigencia_hasta": None,
        "fuente_ref": "GLEIF:959800F44Y3LX54D8007",
    },
]

ENTITY_ALIASES = [
    {"empresa_id": 1, "alias": "Iberbank", "fuente": "GLEIF", "confianza": 0.7},
    {"empresa_id": 1, "alias": "Banco Iberbank", "fuente": "GLEIF", "confianza": 0.6},
    {"empresa_id": 2, "alias": "Santander", "fuente": "GLEIF", "confianza": 0.7},
    {"empresa_id": 2, "alias": "Banco Santander", "fuente": "GLEIF", "confianza": 0.8},
    {"empresa_id": 3, "alias": "BBVA", "fuente": "GLEIF", "confianza": 0.9},
    {"empresa_id": 3, "alias": "Banco Bilbao Vizcaya Argentaria", "fuente": "GLEIF", "confianza": 0.7},
    {"empresa_id": 4, "alias": "Telefonica", "fuente": "GLEIF", "confianza": 0.9},
    {"empresa_id": 4, "alias": "Telefonica SA", "fuente": "GLEIF", "confianza": 0.8},
    {"empresa_id": 5, "alias": "INDTEC", "fuente": "GLEIF", "confianza": 0.6},
    {"empresa_id": 5, "alias": "Industrias Tecnologicas", "fuente": "GLEIF", "confianza": 0.8},
]


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    import re
    name = name.lower().strip()
    name = re.sub(r"[ááàâä]", "a", name)
    name = re.sub(r"[éèêë]", "e", name)
    name = re.sub(r"[íìîï]", "i", name)
    name = re.sub(r"[óòôö]", "o", name)
    name = re.sub(r"[úùûü]", "u", name)
    name = re.sub(r"[ñ]", "n", name)
    name = re.sub(r"[¡¿!@#$%^&*()\-_=+\[\]{}|;:,.<>?/\\~`]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def main():
    parser = argparse.ArgumentParser(description="Seed entity identities (LEI)")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    for entity in ENTITY_IDENTIFIERS:
        cur.execute(
            """INSERT INTO entity_identifiers (empresa_id, lei, nombre_legal, pais,
               estado, vigencia_desde, vigencia_hasta, fuente_ref)
               VALUES (%(empresa_id)s, %(lei)s, %(nombre_legal)s, %(pais)s, %(estado)s,
                       %(vigencia_desde)s, %(vigencia_hasta)s, %(fuente_ref)s)
               ON CONFLICT (empresa_id, lei) DO UPDATE SET
                   nombre_legal = EXCLUDED.nombre_legal,
                   pais = EXCLUDED.pais,
                   estado = EXCLUDED.estado,
                   vigencia_desde = EXCLUDED.vigencia_desde,
                   vigencia_hasta = EXCLUDED.vigencia_hasta,
                   fuente_ref = EXCLUDED.fuente_ref,
                   created_at = now()""",
            entity,
        )

    for alias in ENTITY_ALIASES:
        normalized = _normalize_name(alias["alias"])
        cur.execute(
            """INSERT INTO entity_aliases (empresa_id, alias, alias_normalizado, fuente, confianza)
               VALUES (%(empresa_id)s, %(alias)s, %(alias_normalizado)s, %(fuente)s, %(confianza)s)
               ON CONFLICT DO NOTHING""",
            {
                **alias,
                "alias_normalizado": normalized,
            },
        )

    conn.commit()
    total = len(ENTITY_IDENTIFIERS) + len(ENTITY_ALIASES)
    print(f"OK: {total} registros de identidad insertados ({len(ENTITY_IDENTIFIERS)} entities, {len(ENTITY_ALIASES)} aliases)")
    conn.close()


if __name__ == "__main__":
    main()
