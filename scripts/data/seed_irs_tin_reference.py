#!/usr/bin/env python3
"""Seed irs_tin_reference — Referencias de TIN (Taxpayer Identification Number) por pais.

Uso:
    python scripts/data/seed_irs_tin_reference.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

TIN_REFERENCES = [
    {
        "codigo_pais": "ES",
        "pais_nombre": "Espana",
        "formato_tin": "^[A-Z]\\d{8}$|^\\d{8}[A-Z]$|^[A-Z]\\d{7}[A-Z]$",
        "ejemplo_tin": "B12345678",
        "emisor_espana": "true",
        "emisor_pais": "false",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "US",
        "pais_nombre": "Estados Unidos",
        "formato_tin": "^\\d{2}-\\d{7}$|^\\d{9}$",
        "ejemplo_tin": "12-3456789",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": False,
    },
    {
        "codigo_pais": "FR",
        "pais_nombre": "Francia",
        "formato_tin": "^\\d{11}$",
        "ejemplo_tin": "12345678901",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "DE",
        "pais_nombre": "Alemania",
        "formato_tin": "^\\d{9}$|^\\d{11}$",
        "ejemplo_tin": "12345678901",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "GB",
        "pais_nombre": "Reino Unido",
        "formato_tin": "^\\d{9}$|^\\d{12}$|^[A-Z]{2}\\d{4}[A-Z \\d]$",
        "ejemplo_tin": "123456789",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": False,
    },
    {
        "codigo_pais": "IT",
        "pais_nombre": "Italia",
        "formato_tin": "^[A-Z]\\d{11}$",
        "ejemplo_tin": "A12345678901",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "PT",
        "pais_nombre": "Portugal",
        "formato_tin": "^\\d{9}$",
        "ejemplo_tin": "123456789",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "NL",
        "pais_nombre": "Paises Bajos",
        "formato_tin": "^\\d{9}B\\d{2}$",
        "ejemplo_tin": "123456789B01",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "MX",
        "pais_nombre": "Mexico",
        "formato_tin": "^[A-Z&]{3,4}\\d{6}[A-Z\\d]$",
        "ejemplo_tin": "XAXX910101000",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": False,
    },
    {
        "codigo_pais": "BR",
        "pais_nombre": "Brasil",
        "formato_tin": "^\\d{2}\\d{3}\\d{3}\\d{4}\\d{2}$|^\\d{2}\\.\\d{3}\\.\\d{3}\\/\\d{4}\\-\\d{2}$",
        "ejemplo_tin": "123456789012",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": False,
    },
    {
        "codigo_pais": "AR",
        "pais_nombre": "Argentina",
        "formato_tin": "^[A-Z]{1}\\d{8}$|^\\d{11}$",
        "ejemplo_tin": "B12345678",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": False,
    },
    {
        "codigo_pais": "LU",
        "pais_nombre": "Luxemburgo",
        "formato_tin": "^\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}$",
        "ejemplo_tin": "12345678",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "CH",
        "pais_nombre": "Suiza",
        "formato_tin": "^\\d{9}$|^\\d{4}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}$",
        "ejemplo_tin": "123456789",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": False,
    },
    {
        "codigo_pais": "BE",
        "pais_nombre": "Belgica",
        "formato_tin": "^\\d{10}$|^\\d{2}\\s?\\d{6}\\s?\\d{2}$",
        "ejemplo_tin": "0123456789",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
    {
        "codigo_pais": "IE",
        "pais_nombre": "Irlanda",
        "formato_tin": "^[A-Z]\\d{5}\\d|[A-Z]\\d{5}[A-Z]\\d{2}$",
        "ejemplo_tin": "1234567T",
        "emisor_espana": "false",
        "emisor_pais": "true",
        "es_ocde": True,
        "es_eu_vat": True,
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed irs_tin_reference")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in TIN_REFERENCES:
        cur.execute(
            """INSERT INTO irs_tin_reference (codigo_pais, pais_nombre, formato_tin,
               ejemplo_tin, emisor_espana, emisor_pais, es_ocde, es_eu_vat)
               VALUES (%(codigo_pais)s, %(pais_nombre)s, %(formato_tin)s,
                       %(ejemplo_tin)s, %(emisor_espana)s, %(emisor_pais)s,
                       %(es_ocde)s, %(es_eu_vat)s)
               ON CONFLICT (codigo_pais) DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} irs_tin_reference records inserted")
    conn.close()


if __name__ == "__main__":
    main()
