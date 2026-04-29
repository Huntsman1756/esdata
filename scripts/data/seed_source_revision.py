#!/usr/bin/env python3
"""Seed source_revision — Revisiones de fuentes externas ingested.

Crea registros de revision para tracking de cambios en fuentes externas.

Uso:
    python scripts/data/seed_source_revision.py [--database-url URL]
"""

import argparse
import hashlib
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

REVISIONS_DATA = [
    {
        "worker_name": "boe_ingestion",
        "source_entity_tipo": "boe_norma",
        "source_entity_id": "BOE-A-2023-12345",
        "content_hash_sha256": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "etag": "W/\"abc123\"",
        "last_modified": "2026-04-16",
        "content_length": 45230,
        "fetched_at": "2026-04-16 10:30:00+00",
    },
    {
        "worker_name": "boe_ingestion",
        "source_entity_tipo": "boe_norma",
        "source_entity_id": "BOE-A-2023-67890",
        "content_hash_sha256": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
        "etag": "W/\"def456\"",
        "last_modified": "2026-04-16 14:20:00",
        "content_length": 38100,
        "fetched_at": "2026-04-16 14:25:00+00",
    },
    {
        "worker_name": "boe_ingestion",
        "source_entity_tipo": "boe_noticia",
        "source_entity_id": "BOE-N-2026-001",
        "content_hash_sha256": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        "etag": None,
        "last_modified": "2026-04-17 09:00:00",
        "content_length": 12400,
        "fetched_at": "2026-04-17 09:05:00+00",
    },
    {
        "worker_name": "mercantil_ingestion",
        "source_entity_tipo": "registro_mercantil",
        "source_entity_id": "ES-B-12345678",
        "content_hash_sha256": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
        "etag": "\"xyz789\"",
        "last_modified": "2026-04-20 11:00:00",
        "content_length": 89500,
        "fetched_at": "2026-04-20 11:15:00+00",
    },
    {
        "worker_name": "mercantil_ingestion",
        "source_entity_tipo": "registro_mercantil",
        "source_entity_id": "ES-B-87654321",
        "content_hash_sha256": "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
        "etag": None,
        "last_modified": "2026-04-20 15:30:00",
        "content_length": 67200,
        "fetched_at": "2026-04-20 15:45:00+00",
    },
    {
        "worker_name": "screening_ingestion",
        "source_entity_tipo": "ofac_sdn",
        "source_entity_id": "OFAC-SDN-2026-04",
        "content_hash_sha256": "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1",
        "etag": "W/\"ofac123\"",
        "last_modified": "2026-04-01",
        "content_length": 2340000,
        "fetched_at": "2026-04-01 08:00:00+00",
    },
    {
        "worker_name": "screening_ingestion",
        "source_entity_tipo": "eu_sanctions",
        "source_entity_id": "EU-SANCTIONS-2026-04",
        "content_hash_sha256": "a1a2a3a4a5a6a7a8a9a0b1b2b3b4b5b6b7b8b9b0c1c2c3c4c5c6c7c8c9c0d1d2",
        "etag": None,
        "last_modified": "2026-04-10",
        "content_length": 1890000,
        "fetched_at": "2026-04-10 06:00:00+00",
    },
    {
        "worker_name": "pgc_ingestion",
        "source_entity_tipo": "rd_pgс",
        "source_entity_id": "RD-1514-2007",
        "content_hash_sha256": "b1b2b3b4b5b6b7b8b9b0c1c2c3c4c5c6c7c8c9c0d1d2d3d4d5d6d7d8d9d0e1e2",
        "etag": "W/\"pgc456\"",
        "last_modified": "2007-11-09",
        "content_length": 156000,
        "fetched_at": "2026-04-22 10:00:00+00",
    },
    {
        "worker_name": "pgc_ingestion",
        "source_entity_tipo": "guia_pgc",
        "source_entity_id": "GUÍA-PGC-2007",
        "content_hash_sha256": "c1c2c3c4c5c6c7c8c9c0d1d2d3d4d5d6d7d8d9d0e1e2e3e4e5e6e7e8e9e0f1f2",
        "etag": None,
        "last_modified": "2008-01-15",
        "content_length": 890000,
        "fetched_at": "2026-04-22 14:00:00+00",
    },
    {
        "worker_name": "aeat_ingestion",
        "source_entity_tipo": "aeat_calendario",
        "source_entity_id": "AEAT-CAL-2026",
        "content_hash_sha256": "d1d2d3d4d5d6d7d8d9d0e1e2e3e4e5e6e7e8e9e0f1f2f3f4f5f6f7f8f9f0a1a2",
        "etag": "W/\"aeat789\"",
        "last_modified": "2026-01-15",
        "content_length": 45000,
        "fetched_at": "2026-01-15 08:00:00+00",
    },
    {
        "worker_name": "sfdr_ingestion",
        "source_entity_tipo": "reglamento_ue",
        "source_entity_id": "UE-2019-2088",
        "content_hash_sha256": "e1e2e3e4e5e6e7e8e9e0f1f2f3f4f5f6f7f8f9f0a1a2a3a4a5a6a7a8a9a0b1b2",
        "etag": None,
        "last_modified": "2019-12-10",
        "content_length": 234000,
        "fetched_at": "2026-04-19 09:00:00+00",
    },
    {
        "worker_name": "csrd_ingestion",
        "source_entity_tipo": "directiva_ue",
        "source_entity_id": "UE-2022-2464",
        "content_hash_sha256": "f1f2f3f4f5f6f7f8f9f0a1a2a3a4a5a6a7a8a9a0b1b2b3b4b5b6b7b8b9b0c1c2",
        "etag": "W/\"csrd101\"",
        "last_modified": "2022-12-05",
        "content_length": 567000,
        "fetched_at": "2026-04-21 11:00:00+00",
    },
    {
        "worker_name": "dora_ingestion",
        "source_entity_tipo": "reglamento_ue",
        "source_entity_id": "UE-2022-2554",
        "content_hash_sha256": "a2a3a4a5a6a7a8a9a0b1b2b3b4b5b6b7b8b9b0c1c2c3c4c5c6c7c8c9c0d1d2d3",
        "etag": None,
        "last_modified": "2022-12-28",
        "content_length": 189000,
        "fetched_at": "2026-04-23 10:00:00+00",
    },
    {
        "worker_name": "pbc_ingestion",
        "source_entity_tipo": "ley_es",
        "source_entity_id": "Ley-10-2010",
        "content_hash_sha256": "b2b3b4b5b6b7b8b9b0c1c2c3c4c5c6c7c8c9c0d1d2d3d4d5d6d7d8d9d0e1e2e3",
        "etag": "W/\"pbc202\"",
        "last_modified": "2010-04-23",
        "content_length": 78000,
        "fetched_at": "2026-04-26 09:00:00+00",
    },
    {
        "worker_name": "psd2_ingestion",
        "source_entity_tipo": "directiva_ue",
        "source_entity_id": "UE-2015-2366",
        "content_hash_sha256": "c2c3c4c5c6c7c8c9c0d1d2d3d4d5d6d7d8d9d0e1e2e3e4e5e6e7e8e9e0f1f2f3",
        "etag": None,
        "last_modified": "2015-12-16",
        "content_length": 145000,
        "fetched_at": "2026-04-27 08:00:00+00",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed source_revision")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in REVISIONS_DATA:
        cur.execute(
            """INSERT INTO source_revision (worker_name, source_entity_tipo,
               source_entity_id, content_hash_sha256, etag, last_modified,
               content_length, fetched_at)
               VALUES (%(worker_name)s, %(source_entity_tipo)s, %(source_entity_id)s,
                       %(content_hash_sha256)s, %(etag)s, %(last_modified)s,
                       %(content_length)s, %(fetched_at)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} source_revision records inserted")
    conn.close()


if __name__ == "__main__":
    main()
