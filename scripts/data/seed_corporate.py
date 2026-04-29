#!/usr/bin/env python3
"""Seed Corporate — Ownership, UBO y entity identifiers.

Crea estructura societaria de ejemplo con 3 empresas, relaciones de
ownership, UBO records y entity identifiers (CIF, LEI, DUNS).

Uso:
    python scripts/data/seed_corporate.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"


# Note: empresa table references documento_interpretativo for source docs.
# We assume empresa rows exist (created by BOE/CNMV/SEPBLAC seeds).
# This script creates ownership_share, ownership_relation, ubo_record, entity_identifiers.

EMPRESAS = [
    {"nombre": "IBERBANK, S.A.", "tipo": "sociedad_anonima", "nif": "A01234567"},
    {"nombre": "BANCO IBEROAMERICANO, S.A.", "tipo": "sociedad_anonima", "nif": "A09876543"},
    {"nombre": "IBERCAPITAL GESTION, S.A.G.I.I.C.", "tipo": "sociedad_gestion_inversion", "nif": "A11223344"},
]


OWNERSHIP_DATA = [
    {"empresa_id": "IBERBANK", "titular_id": "IBERBANK", "titular_tipo": "empresa", "titular_nombre": "IBERBANK, S.A.", "porcentaje": 51.00, "tipo_participacion": "directa", "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2020-001"},
    {"empresa_id": "IBERCAPITAL", "titular_id": "IBERBANK", "titular_tipo": "empresa", "titular_nombre": "IBERBANK, S.A.", "porcentaje": 35.00, "tipo_participacion": "directa", "vigencia_desde": "2019-06-15", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2019-045"},
    {"empresa_id": "IBERBANK", "titular_id": 101, "titular_tipo": "persona", "titular_nombre": "RODRIGUEZ FERNANDEZ, Carlos", "porcentaje": 25.00, "tipo_participacion": "directa", "vigencia_desde": "2018-03-01", "vigencia_hasta": None, "fuente": "CNMV", "fuente_ref": "CNMV-DOC-2018-123"},
    {"empresa_id": "IBERBANK", "titular_id": 102, "titular_tipo": "persona", "titular_nombre": "MARTINEZ LOPEZ, Elena", "porcentaje": 20.00, "tipo_participacion": "directa", "vigencia_desde": "2018-03-01", "vigencia_hasta": None, "fuente": "CNMV", "fuente_ref": "CNMV-DOC-2018-123"},
    {"empresa_id": "IBERCAPITAL", "titular_id": "BANCO_IBEROAMERICANO", "titular_tipo": "empresa", "titular_nombre": "BANCO IBEROAMERICANO, S.A.", "porcentaje": 60.00, "tipo_participacion": "indirecta", "vigencia_desde": "2021-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2021-003"},
    {"empresa_id": "BANCO_IBEROAMERICANO", "titular_id": 101, "titular_tipo": "persona", "titular_nombre": "RODRIGUEZ FERNANDEZ, Carlos", "porcentaje": 15.00, "tipo_participacion": "indirecta", "vigencia_desde": "2022-06-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2022-015"},
]


RELATION_DATA = [
    {"empresa_origen_id": "IBERBANK", "empresa_destino_id": "BANCO_IBEROAMERICANO", "tipo_relacion": "matriz", "porcentaje": 51.00, "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2020-001", "nota": "Iberbank es matriz de Banco Iberoamericano"},
    {"empresa_origen_id": "IBERBANK", "empresa_destino_id": "IBERCAPITAL", "tipo_relacion": "participacion_significativa", "porcentaje": 35.00, "vigencia_desde": "2019-06-15", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2019-045", "nota": "Iberbank tiene participacion significativa en Ibercapital Gestion"},
    {"empresa_origen_id": "BANCO_IBEROAMERICANO", "empresa_destino_id": "IBERCAPITAL", "tipo_relacion": "participacion_mayoritaria", "porcentaje": 60.00, "vigencia_desde": "2021-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2021-003", "nota": "Banco Iberoamericano es matriz mayoritaria de Ibercapital Gestion"},
    {"empresa_origen_id": "IBERBANK", "empresa_destino_id": "IBERCAPITAL", "tipo_relacion": "grupo_economico", "porcentaje": None, "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2020-050", "nota": "Grupo economico financiero Iberbank"},
]


UBO_DATA = [
    {"empresa_id": "IBERBANK", "nombre_persona": "RODRIGUEZ FERNANDEZ, Carlos", "nacionalidad": "ES", "fecha_nacimiento": "1965-04-10", "pais_residencia": "ES", "tipo_ubo": "titular_poder", "porcentaje_control": 25.00, "umbral_superado": "25%", "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2020-001", "nota": "UBO via participacion directa del 25% en Iberbank"},
    {"empresa_id": "IBERBANK", "nombre_persona": "MARTINEZ LOPEZ, Elena", "nacionalidad": "ES", "fecha_nacimiento": "1970-08-22", "pais_residencia": "ES", "tipo_ubo": "titular_propiedad", "porcentaje_control": 20.00, "umbral_superado": "25%", "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "CNMV", "fuente_ref": "CNMV-DOC-2018-123", "nota": "UBO via participacion directa del 20% en Iberbank"},
    {"empresa_id": "IBERBANK", "nombre_persona": "RODRIGUEZ FERNANDEZ, Carlos", "nacionalidad": "ES", "fecha_nacimiento": "1965-04-10", "pais_residencia": "ES", "tipo_ubo": "control_por_otros_medios", "porcentaje_control": 40.00, "umbral_superado": "25%", "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2020-001", "nota": "UBO: Rodriguez controla indirectamente 40%"},
    {"empresa_id": "BANCO_IBEROAMERICANO", "nombre_persona": "RODRIGUEZ FERNANDEZ, Carlos", "nacionalidad": "ES", "fecha_nacimiento": "1965-04-10", "pais_residencia": "ES", "tipo_ubo": "titular_poder", "porcentaje_control": 40.00, "umbral_superado": "25%", "vigencia_desde": "2020-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2022-015", "nota": "UBO via 51% Iberbank + 15% directa = 40% efectivo"},
    {"empresa_id": "IBERCAPITAL", "nombre_persona": "IBERBANK, S.A.", "nacionalidad": "ES", "fecha_nacimiento": None, "pais_residencia": "ES", "tipo_ubo": "titular_propiedad", "porcentaje_control": 56.00, "umbral_superado": "25%", "vigencia_desde": "2021-01-01", "vigencia_hasta": None, "fuente": "BORME", "fuente_ref": "BORME-A-2021-003", "nota": "UBO: Iberbank controla 35% directo + 60% via Banco Iberoamericano = 56% efectivo"},
]


ENTITY_ID_DATA = [
    {"empresa_id": "IBERBANK", "lei": "5493001KJH8X7T1Z9X92", "pais": "ES", "estado": "active", "nota": "LEI de Iberbank, S.A. — ISO 17442"},
    {"empresa_id": "IBERBANK", "nombre_legal": "A01234567", "pais": "ES", "estado": "active", "nota": "CIF A01234567 de Iberbank, S.A."},
    {"empresa_id": "IBERBANK", "nombre_legal": "08-123-4567", "pais": "US", "estado": "active", "nota": "DUNS 08-123-4567 de Iberbank, S.A."},
    {"empresa_id": "BANCO_IBEROAMERICANO", "lei": "549300ABCDEFGH123456", "pais": "ES", "estado": "active", "nota": "LEI de Banco Iberoamericano, S.A."},
    {"empresa_id": "BANCO_IBEROAMERICANO", "nombre_legal": "A09876543", "pais": "ES", "estado": "active", "nota": "CIF A09876543 de Banco Iberoamericano, S.A."},
    {"empresa_id": "IBERCAPITAL", "lei": "549300XYZABC987654", "pais": "ES", "estado": "active", "nota": "LEI de Ibercapital Gestion, S.A.G.I.I.C."},
    {"empresa_id": "IBERCAPITAL", "nombre_legal": "A11223344", "pais": "ES", "estado": "active", "nota": "CIF A11223344 de Ibercapital Gestion, S.A.G.I.I.C."},
]


def main():
    parser = argparse.ArgumentParser(description="Seed Corporate data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(EMPRESAS)} empresas ficticias")
        print(f"[DRY RUN] Would insert {len(OWNERSHIP_DATA)} ownership_share records")
        print(f"[DRY RUN] Would insert {len(RELATION_DATA)} ownership_relation records")
        print(f"[DRY RUN] Would insert {len(UBO_DATA)} ubo_record records")
        print(f"[DRY RUN] Would insert {len(ENTITY_ID_DATA)} entity_identifier records")
        total = len(EMPRESAS) + len(OWNERSHIP_DATA) + len(RELATION_DATA) + len(UBO_DATA) + len(ENTITY_ID_DATA)
        print(f"[DRY RUN] Total: {total} registros")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert/create empresas ficticias
    empresa_ids = {}
    for emp in EMPRESAS:
        cur.execute(
            """INSERT INTO empresa (nombre, nif, fuente_inicial)
               VALUES (%s, %s, 'seed_corporate')
               ON CONFLICT (nombre) DO UPDATE SET nif = EXCLUDED.nif
               RETURNING id""",
            (emp["nombre"], emp["nif"]),
        )
        empresa_ids[emp["nombre"]] = cur.fetchone()[0]

    # Map empresa_ids for ownership/relation/ubo
    id_map = {
        "IBERBANK": empresa_ids["IBERBANK, S.A."],
        "BANCO_IBEROAMERICANO": empresa_ids["BANCO IBEROAMERICANO, S.A."],
        "IBERCAPITAL": empresa_ids["IBERCAPITAL GESTION, S.A.G.I.I.C."],
    }

    # Insert ownership shares
    for o in OWNERSHIP_DATA:
        empresa_id = id_map[o["empresa_id"]]
        titular_id = id_map[o["titular_id"]] if o["titular_id"] in id_map else o["titular_id"]
        cur.execute(
            """INSERT INTO ownership_share (empresa_id, titular_id, titular_tipo, titular_nombre,
               porcentaje, tipo_participacion, vigencia_desde, vigencia_hasta, fuente, fuente_ref)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (empresa_id, titular_id, o["titular_tipo"], o["titular_nombre"],
             o["porcentaje"], o["tipo_participacion"], o["vigencia_desde"],
             o["vigencia_hasta"], o["fuente"], o["fuente_ref"]),
        )

    # Insert ownership relations
    for r in RELATION_DATA:
        origen_id = id_map[r["empresa_origen_id"]]
        destino_id = id_map[r["empresa_destino_id"]]
        cur.execute(
            """INSERT INTO ownership_relation (empresa_origen_id, empresa_destino_id, tipo_relacion,
               porcentaje, vigencia_desde, vigencia_hasta, fuente, fuente_ref, nota)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (empresa_origen_id, empresa_destino_id, tipo_relacion, vigencia_desde) DO UPDATE SET
                   porcentaje = EXCLUDED.porcentaje""",
            (origen_id, destino_id, r["tipo_relacion"], r["porcentaje"],
             r["vigencia_desde"], r["vigencia_hasta"], r["fuente"], r["fuente_ref"], r["nota"]),
        )

    # Insert UBO records
    for u in UBO_DATA:
        empresa_id = id_map[u["empresa_id"]]
        cur.execute(
            """INSERT INTO ubo_record (empresa_id, nombre_persona, nacionalidad, fecha_nacimiento,
               pais_residencia, tipo_ubo, porcentaje_control, umbral_superado, vigencia_desde,
               vigencia_hasta, fuente, fuente_ref, nota)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (empresa_id, u["nombre_persona"], u["nacionalidad"], u["fecha_nacimiento"],
             u["pais_residencia"], u["tipo_ubo"], u["porcentaje_control"], u["umbral_superado"],
             u["vigencia_desde"], u["vigencia_hasta"], u["fuente"], u["fuente_ref"], u["nota"]),
        )

    # Insert entity identifiers
    for e in ENTITY_ID_DATA:
        empresa_id = id_map[e["empresa_id"]]
        if "lei" in e and e["lei"]:
            cur.execute(
                """INSERT INTO entity_identifiers (empresa_id, lei, pais, estado, fuente_ref)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (empresa_id, lei) DO UPDATE SET
                       estado = EXCLUDED.estado""",
                (empresa_id, e["lei"], e["pais"], e["estado"], e["nota"]),
            )
        elif "nombre_legal" in e and e["nombre_legal"]:
            cur.execute(
                """INSERT INTO entity_identifiers (empresa_id, nombre_legal, pais, estado, fuente_ref)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (empresa_id, e["nombre_legal"], e["pais"], e["estado"], e["nota"]),
            )

    conn.commit()
    total = len(EMPRESAS) + len(OWNERSHIP_DATA) + len(RELATION_DATA) + len(UBO_DATA) + len(ENTITY_ID_DATA)
    print(f"OK: {total} registros corporativos insertados ({len(EMPRESAS)} empresas, {len(OWNERSHIP_DATA)} ownership, {len(RELATION_DATA)} relations, {len(UBO_DATA)} UBO, {len(ENTITY_ID_DATA)} entity IDs)")
    conn.close()


if __name__ == "__main__":
    main()
