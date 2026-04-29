#!/usr/bin/env python3
"""Seed data_lineage — Trazabilidad de fuentes para datos ingested.

Crea registros de lineage para los principales workers de ingestion.

Uso:
    python scripts/data/seed_data_lineage.py [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

LINEAGE_DATA = [
    {
        "entry_id": "articulo-001",
        "tabla": "articulo",
        "campo": "titulo",
        "fuente_origen": "BOE-A-2023-12345",
        "transformacion": "extract_text_from_boe_xml",
        "fecha_ingestion": "2026-04-16",
        "worker_correspondiente": "boe_ingestion",
        "calidad_score": 0.95,
        "observaciones": "Texto extraido directamente del BOE sin transformacion",
    },
    {
        "entry_id": "articulo-002",
        "tabla": "articulo",
        "campo": "contenido",
        "fuente_origen": "BOE-A-2023-12345",
        "transformacion": "parse_html_sections",
        "fecha_ingestion": "2026-04-16",
        "worker_correspondiente": "boe_ingestion",
        "calidad_score": 0.92,
        "observaciones": "Parseo HTML con extraccion de secciones jerarquicas",
    },
    {
        "entry_id": "norma-001",
        "tabla": "norma",
        "campo": "titulo",
        "fuente_origen": "BOE-A-2023-12345",
        "transformacion": "extract_norma_metadata",
        "fecha_ingestion": "2026-04-16",
        "worker_correspondiente": "boe_ingestion",
        "calidad_score": 0.98,
        "observaciones": "Metadata extraida del encabezado del BOE",
    },
    {
        "entry_id": "documento-001",
        "tabla": "documento_fragmento",
        "campo": "contenido",
        "fuente_origen": "BOE-A-2023-12345",
        "transformacion": "chunk_text_by_section",
        "fecha_ingestion": "2026-04-16",
        "worker_correspondiente": "boe_ingestion",
        "calidad_score": 0.90,
        "observaciones": "Fragmentos de 500 tokens con overlap 50",
    },
    {
        "entry_id": "empresa-001",
        "tabla": "empresa",
        "campo": "nombre",
        "fuente_origen": "Registro Mercantil ES-B-12345678",
        "transformacion": "normalize_company_name",
        "fecha_ingestion": "2026-04-20",
        "worker_correspondiente": "mercantil_ingestion",
        "calidad_score": 0.97,
        "observaciones": "Nombre normalizado con sufijos juridicos",
    },
    {
        "entry_id": "empresa-002",
        "tabla": "empresa",
        "campo": "cif",
        "fuente_origen": "Registro Mercantil ES-B-12345678",
        "transformacion": "extract_cif_from_registry",
        "fecha_ingestion": "2026-04-20",
        "worker_correspondiente": "mercantil_ingestion",
        "calidad_score": 0.99,
        "observaciones": "CIF validado con algoritmo de control",
    },
    {
        "entry_id": "screening-001",
        "tabla": "screening_entries",
        "campo": "nombre",
        "fuente_origen": "OFAC SDN List 2026-04-01",
        "transformacion": "normalize_sanctions_name",
        "fecha_ingestion": "2026-04-01",
        "worker_correspondiente": "screening_ingestion",
        "calidad_score": 0.88,
        "observaciones": "Nombre normalizado a mayusculas sin acentos",
    },
    {
        "entry_id": "screening-002",
        "tabla": "screening_entries",
        "campo": "aliases",
        "fuente_origen": "OFAC SDN List 2026-04-01",
        "transformacion": "split_aliases_by_comma",
        "fecha_ingestion": "2026-04-01",
        "worker_correspondiente": "screening_ingestion",
        "calidad_score": 0.85,
        "observaciones": "Aliases separados por comas en array JSONB",
    },
    {
        "entry_id": "pgc-001",
        "tabla": "pgc_cuenta",
        "campo": "codigo",
        "fuente_origen": "Real Decreto 1514/2007 PGC",
        "transformacion": "parse_pgc_xml",
        "fecha_ingestion": "2026-04-22",
        "worker_correspondiente": "pgc_ingestion",
        "calidad_score": 0.99,
        "observaciones": "Cuenta extraida del XML oficial del PGC",
    },
    {
        "entry_id": "pgc-002",
        "tabla": "pgc_cuenta",
        "campo": "descripcion",
        "fuente_origen": "Real Decreto 1514/2007 PGC",
        "transformacion": "extract_account_description",
        "fecha_ingestion": "2026-04-22",
        "worker_correspondiente": "pgc_ingestion",
        "calidad_score": 0.96,
        "observaciones": "Descripcion del plan general contable oficial",
    },
    {
        "entry_id": "aeat-001",
        "tabla": "modelo_fiscal_calendar",
        "campo": "fecha_limite",
        "fuente_origen": "AEAT calendario 2026",
        "transformacion": "parse_aeat_calendar",
        "fecha_ingestion": "2026-01-15",
        "worker_correspondiente": "aeat_ingestion",
        "calidad_score": 0.98,
        "observaciones": "Fechas oficiales del calendario AEAT",
    },
    {
        "entry_id": "aeat-002",
        "tabla": "modelo_fiscal_calendar",
        "campo": "periodificacion",
        "fuente_origen": "AEAT calendario 2026",
        "transformacion": "extract_periodification",
        "fecha_ingestion": "2026-01-15",
        "worker_correspondiente": "aeat_ingestion",
        "calidad_score": 0.95,
        "observaciones": "Periodificacion extraida de la normativa AEAT",
    },
    {
        "entry_id": "mifid-001",
        "tabla": "mifid_client_category",
        "campo": "category",
        "fuente_origen": "Directiva MiFID II 2014/65/EU",
        "transformacion": "parse_directive_classification",
        "fecha_ingestion": "2026-04-18",
        "worker_correspondiente": "mifid_ingestion",
        "calidad_score": 0.93,
        "observaciones": "Clasificacion de clientes segun MiFID II",
    },
    {
        "entry_id": "sfdr-001",
        "tabla": "sfdr_product",
        "campo": "product_name",
        "fuente_origen": "Reglamento UE 2019/2088 SFDR",
        "transformacion": "extract_sfdr_product_info",
        "fecha_ingestion": "2026-04-19",
        "worker_correspondiente": "sfdr_ingestion",
        "calidad_score": 0.91,
        "observaciones": "Informacion de productos financieros sostenibles",
    },
    {
        "entry_id": "csrd-001",
        "tabla": "csrd_esg_data_point",
        "campo": "metric_value",
        "fuente_origen": "Directiva CSRD 2022/2464",
        "transformacion": "parse_esg_metrics",
        "fecha_ingestion": "2026-04-21",
        "worker_correspondiente": "csrd_ingestion",
        "calidad_score": 0.89,
        "observaciones": "Metricas ESG extraidas del informe de sostenibilidad",
    },
    {
        "entry_id": "dora-001",
        "tabla": "dora_tic_incident",
        "campo": "incident_severity",
        "fuente_origen": "Reglamento UE 2022/2554 DORA",
        "transformacion": "classify_incident_severity",
        "fecha_ingestion": "2026-04-23",
        "worker_correspondiente": "dora_ingestion",
        "calidad_score": 0.94,
        "observaciones": "Clasificacion de incidentes TIC segun DORA",
    },
    {
        "entry_id": "ownership-001",
        "tabla": "ownership_share",
        "campo": "porcentaje",
        "fuente_origen": "Registro Mercantil ES-B-12345678",
        "transformacion": "extract_shareholding_pct",
        "fecha_ingestion": "2026-04-24",
        "worker_correspondiente": "ownership_ingestion",
        "calidad_score": 0.96,
        "observaciones": "Porcentaje de participacion extraido del registro",
    },
    {
        "entry_id": "ubo-001",
        "tabla": "ubo_record",
        "campo": "nombre_persona",
        "fuente_origen": "Registro UBO ES-12345678901",
        "transformacion": "extract_ubo_name",
        "fecha_ingestion": "2026-04-25",
        "worker_correspondiente": "ubo_ingestion",
        "calidad_score": 0.97,
        "observaciones": "Nombre del beneficiario final del registro oficial",
    },
    {
        "entry_id": "pbc-001",
        "tabla": "pbc_internal_control",
        "campo": "descripcion",
        "fuente_origen": "Ley 10/2010 prevencion blanqueo",
        "transformacion": "parse_pbc_controls",
        "fecha_ingestion": "2026-04-26",
        "worker_correspondiente": "pbc_ingestion",
        "calidad_score": 0.92,
        "observaciones": "Controles internos de prevencion de blanqueo",
    },
    {
        "entry_id": "psd2-001",
        "tabla": "psd2_aspsp",
        "campo": "swift_code",
        "fuente_origen": "Registro Banca PSD2",
        "transformacion": "extract_swift_identifier",
        "fecha_ingestion": "2026-04-27",
        "worker_correspondiente": "psd2_ingestion",
        "calidad_score": 0.98,
        "observaciones": "Codigo SWIFT de entidad de pago",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Seed data_lineage")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    conn = psycopg.connect(args.database_url)
    cur = conn.cursor()

    count = 0
    for d in LINEAGE_DATA:
        cur.execute(
            """INSERT INTO data_lineage (entry_id, tabla, campo, fuente_origen,
               transformacion, fecha_ingestion, worker_correspondiente,
               calidad_score, observaciones)
               VALUES (%(entry_id)s, %(tabla)s, %(campo)s, %(fuente_origen)s,
                       %(transformacion)s, %(fecha_ingestion)s,
                       %(worker_correspondiente)s, %(calidad_score)s, %(observaciones)s)
               ON CONFLICT DO NOTHING""",
            d,
        )
        count += 1

    conn.commit()
    print(f"OK: {count} data_lineage records inserted")
    conn.close()


if __name__ == "__main__":
    main()
