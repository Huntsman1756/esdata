#!/usr/bin/env python3
"""Seed tablas vacias de dominio regulatorio (MiCA, CRD/BRRD/EMIR, Ownership) con datos fixture minimos.

Cubre: casp, tokenized_asset, wallet_custodian, crd_capital_position, crd_stress_test,
brrd_bail_in, emir_clearing_member, emir_trade_report, ownership_relation, ownership_share,
ubo_record, source_freshness_snapshot, posicion_interpretativa.

Dependencias FK:
  - ownership_relation → empresa(id) x2, documento_interpretativo(id)
  - ownership_share → empresa(id), documento_interpretativo(id)
  - ubo_record → empresa(id), documento_interpretativo(id)
  - posicion_interpretativa → documento_interpretativo(id)

Uso:
    python scripts/data/seed_remaining_tables.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

# ── casp (MiCA) ───────────────────────────────────────────────────────────
CASPS = [
    {
        "name": "Binance Europe AB",
        "registration_number": "CASP-ES-001",
        "home_member_state": "ES",
        "passport_active": True,
        "services_offered": "exchange, wallet, custody",
        "status": "active",
    },
    {
        "name": "Coinbase Europe Limited",
        "registration_number": "CASP-IE-002",
        "home_member_state": "IE",
        "passport_active": True,
        "services_offered": "exchange, OTC",
        "status": "active",
    },
    {
        "name": "Kraken Services Ireland Limited",
        "registration_number": "CASP-IE-003",
        "home_member_state": "IE",
        "passport_active": False,
        "services_offered": "exchange, margin trading",
        "status": "active",
    },
]

# ── tokenized_asset (MiCA) ────────────────────────────────────────────────
TOKENIZED_ASSETS = [
    {
        "underlying_type": "equity",
        "issuer_id": 1,
        "face_value": 100.00,
        "total_amount": 5000000.00,
        "listing_date": "2026-01-15",
        "regulated_market": "BME Spanish Market",
        "status": "active",
    },
    {
        "underlying_type": "debt",
        "issuer_id": 3,
        "face_value": 1000.00,
        "total_amount": 50000000.00,
        "listing_date": "2026-02-01",
        "regulated_market": "BME Spanish Market",
        "status": "active",
    },
    {
        "underlying_type": "real_estate",
        "issuer_id": 2,
        "face_value": 250.00,
        "total_amount": 2500000.00,
        "listing_date": "2026-03-10",
        "regulated_market": "BME Spanish Market",
        "status": "pending",
    },
]

# ── wallet_custodian (MiCA) ───────────────────────────────────────────────
WALLET_CUSTODIANS = [
    {
        "entity_id": 3,
        "wallet_type": "hot_wallet",
        "custody_mechanism": "multi_sig",
        "insurance_coverage": 1000000.00,
        "audit_frequency": "quarterly",
        "status": "active",
    },
    {
        "entity_id": 3,
        "wallet_type": "cold_wallet",
        "custody_mechanism": "offline_hsm",
        "insurance_coverage": 5000000.00,
        "audit_frequency": "annual",
        "status": "active",
    },
    {
        "entity_id": 1,
        "wallet_type": "hot_wallet",
        "custody_mechanism": "multi_sig",
        "insurance_coverage": 500000.00,
        "audit_frequency": "quarterly",
        "status": "active",
    },
]

# ── crd_capital_position ──────────────────────────────────────────────────
CRD_CAPITAL_POSITIONS = [
    {
        "entity_id": 3,
        "reporting_date": "2025-12-31",
        "cet1_ratio": 15.2345,
        "tier1_ratio": 17.8901,
        "total_capital_ratio": 19.5678,
        "cet1_amount": 28500000000.00,
        "tier1_amount": 33400000000.00,
        "total_capital_amount": 36700000000.00,
        "leverage_ratio": 6.1234,
        "risk_weighted_assets": 187300000000.00,
        "status": "filed",
    },
    {
        "entity_id": 4,
        "reporting_date": "2025-12-31",
        "cet1_ratio": 14.5678,
        "tier1_ratio": 16.2345,
        "total_capital_ratio": 18.1234,
        "cet1_amount": 8900000000.00,
        "tier1_amount": 9900000000.00,
        "total_capital_amount": 11100000000.00,
        "leverage_ratio": 5.8901,
        "risk_weighted_assets": 61200000000.00,
        "status": "filed",
    },
    {
        "entity_id": 5,
        "reporting_date": "2025-12-31",
        "cet1_ratio": 18.3456,
        "tier1_ratio": 19.1234,
        "total_capital_ratio": 20.4567,
        "cet1_amount": 4200000000.00,
        "tier1_amount": 4400000000.00,
        "total_capital_amount": 4700000000.00,
        "leverage_ratio": 7.2345,
        "risk_weighted_assets": 22900000000.00,
        "status": "filed",
    },
]

# ── crd_stress_test ───────────────────────────────────────────────────────
CRD_STRESS_TESTS = [
    {
        "entity_id": 3,
        "test_date": "2025-10-31",
    },
    {
        "entity_id": 4,
        "test_date": "2025-10-31",
    },
]

# ── brrd_bail_in ──────────────────────────────────────────────────────────
BRRD_BAIL_INS = [
    {
        "entity_id": 3,
        "total_eligible_liabilities": 150000000000.00,
        "mrel_target_pct": 21.0000,
        "mrel_compliance_pct": 22.5000,
        "internal_mrel": 23.1000,
        "resolution_status": "compliant",
        "status": "active",
    },
    {
        "entity_id": 4,
        "total_eligible_liabilities": 45000000000.00,
        "mrel_target_pct": 18.0000,
        "mrel_compliance_pct": 17.8000,
        "internal_mrel": 18.5000,
        "resolution_status": "non_compliant",
        "status": "active",
    },
]

# ── emir_clearing_member ──────────────────────────────────────────────────
EMIR_CLEARING_MEMBERS = [
    {
        "entity_id": 3,
        "emir_registration": "EMIR-CM-ES-001",
        "clearing_type": "central",
        "status": "active",
    },
    {
        "entity_id": 1,
        "emir_registration": "EMIR-CM-ES-002",
        "clearing_type": "central",
        "status": "active",
    },
]

# ── emir_trade_report ─────────────────────────────────────────────────────
EMIR_TRADE_REPORTS = [
    {
        "trade_id": "TRD-EMIR-2026-001",
        "asset_class": "interest_rate",
        "instrument_class": "swap",
        "clearing_obligation_applied": True,
        "reporting_delay_days": 1,
        "counterparty_type": "financial",
        "status": "reported",
    },
    {
        "trade_id": "TRD-EMIR-2026-002",
        "asset_class": "credit_default_swap",
        "instrument_class": "cds",
        "clearing_obligation_applied": False,
        "reporting_delay_days": 1,
        "counterparty_type": "non_financial",
        "status": "reported",
    },
    {
        "trade_id": "TRD-EMIR-2026-003",
        "asset_class": "equity",
        "instrument_class": "option",
        "clearing_obligation_applied": False,
        "reporting_delay_days": 2,
        "counterparty_type": "financial",
        "status": "reported",
    },
]

# ── ownership_relation ────────────────────────────────────────────────────
OWNERSHIP_RELATIONS = [
    {
        "empresa_origen_id": 3,
        "empresa_destino_id": 1,
        "tipo_relacion": "participacion_significativa",
        "porcentaje": 5.2300,
        "vigencia_desde": "2024-01-01",
        "fuente": "CNMV",
        "fuente_ref": "CNMV-2024-001",
        "documento_id": 1,
        "nota": "Participacion significativa reportada segun art. 12 RLACVM",
    },
    {
        "empresa_origen_id": 2,
        "empresa_destino_id": 5,
        "tipo_relacion": "participacion_mayoritaria",
        "porcentaje": 67.5000,
        "vigencia_desde": "2020-06-15",
        "fuente": "MERC",
        "fuente_ref": "MERC-2020-045",
        "documento_id": 2,
        "nota": "Filial mayoritaria — consolidacion contable",
    },
    {
        "empresa_origen_id": 4,
        "empresa_destino_id": 1,
        "tipo_relacion": "participacion_significativa",
        "porcentaje": 3.8700,
        "vigencia_desde": "2025-03-01",
        "fuente": "CNMV",
        "fuente_ref": "CNMV-2025-012",
        "nota": "Participacion reportada Q1 2025",
    },
]

# ── ownership_share ───────────────────────────────────────────────────────
OWNERSHIP_SHARES = [
    {
        "empresa_id": 1,
        "titular_id": 3,
        "titular_tipo": "empresa",
        "titular_nombre": "Banco Santander, S.A.",
        "porcentaje": 5.2300,
        "tipo_participacion": "directa",
        "vigencia_desde": "2024-01-01",
        "fuente": "CNMV",
        "fuente_ref": "CNMV-2024-001",
        "documento_id": 1,
    },
    {
        "empresa_id": 2,
        "titular_id": 1,
        "titular_tipo": "empresa",
        "titular_nombre": "Telefonica, S.A.",
        "porcentaje": 67.5000,
        "tipo_participacion": "directa",
        "vigencia_desde": "2020-06-15",
        "fuente": "MERC",
        "fuente_ref": "MERC-2020-045",
        "documento_id": 2,
    },
    {
        "empresa_id": 3,
        "titular_id": 2,
        "titular_tipo": "empresa",
        "titular_nombre": "Inditex, S.A.",
        "porcentaje": 2.1500,
        "tipo_participacion": "indirecta",
        "vigencia_desde": "2025-01-01",
        "fuente": "CNMV",
        "fuente_ref": "CNMV-2025-008",
    },
]

# ── ubo_record ────────────────────────────────────────────────────────────
UBO_RECORDS = [
    {
        "empresa_id": 1,
        "nombre_persona": "Jesus Gil Martinez",
        "nacionalidad": "ES",
        "fecha_nacimiento": "1965-03-22",
        "pais_residencia": "ES",
        "tipo_ubo": "titular_propiedad",
        "porcentaje_control": 23.4500,
        "umbral_superado": "si",
        "vigencia_desde": "2024-01-01",
        "fuente": "MERC",
        "fuente_ref": "MERC-2024-010",
        "documento_id": 1,
        "nota": "Ultimo UBO registrado en MERC — cumple art. 14 RDL 5/2020",
    },
    {
        "empresa_id": 2,
        "nombre_persona": "Maria Fernandez Lopez",
        "nacionalidad": "ES",
        "fecha_nacimiento": "1972-07-14",
        "pais_residencia": "ES",
        "tipo_ubo": "titular_poder",
        "porcentaje_control": 18.9000,
        "umbral_superado": "si",
        "vigencia_desde": "2024-06-01",
        "fuente": "MERC",
        "fuente_ref": "MERC-2024-032",
        "documento_id": 2,
    },
    {
        "empresa_id": 3,
        "nombre_persona": "Antonio Rodriguez Ruiz",
        "nacionalidad": "ES",
        "fecha_nacimiento": "1968-11-30",
        "pais_residencia": "ES",
        "tipo_ubo": "control_por_otros_medios",
        "porcentaje_control": 31.2000,
        "umbral_superado": "si",
        "vigencia_desde": "2025-01-01",
        "fuente": "CNMV",
        "fuente_ref": "CNMV-2025-015",
        "nota": "Control por acuerdo de votacion — art. 5.10 RLACVM",
    },
]

# ── source_freshness_snapshot ─────────────────────────────────────────────
SOURCE_FRESHNESS_SNAPSHOTS = [
    {
        "snapshot_id": "snap-borme-20260429-001",
        "source_id": "borme",
        "snapshot_version": "v1.0.0",
        "snapshot_at": "2026-04-29T06:00:00+00:00",
        "last_success_at": "2026-04-29T06:15:23+00:00",
        "last_status": "success",
        "stale": 0,
        "cadencia": "daily",
        "modo_deteccion_cambios": "manifest_hash",
        "manifest_hash": "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        "payload": '{"total_records": 1247, "new_entries": 34, "modified_entries": 12}',
    },
    {
        "snapshot_id": "snap-boe-20260429-001",
        "source_id": "boe",
        "snapshot_version": "v2.1.0",
        "snapshot_at": "2026-04-29T05:00:00+00:00",
        "last_success_at": "2026-04-29T05:45:12+00:00",
        "last_status": "success",
        "stale": 0,
        "cadencia": "daily",
        "modo_deteccion_cambios": "manifest_hash",
        "manifest_hash": "sha256:b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
        "payload": '{"total_records": 8934, "new_entries": 156, "modified_entries": 45}',
    },
    {
        "snapshot_id": "snap-cnmv-20260429-001",
        "source_id": "cnmv",
        "snapshot_version": "v1.2.0",
        "snapshot_at": "2026-04-29T07:00:00+00:00",
        "last_success_at": "2026-04-29T07:22:45+00:00",
        "last_status": "success",
        "stale": 0,
        "cadencia": "daily",
        "modo_deteccion_cambios": "manifest_hash",
        "manifest_hash": "sha256:c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
        "payload": '{"total_records": 3421, "new_entries": 89, "modified_entries": 23}',
    },
]

# ── posicion_interpretativa ───────────────────────────────────────────────
POSICIONES_INTERPRETATIVAS = [
    {
        "titulo": "Aplicabilidad del tipo reducido IS para startups — interpretacion art. 34 LIS modificado",
        "descripcion": "Analisis de los requisitos para acceder al tipo reducido del 15% para startups segun la reforma de la Ley 28/2025.",
        "contenido": "Las startups calificadas podran acceder al tipo reducido del 15% durante los tres primeros ejercicios tributes con resultado de imposicion negativa, siempre que cumplan los requisitos del art. 34 LIS (modificado) y no tengan actividad financiera predominante.",
        "fuente_oficial_referencia": "BOE-A-2025-4567",
        "documento_origen_id": 3,
        "autor_id": "analista-fiscal-001",
        "estado": "revision",
        "vigencia_desde": "2026-01-01",
    },
    {
        "titulo": "Interpretacion de UBO para estructuras societarias multinivel",
        "descripcion": "Criterios para identificar el beneficiario final en estructuras con multiples capas de participacion.",
        "contenido": "En estructuras multinivel, el umbral del 25% se aplica de forma acumulativa a lo largo de toda la cadena de control. Se considera UBO a toda persona fisica que controle directa o indirectamente al menos el 25% del capital o derechos de votacion.",
        "fuente_oficial_referencia": "BOE-A-2020-9563",
        "documento_origen_id": 4,
        "autor_id": "cumplimiento-001",
        "revisor_id": "cumplimiento-lead-001",
        "estado": "borrador",
        "vigencia_desde": "2024-01-01",
    },
]


def upsert_casp(cur, row):
    cur.execute(
        """INSERT INTO casp (name, registration_number, home_member_state,
           passport_active, services_offered, status)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (registration_number, home_member_state) DO NOTHING""",
        (row["name"], row.get("registration_number"), row.get("home_member_state"),
         row["passport_active"], row.get("services_offered"), row["status"]),
    )


def upsert_tokenized_asset(cur, row):
    cur.execute(
        """INSERT INTO tokenized_asset (underlying_type, issuer_id, face_value,
           total_amount, listing_date, regulated_market, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["underlying_type"], row.get("issuer_id"), row.get("face_value"),
         row.get("total_amount"), row.get("listing_date"),
         row.get("regulated_market"), row["status"]),
    )


