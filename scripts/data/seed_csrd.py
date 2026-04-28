#!/usr/bin/env python
"""Seed CSRD (Corporate Sustainability Reporting Directive) data.

Fase 31.9.2 — Expansion regulatoria: CSRD.

Tablas: csrd_entity_report, csrd_esg_data_point, csrd_ess, csrd_double_materiality

Fuente: ESAP (European Single Access Point)
verified_date: 2026-04-28
"""

import psycopg

DB = "postgresql://esdata:esdata_dev@postgres:5432/esdata"

CSRD_ENTITY_REPORTS = [
    (1, 2024, "https://www.esap.europa.eu/csrd/accelera-2024", "limited", "ESGAS", "active"),
    (2, 2024, "https://www.esap.europa.eu/csrd/santander-2024", "limited", "ESGAS", "active"),
    (3, 2024, "https://www.esap.europa.eu/csrd/iberdrola-2024", "reasonable", "ESGAS", "active"),
    (4, 2023, "https://www.esap.europa.eu/csrd/repsol-2023", "limited", "ESGAS", "active"),
]

CSRD_ESG_DATA_POINTS = [
    # Report 1 — Accelera (energy sector)
    (1, "environment", "G1-ECO-1", 125000.0, "tCO2e", 1, "verified"),
    (1, "environment", "G1-ECO-2", 85000.0, "tCO2e", 2, "verified"),
    (1, "environment", "G1-ECO-3", 45000.0, "tCO2e", 3, "verified"),
    (1, "environment", "G1-EN-1", 850.0, "GWh", None, "verified"),
    (1, "environment", "G1-EN-2", 12.5, "%", None, "verified"),
    (1, "social", "G1-SO-1", 3200, "number", None, "verified"),
    (1, "social", "G1-SO-2", 2.8, "%", None, "verified"),
    (1, "governance", "G1-GV-1", 12, "number", None, "verified"),
    # Report 2 — Santander
    (2, "environment", "G1-ECO-1", 42000.0, "tCO2e", 1, "verified"),
    (2, "environment", "G1-ECO-2", 28000.0, "tCO2e", 2, "verified"),
    (2, "social", "G1-SO-1", 58000, "number", None, "verified"),
    (2, "social", "G1-SO-3", 52.3, "%", None, "verified"),
    (2, "governance", "G1-GV-1", 18, "number", None, "verified"),
    # Report 3 — Iberdrola
    (3, "environment", "G1-ECO-1", 2100000.0, "tCO2e", 1, "verified"),
    (3, "environment", "G1-EN-1", 5200.0, "GWh", None, "verified"),
    (3, "environment", "G1-EN-2", 38.2, "%", None, "verified"),
    (3, "social", "G1-SO-1", 28500, "number", None, "verified"),
    (3, "social", "G1-SO-2", 1.5, "%", None, "verified"),
    (3, "governance", "G1-GV-1", 15, "number", None, "verified"),
]

CSRD_ES = [
    ("ESRS E1", "environment", 2024, "Climate change — mitigation, adaptation, resilience"),
    ("ESRS E2", "environment", 2024, "Pollution — prevention, control, remediation"),
    ("ESRS E3", "environment", 2025, "Water and marine resources — consumption, protection"),
    ("ESRS E4", "environment", 2025, "Biodiversity and ecosystems — protection, restoration"),
    ("ESRS E5", "environment", 2025, "Resource use and circular economy — efficiency, waste"),
    ("ESRS S1", "social", 2024, "Own workforce — working conditions, diversity, health & safety"),
    ("ESRS S2", "social", 2024, "Workers in value chain — labor rights, living wage"),
    ("ESRS S3", "social", 2025, "Affected communities — impact, benefit sharing"),
    ("ESRS S4", "social", 2025, "Consumers and end-users — product responsibility, privacy"),
    ("ESRS G1", "governance", 2024, "Business conduct — anti-corruption, competitive behavior"),
]

