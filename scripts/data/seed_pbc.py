#!/usr/bin/env python3
"""Seed PBC/FT — Prevencion blanqueo, controles internos, SARs, beneficiarios.

Crea sujetos obligatorios PBC, controles, reportes de actividad sospechosa
y registros de beneficiarios finales conforme a Ley 10/2010.

Uso:
    python scripts/data/seed_pbc.py [--dry-run] [--database-url URL]
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5432/esdata"

SUBJECTS_DATA = [
    {"subject_type": "credit_institution", "tin": "ESA12345678", "registration_number": "B-12345678", "supervisory_authority": "Banco de Espana", "pbc_license": "1/2018", "status": "active"},
    {"subject_type": "investment_firm", "tin": "ESA87654321", "registration_number": "A-98765432", "supervisory_authority": "CNMV", "pbc_license": "2/2018", "status": "active"},
    {"subject_type": "insurance_company", "tin": "ESA11223344", "registration_number": "S-11223344", "supervisory_authority": "DGSFP", "pbc_license": "3/2018", "status": "active"},
    {"subject_type": "trust_company", "tin": "ESA55667788", "registration_number": "TC-55667788", "supervisory_authority": "CNMV", "pbc_license": "4/2018", "status": "active"},
    {"subject_type": "crypto_asset_service", "tin": "ESA99887766", "registration_number": "CA-99887766", "supervisory_authority": "Banco de Espana", "pbc_license": "5/2018", "status": "active"},
    {"subject_type": "real_estate_agency", "tin": "ESA33445566", "registration_number": "RE-33445566", "supervisory_authority": "Ministerio Justicia", "pbc_license": "6/2018", "status": "active"},
]

CONTROLS_DATA = [
    {"obligated_subject_id": None, "risk_assessment_date": "2025-01-15", "compliance_officer": "Maria Garcia Lopez", "internal_reporting_channel": True, "training_program": True, "audit_trail": True},
    {"obligated_subject_id": None, "risk_assessment_date": "2025-02-20", "compliance_officer": "Carlos Fernandez Ruiz", "internal_reporting_channel": True, "training_program": True, "audit_trail": True},
    {"obligated_subject_id": None, "risk_assessment_date": "2025-03-10", "compliance_officer": "Ana Martinez Serra", "internal_reporting_channel": True, "training_program": True, "audit_trail": True},
    {"obligated_subject_id": None, "risk_assessment_date": "2025-04-05", "compliance_officer": "Javier Rodriguez Gil", "internal_reporting_channel": True, "training_program": True, "audit_trail": False},
    {"obligated_subject_id": None, "risk_assessment_date": "2025-05-12", "compliance_officer": "Elena Moreno Vega", "internal_reporting_channel": True, "training_program": True, "audit_trail": True},
    {"obligated_subject_id": None, "risk_assessment_date": "2025-06-18", "compliance_officer": "Pablo Ruiz Diaz", "internal_reporting_channel": True, "training_program": False, "audit_trail": True},
]

SAR_DATA = [
    {"obligated_subject_id": None, "submission_date": "2025-02-10", "description": "Transferencias internacionales sin justificacion economica aparente", "severity": "high", "status": "under_review", "sepblac_reference": "SAR-2025-00145"},
    {"obligated_subject_id": None, "submission_date": "2025-03-22", "description": "Depositos en efectivo superiores a umbral sin origen declarado", "severity": "critical", "status": "escalated", "sepblac_reference": "SAR-2025-00287"},
    {"obligated_subject_id": None, "submission_date": "2025-05-15", "description": "Uso de criptomonedas para estructurar operaciones", "severity": "high", "status": "filed", "sepblac_reference": "SAR-2025-00512"},
    {"obligated_subject_id": None, "submission_date": "2025-07-08", "description": "Operaciones con jurisdicciones de alto riesgo sin justificacion", "severity": "medium", "status": "filed", "sepblac_reference": "SAR-2025-00789"},
    {"obligated_subject_id": None, "submission_date": "2025-09-30", "description": "Posible uso de empresa fantasma para lavado de capitales", "severity": "critical", "status": "under_review", "sepblac_reference": "SAR-2025-01023"},
]

BENEFICIAL_OWNER_DATA = [
    {"entity_id": None, "owner_name": "Grupo Iberfin Holdings S.L.", "ownership_percentage": 45.50, "acquisition_date": "2020-03-15", "verification_method": "registro_mercantil", "verification_date": "2025-01-10"},
    {"entity_id": None, "owner_name": "Carlos Fernandez Ruiz", "ownership_percentage": 25.00, "acquisition_date": "2019-06-01", "verification_method": "dni_verificado", "verification_date": "2025-01-10"},
    {"entity_id": None, "owner_name": "Maria Garcia Lopez", "ownership_percentage": 20.00, "acquisition_date": "2021-01-20", "verification_method": "escritura_publica", "verification_date": "2025-02-15"},
    {"entity_id": None, "owner_name": "BlackRock Fund Managers", "ownership_percentage": 15.75, "acquisition_date": "2022-05-10", "verification_method": "comunicacion_cnmv", "verification_date": "2025-03-01"},
    {"entity_id": None, "owner_name": "Patricia Navarro Soler", "ownership_percentage": 10.25, "acquisition_date": "2023-09-01", "verification_method": "dni_verificado", "verification_date": "2025-04-20"},
    {"entity_id": None, "owner_name": "Inversiones Mediterraneo S.A.", "ownership_percentage": 30.00, "acquisition_date": "2018-11-30", "verification_method": "registro_mercantil", "verification_date": "2025-05-05"},
    {"entity_id": None, "owner_name": "Antonio Lopez Herrera", "ownership_percentage": 20.00, "acquisition_date": "2020-07-15", "verification_method": "escritura_publica", "verification_date": "2025-05-05"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed PBC/FT data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(SUBJECTS_DATA)} obligated subjects")
        print(f"[DRY RUN] Would insert {len(CONTROLS_DATA)} internal controls")
        print(f"[DRY RUN] Would insert {len(SAR_DATA)} suspicious activity reports")
        print(f"[DRY RUN] Would insert {len(BENEFICIAL_OWNER_DATA)} beneficial owner records")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    # Insert subjects
    subject_ids = []
    for s in SUBJECTS_DATA:
        cur.execute(
            """INSERT INTO pbc_obligated_subject (subject_type, tin, registration_number,
               supervisory_authority, pbc_license, status)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (s["subject_type"], s["tin"], s["registration_number"], s["supervisory_authority"],
             s["pbc_license"], s["status"]),
        )
        subject_ids.append(cur.fetchone()[0])

    # Insert controls with subject_id references
    for i, c in enumerate(CONTROLS_DATA):
        cur.execute(
            """INSERT INTO pbc_internal_control (obligated_subject_id, risk_assessment_date,
               compliance_officer, internal_reporting_channel, training_program, audit_trail)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (subject_ids[i] if i < len(subject_ids) else None, c["risk_assessment_date"],
             c["compliance_officer"], c["internal_reporting_channel"], c["training_program"],
             c["audit_trail"]),
        )

    # Insert SARs with subject_id references
    for i, sar in enumerate(SAR_DATA):
        cur.execute(
            """INSERT INTO suspicious_activity_report (obligated_subject_id, submission_date,
               description, severity, status, sepblac_reference)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (subject_ids[i % len(subject_ids)] if i < len(subject_ids) else None,
             sar["submission_date"], sar["description"], sar["severity"], sar["status"],
             sar["sepblac_reference"]),
        )

    # Insert beneficial owners with subject_id references
    for i, bo in enumerate(BENEFICIAL_OWNER_DATA):
        cur.execute(
            """INSERT INTO beneficial_owner_record (entity_id, owner_name, ownership_percentage,
               acquisition_date, verification_method, verification_date)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (subject_ids[i % len(subject_ids)] if i < len(subject_ids) else None,
             bo["owner_name"], float(bo["ownership_percentage"]), bo["acquisition_date"],
             bo["verification_method"], bo["verification_date"]),
        )

    conn.commit()
    total = len(SUBJECTS_DATA) + len(CONTROLS_DATA) + len(SAR_DATA) + len(BENEFICIAL_OWNER_DATA)
    print(f"OK: {total} registros PBC/FT insertados ({len(SUBJECTS_DATA)} subjects, {len(CONTROLS_DATA)} controls, {len(SAR_DATA)} SARs, {len(BENEFICIAL_OWNER_DATA)} beneficial owners)")
    conn.close()


if __name__ == "__main__":
    main()
