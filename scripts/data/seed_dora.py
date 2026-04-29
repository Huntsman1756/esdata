#!/usr/bin/env python3
"""Seed DORA — Resiliencia operacional digital financiera.

Crea incidentes TIC, proveedores terceros, riesgos, pentests y marco clasificacion.

Uso:
    python scripts/data/seed_dora.py [--dry-run] [--database-url URL]
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = "postgresql://esdata:esdata_dev@localhost:5434/esdata"

INCIDENTS_DATA = [
    {"entity_id": None, "incident_severity": "major", "description": "Interrupcion servicio online banking 4 horas", "impact_scope": "customer-facing", "detection_date": "2025-03-15", "resolution_date": "2025-03-15", "root_cause": "failover DNS no configurado correctamente", "classification": "ict_disruption", "status": "resolved"},
    {"entity_id": None, "incident_severity": "significant", "description": "Ataque DDoS contra API de pagos", "impact_scope": "api", "detection_date": "2025-05-20", "resolution_date": "2025-05-21", "root_cause": "vulnerabilidad DDoS en balanceador", "classification": "cyberattack", "status": "resolved"},
    {"entity_id": None, "incident_severity": "high", "description": "Ransomware detectado en red interna", "impact_scope": "internal", "detection_date": "2025-07-10", "resolution_date": "2025-07-14", "root_cause": "phishing email sin parchear endpoint", "classification": "cyberattack", "status": "resolved"},
    {"entity_id": None, "incident_severity": "major", "description": "Caida de centro de datos primario", "impact_scope": "full-operations", "detection_date": "2025-09-01", "resolution_date": "2025-09-02", "root_cause": "fallo alimentacion electrica", "classification": "ict_disruption", "status": "resolved"},
]

PROVIDERS_DATA = [
    {"provider_name": "AWS EU (Ireland)", "provider_type": "cloud_service", "criticality_assessment": "critical", "contract_start": "2022-01-01", "contract_end": "2027-12-31", "eu_supervision_status": "under_supervision", "exit_strategy": "multi-cloud fallback plan documented", "status": "active"},
    {"provider_name": "Microsoft Azure EU", "provider_type": "cloud_service", "criticality_assessment": "critical", "contract_start": "2023-06-01", "contract_end": "2028-05-31", "eu_supervision_status": "under_supervision", "exit_strategy": "hybrid cloud migration in progress", "status": "active"},
    {"provider_name": "Salesforce Financial Services", "provider_type": "saas", "criticality_assessment": "high", "contract_start": "2021-03-01", "contract_end": "2026-02-28", "eu_supervision_status": "not_assessed", "exit_strategy": "data export and CRM migration planned", "status": "active"},
    {"provider_name": "MSCI ESG Research", "provider_type": "data_provider", "criticality_assessment": "moderate", "contract_start": "2020-01-01", "contract_end": "2026-12-31", "eu_supervision_status": "not_assessed", "exit_strategy": "alternative ESG data sources available", "status": "active"},
]

RISK_DATA = [
    {"entity_id": None, "risk_description": "Dependencia de unico proveedor cloud", "likelihood": "unlikely", "impact": "severe", "mitigation": "multi-cloud strategy defined", "owner": "CISO", "review_date": "2026-06-30", "status": "active"},
    {"entity_id": None, "risk_description": "Vulnerabilidades en software de terceros", "likelihood": "likely", "impact": "major", "mitigation": "SBOM tracking and patch management", "owner": "CISO", "review_date": "2026-06-30", "status": "active"},
    {"entity_id": None, "risk_description": "Phishing dirigido a empleados", "likelihood": "almost_certain", "impact": "moderate", "mitigation": "security awareness training quarterly", "owner": "IT Security", "review_date": "2026-03-31", "status": "active"},
    {"entity_id": None, "risk_description": "Fallo de redundancia en DR site", "likelihood": "unlikely", "impact": "severe", "mitigation": "quarterly DR drills", "owner": "IT Operations", "review_date": "2026-09-30", "status": "active"},
]

PENTEST_DATA = [
    {"entity_id": None, "test_type": "external", "tester": "SecuritasIT", "test_date": "2025-04-15", "findings_count": 12, "critical_findings": 1, "remediation_deadline": "2025-07-15", "status": "completed"},
    {"entity_id": None, "test_type": "internal", "tester": "PentesterLab", "test_date": "2025-06-20", "findings_count": 8, "critical_findings": 0, "remediation_deadline": "2025-09-20", "status": "completed"},
    {"entity_id": None, "test_type": "red_team", "tester": "CyberSec Europe", "test_date": "2025-09-10", "findings_count": 15, "critical_findings": 2, "remediation_deadline": "2025-12-10", "status": "in_progress"},
    {"entity_id": None, "test_type": "external", "tester": "SecuritasIT", "test_date": "2026-04-15", "findings_count": None, "critical_findings": None, "remediation_deadline": "2026-07-15", "status": "scheduled"},
]

CLASSIFICATION_DATA = [
    {"framework_version": "v2.1", "severity_thresholds": {"low": {"max_impact": "minor", "max_duration_min": 30}, "moderate": {"max_impact": "moderate", "max_duration_min": 120}, "high": {"max_impact": "major", "max_duration_min": 240}, "major": {"max_impact": "severe", "max_duration_min": 480}, "critical": {"max_impact": "severe", "max_duration_min": 1440}}, "reporting_timelines": {"initial": "4_hours", "intermediate": "24_hours", "final": "72_hours"}, "effective_date": "2024-01-01", "status": "active"},
]


def main():
    parser = argparse.ArgumentParser(description="Seed DORA data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be inserted")
    parser.add_argument("--database-url", default=DEFAULT_DB, help="Database connection string")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] Would insert {len(INCIDENTS_DATA)} TIC incidents")
        print(f"[DRY RUN] Would insert {len(PROVIDERS_DATA)} third-party providers")
        print(f"[DRY RUN] Would insert {len(RISK_DATA)} ICT risks")
        print(f"[DRY RUN] Would insert {len(PENTEST_DATA)} penetration tests")
        print(f"[DRY RUN] Would insert {len(CLASSIFICATION_DATA)} classification frameworks")
        return

    conn = psycopg.connect(args.database_url if args.database_url else DEFAULT_DB)
    cur = conn.cursor()

    for inc in INCIDENTS_DATA:
        cur.execute(
            """INSERT INTO dora_tic_incident (entity_id, incident_severity, description,
               impact_scope, detection_date, resolution_date, root_cause, classification, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (inc["entity_id"], inc["incident_severity"], inc["description"], inc["impact_scope"],
             inc["detection_date"], inc["resolution_date"], inc["root_cause"], inc["classification"],
             inc["status"]),
        )

    for prov in PROVIDERS_DATA:
        cur.execute(
            """INSERT INTO dora_third_party_provider (provider_name, provider_type,
               criticality_assessment, contract_start, contract_end, eu_supervision_status, exit_strategy, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (prov["provider_name"], prov["provider_type"], prov["criticality_assessment"],
             prov["contract_start"], prov["contract_end"], prov["eu_supervision_status"],
             prov["exit_strategy"], prov["status"]),
        )

    for risk in RISK_DATA:
        cur.execute(
            """INSERT INTO dora_ict_risk_register (entity_id, risk_description, likelihood,
               impact, mitigation, owner, review_date, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (risk["entity_id"], risk["risk_description"], risk["likelihood"], risk["impact"],
             risk["mitigation"], risk["owner"], risk["review_date"], risk["status"]),
        )

    for pt in PENTEST_DATA:
        cur.execute(
            """INSERT INTO dora_penetration_test (entity_id, test_type, tester, test_date,
               findings_count, critical_findings, remediation_deadline, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (pt["entity_id"], pt["test_type"], pt["tester"], pt["test_date"],
             pt["findings_count"], pt["critical_findings"], pt["remediation_deadline"], pt["status"]),
        )

    for clf in CLASSIFICATION_DATA:
        cur.execute(
            """INSERT INTO dora_incident_classification_framework (framework_version,
               severity_thresholds, reporting_timelines, effective_date, status)
               VALUES (%s, %s, %s, %s, %s)""",
            (clf["framework_version"], json.dumps(clf["severity_thresholds"]),
             json.dumps(clf["reporting_timelines"]), clf["effective_date"], clf["status"]),
        )

    conn.commit()
    total = len(INCIDENTS_DATA) + len(PROVIDERS_DATA) + len(RISK_DATA) + len(PENTEST_DATA) + len(CLASSIFICATION_DATA)
    print(f"OK: {total} registros DORA insertados ({len(INCIDENTS_DATA)} incidents, {len(PROVIDERS_DATA)} providers, {len(RISK_DATA)} risks, {len(PENTEST_DATA)} pentests, {len(CLASSIFICATION_DATA)} frameworks)")
    conn.close()


if __name__ == "__main__":
    main()