CSRD_DOUBLE_MATERIALITY = [
    (1, '{"impact": {"climate_change": "high", "pollution": "medium"}, "financial": {"climate_change": "high", "regulatory": "medium"}}', '{"impact": {"transition_risk": "high"}, "financial": {"reputation": "medium"}}', "2024-06-15", "High carbon footprint from energy generation operations; significant regulatory transition risk", "Dependency on water resources for cooling; biodiversity impact near generation sites", "active"),
    (2, '{"impact": {"financial_inclusion": "medium"}, "financial": {"reputational": "low", "regulatory": "high"}}', '{"impact": {"supply_chain": "medium"}, "financial": {"operational": "low"}}', "2024-06-20", "Limited direct environmental impact as financial intermediary", "Regulatory pressure on ESG data quality and greenwashing risk", "active"),
    (3, '{"impact": {"climate_change": "high", "biodiversity": "medium"}, "financial": {"climate_change": "high", "physical_risk": "medium"}}', '{"impact": {"value_chain": "medium"}, "financial": {"market": "high"}}', "2024-07-01", "Major greenhouse gas emitter from thermal generation; significant biodiversity risk at hydroelectric sites", "High exposure to climate physical risks on infrastructure; market risk from energy transition", "active"),
]


def _upsert_report(cur, row):
    cur.execute(
        """INSERT INTO csrd_entity_report
           (entity_id, reporting_year, esap_url, assurance_status, reporting_standard, status)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (entity_id, reporting_year) DO UPDATE SET
             esap_url = EXCLUDED.esap_url,
             assurance_status = EXCLUDED.assurance_status,
             reporting_standard = EXCLUDED.reporting_standard,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_esg_data_point(cur, row):
    cur.execute(
        """INSERT INTO csrd_esg_data_point
           (report_id, topic, indicator_code, value, unit, scope, verification_status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (report_id, topic, indicator_code) DO UPDATE SET
             value = EXCLUDED.value,
             unit = EXCLUDED.unit,
             scope = EXCLUDED.scope,
             verification_status = EXCLUDED.verification_status""",
        row,
    )


def _upsert_ess(cur, row):
    cur.execute(
        """INSERT INTO csrd_ess
           (standard_code, topic, applicable_from_year, description, status)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (standard_code) DO UPDATE SET
             topic = EXCLUDED.topic,
             applicable_from_year = EXCLUDED.applicable_from_year,
             description = EXCLUDED.description,
             status = EXCLUDED.status""",
        row,
    )


def _upsert_double_materiality(cur, row):
    cur.execute(
        """INSERT INTO csrd_double_materiality
           (entity_id, impact_materiality, financial_materiality, assessment_date,
            key_impacts, key_dependencies, status)
           VALUES (%s, %s::json, %s::json, %s::date, %s, %s, %s)
           ON CONFLICT (entity_id) DO UPDATE SET
             impact_materiality = EXCLUDED.impact_materiality,
             financial_materiality = EXCLUDED.financial_materiality,
             assessment_date = EXCLUDED.assessment_date,
             key_impacts = EXCLUDED.key_impacts,
             key_dependencies = EXCLUDED.key_dependencies,
             status = EXCLUDED.status""",
        row,
    )


def main():
    conn = psycopg.connect(DB)
    cur = conn.cursor()

    for row in CSRD_ENTITY_REPORTS:
        _upsert_report(cur, row)

    for row in CSRD_ESG_DATA_POINTS:
        _upsert_esg_data_point(cur, row)

    for row in CSRD_ES:
        _upsert_ess(cur, row)

    for row in CSRD_DOUBLE_MATERIALITY:
        _upsert_double_materiality(cur, row)

    conn.commit()
    total = len(CSRD_ENTITY_REPORTS) + len(CSRD_ESG_DATA_POINTS) + len(CSRD_ES) + len(CSRD_DOUBLE_MATERIALITY)
    print(f"OK: {total} registros CSRD insertados ({len(CSRD_ENTITY_REPORTS)} reports, {len(CSRD_ESG_DATA_POINTS)} ESG data points, {len(CSRD_ES)} ES standards, {len(CSRD_DOUBLE_MATERIALITY)} double materiality)")
    conn.close()


if __name__ == "__main__":
    main()