def upsert_wallet_custodian(cur, row):
    cur.execute(
        """INSERT INTO wallet_custodian (entity_id, wallet_type, custody_mechanism,
           insurance_coverage, audit_frequency, status)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row.get("entity_id"), row["wallet_type"], row.get("custody_mechanism"),
         row.get("insurance_coverage"), row.get("audit_frequency"), row["status"]),
    )


def upsert_crd_capital_position(cur, row):
    cur.execute(
        """INSERT INTO crd_capital_position (entity_id, reporting_date, cet1_ratio,
           tier1_ratio, total_capital_ratio, cet1_amount, tier1_amount,
           total_capital_amount, leverage_ratio, risk_weighted_assets, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["entity_id"], row["reporting_date"], row.get("cet1_ratio"),
         row.get("tier1_ratio"), row.get("total_capital_ratio"),
         row.get("cet1_amount"), row.get("tier1_amount"),
         row.get("total_capital_amount"), row.get("leverage_ratio"),
         row.get("risk_weighted_assets"), row["status"]),
    )


def upsert_crd_stress_test(cur, row):
    cur.execute(
        """INSERT INTO crd_stress_test (entity_id, test_date)
           VALUES (%s, %s)
           ON CONFLICT DO NOTHING""",
        (row["entity_id"], row["test_date"]),
    )


def upsert_brrd_bail_in(cur, row):
    cur.execute(
        """INSERT INTO brrd_bail_in (entity_id, total_eligible_liabilities,
           mrel_target_pct, mrel_compliance_pct, internal_mrel,
           resolution_status, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["entity_id"], row.get("total_eligible_liabilities"),
         row.get("mrel_target_pct"), row.get("mrel_compliance_pct"),
         row.get("internal_mrel"), row.get("resolution_status"), row["status"]),
    )


def upsert_emir_clearing_member(cur, row):
    cur.execute(
        """INSERT INTO emir_clearing_member (entity_id, emir_registration,
           clearing_type, status)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["entity_id"], row.get("emir_registration"), row["clearing_type"], row["status"]),
    )


def upsert_emir_trade_report(cur, row):
    cur.execute(
        """INSERT INTO emir_trade_report (trade_id, asset_class, instrument_class,
           clearing_obligation_applied, reporting_delay_days, counterparty_type, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["trade_id"], row["asset_class"], row.get("instrument_class"),
         row["clearing_obligation_applied"], row.get("reporting_delay_days"),
         row.get("counterparty_type"), row["status"]),
    )


def upsert_ownership_relation(cur, row):
    cur.execute(
        """INSERT INTO ownership_relation (empresa_origen_id, empresa_destino_id,
           tipo_relacion, porcentaje, vigencia_desde, fuente, fuente_ref,
           documento_id, nota)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["empresa_origen_id"], row["empresa_destino_id"], row["tipo_relacion"],
         row.get("porcentaje"), row.get("vigencia_desde"), row["fuente"],
         row.get("fuente_ref"), row.get("documento_id"), row.get("nota")),
    )


def upsert_ownership_share(cur, row):
    cur.execute(
        """INSERT INTO ownership_share (empresa_id, titular_id, titular_tipo,
           titular_nombre, porcentaje, tipo_participacion, vigencia_desde,
           fuente, fuente_ref, documento_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["empresa_id"], row["titular_id"], row["titular_tipo"],
         row["titular_nombre"], row["porcentaje"], row["tipo_participacion"],
         row.get("vigencia_desde"), row["fuente"], row.get("fuente_ref"),
         row.get("documento_id")),
    )


def upsert_ubo_record(cur, row):
    cur.execute(
        """INSERT INTO ubo_record (empresa_id, nombre_persona, nacionalidad,
           fecha_nacimiento, pais_residencia, tipo_ubo, porcentaje_control,
           umbral_superado, vigencia_desde, fuente, fuente_ref, documento_id, nota)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING""",
        (row["empresa_id"], row["nombre_persona"], row.get("nacionalidad"),
         row.get("fecha_nacimiento"), row.get("pais_residencia"), row["tipo_ubo"],
         row.get("porcentaje_control"), row.get("umbral_superado"),
         row.get("vigencia_desde"), row["fuente"], row.get("fuente_ref"),
         row.get("documento_id"), row.get("nota")),
    )


def upsert_source_freshness(cur, row):
    cur.execute(
        """INSERT INTO source_freshness_snapshot (snapshot_id, source_id,
           snapshot_version, snapshot_at, last_success_at, last_status,
           stale, cadencia, modo_deteccion_cambios, manifest_hash, payload)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::json)
           ON CONFLICT (snapshot_id) DO NOTHING""",
        (row["snapshot_id"], row["source_id"], row["snapshot_version"],
         row["snapshot_at"], row.get("last_success_at"), row["last_status"],
         row.get("stale"), row["cadencia"], row["modo_deteccion_cambios"],
         row["manifest_hash"], row.get("payload")),
    )


def upsert_posicion_interpretativa(cur, row):
    cur.execute(
        """INSERT INTO posicion_interpretativa (titulo, descripcion, contenido,
           fuente_oficial_referencia, documento_origen_id, autor_id, revisor_id,
           estado, version, vigencia_desde, vigencia_hasta, fecha_creacion, fecha_revision)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s)
           ON CONFLICT DO NOTHING""",
        (row["titulo"], row.get("descripcion"), row.get("contenido"),
         row.get("fuente_oficial_referencia"), row.get("documento_origen_id"),
         row["autor_id"], row.get("revisor_id"), row["estado"], row.get("version", 1),
         row.get("vigencia_desde"), row.get("vigencia_hasta"), row.get("fecha_revision")),
    )


def main():
    parser = argparse.ArgumentParser(description="Seed remaining empty tables with fixture data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        counts = {
            "casp": len(CASPS),
            "tokenized_asset": len(TOKENIZED_ASSETS),
            "wallet_custodian": len(WALLET_CUSTODIANS),
            "crd_capital_position": len(CRD_CAPITAL_POSITIONS),
            "crd_stress_test": len(CRD_STRESS_TESTS),
            "brrd_bail_in": len(BRRD_BAIL_INS),
            "emir_clearing_member": len(EMIR_CLEARING_MEMBERS),
            "emir_trade_report": len(EMIR_TRADE_REPORTS),
            "ownership_relation": len(OWNERSHIP_RELATIONS),
            "ownership_share": len(OWNERSHIP_SHARES),
            "ubo_record": len(UBO_RECORDS),
            "source_freshness_snapshot": len(SOURCE_FRESHNESS_SNAPSHOTS),
            "posicion_interpretativa": len(POSICIONES_INTERPRETATIVAS),
        }
        total = sum(counts.values())
        print(f"[DRY RUN] Would insert {total} rows across {len(counts)} tables:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # 1. casp (no FKs)
    for row in CASPS:
        upsert_casp(cur, row)
    print(f"  casp: {len(CASPS)} rows")

    # 2. tokenized_asset (issuer_id FK to empresa)
    for row in TOKENIZED_ASSETS:
        upsert_tokenized_asset(cur, row)
    print(f"  tokenized_asset: {len(TOKENIZED_ASSETS)} rows")

    # 3. wallet_custodian (entity_id FK to empresa)
    for row in WALLET_CUSTODIANS:
        upsert_wallet_custodian(cur, row)
    print(f"  wallet_custodian: {len(WALLET_CUSTODIANS)} rows")

    # 4. crd_capital_position (entity_id FK to empresa)
    for row in CRD_CAPITAL_POSITIONS:
        upsert_crd_capital_position(cur, row)
    print(f"  crd_capital_position: {len(CRD_CAPITAL_POSITIONS)} rows")

    # 5. crd_stress_test (entity_id FK to empresa)
    for row in CRD_STRESS_TESTS:
        upsert_crd_stress_test(cur, row)
    print(f"  crd_stress_test: {len(CRD_STRESS_TESTS)} rows")

    # 6. brrd_bail_in (entity_id FK to empresa)
    for row in BRRD_BAIL_INS:
        upsert_brrd_bail_in(cur, row)
    print(f"  brrd_bail_in: {len(BRRD_BAIL_INS)} rows")

    # 7. emir_clearing_member (entity_id FK to empresa)
    for row in EMIR_CLEARING_MEMBERS:
        upsert_emir_clearing_member(cur, row)
    print(f"  emir_clearing_member: {len(EMIR_CLEARING_MEMBERS)} rows")

    # 8. emir_trade_report (no FKs)
    for row in EMIR_TRADE_REPORTS:
        upsert_emir_trade_report(cur, row)
    print(f"  emir_trade_report: {len(EMIR_TRADE_REPORTS)} rows")

    # 9. ownership_relation (empresa x2 FK, documento_interpretativo FK)
    for row in OWNERSHIP_RELATIONS:
        upsert_ownership_relation(cur, row)
    print(f"  ownership_relation: {len(OWNERSHIP_RELATIONS)} rows")

    # 10. ownership_share (empresa FK, documento_interpretativo FK)
    for row in OWNERSHIP_SHARES:
        upsert_ownership_share(cur, row)
    print(f"  ownership_share: {len(OWNERSHIP_SHARES)} rows")

    # 11. ubo_record (empresa FK, documento_interpretativo FK)
    for row in UBO_RECORDS:
        upsert_ubo_record(cur, row)
    print(f"  ubo_record: {len(UBO_RECORDS)} rows")

    # 12. source_freshness_snapshot (no FKs)
    for row in SOURCE_FRESHNESS_SNAPSHOTS:
        upsert_source_freshness(cur, row)
    print(f"  source_freshness_snapshot: {len(SOURCE_FRESHNESS_SNAPSHOTS)} rows")

    # 13. posicion_interpretativa (documento_interpretativo FK)
    for row in POSICIONES_INTERPRETATIVAS:
        upsert_posicion_interpretativa(cur, row)
    print(f"  posicion_interpretativa: {len(POSICIONES_INTERPRETATIVAS)} rows")

    conn.commit()
    total = sum([
        len(CASPS), len(TOKENIZED_ASSETS), len(WALLET_CUSTODIANS),
        len(CRD_CAPITAL_POSITIONS), len(CRD_STRESS_TESTS), len(BRRD_BAIL_INS),
        len(EMIR_CLEARING_MEMBERS), len(EMIR_TRADE_REPORTS),
        len(OWNERSHIP_RELATIONS), len(OWNERSHIP_SHARES), len(UBO_RECORDS),
        len(SOURCE_FRESHNESS_SNAPSHOTS), len(POSICIONES_INTERPRETATIVAS),
    ])
    print(f"OK: {total} rows inserted across {13} tables")
    conn.close()


if __name__ == "__main__":
    main()
