"""Worker para ingestion de datos CRD V/CRR, BRRD y EMIR.

Ingesta seed data para:
- crd_capital_position: posiciones de capital CRD/CRR
- crd_stress_test: pruebas de resistencia CRD
- brrd_bail_in: bail-in / MREL BRRD
- emir_trade_report: reportes de operaciones EMIR
- emir_clearing_member: clearing members EMIR
"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def seed_crd_capital_position(db: Session):
    """Seed CRD capital position records."""
    positions = [
        {
            "entity_id": 1,
            "reporting_date": date(2025, 9, 30),
            "cet1_ratio": 14.5,
            "tier1_ratio": 16.2,
            "total_capital_ratio": 18.7,
            "cet1_amount": 8500000000.00,
            "tier1_amount": 9500000000.00,
            "total_capital_amount": 10950000000.00,
            "leverage_ratio": 5.8,
            "risk_weighted_assets": 58600000000.00,
            "status": "filed",
        },
        {
            "entity_id": 2,
            "reporting_date": date(2025, 9, 30),
            "cet1_ratio": 13.2,
            "tier1_ratio": 15.1,
            "total_capital_ratio": 17.3,
            "cet1_amount": 4200000000.00,
            "tier1_amount": 4800000000.00,
            "total_capital_amount": 5500000000.00,
            "leverage_ratio": 4.9,
            "risk_weighted_assets": 32400000000.00,
            "status": "filed",
        },
        {
            "entity_id": 3,
            "reporting_date": date(2025, 6, 30),
            "cet1_ratio": 15.1,
            "tier1_ratio": 17.0,
            "total_capital_ratio": 19.4,
            "cet1_amount": 12300000000.00,
            "tier1_amount": 13800000000.00,
            "total_capital_amount": 15700000000.00,
            "leverage_ratio": 6.2,
            "risk_weighted_assets": 78900000000.00,
            "status": "filed",
        },
    ]

    for pos in positions:
        existing = db.execute(
            text(
                "SELECT id FROM crd_capital_position "
                "WHERE entity_id = :entity_id AND reporting_date = :reporting_date"
            ),
            {"entity_id": pos["entity_id"], "reporting_date": pos["reporting_date"]},
        ).fetchone()

        if existing:
            db.execute(
                text(
                    "UPDATE crd_capital_position SET "
                    "cet1_ratio=:cet1_ratio, tier1_ratio=:tier1_ratio, "
                    "total_capital_ratio=:total_capital_ratio, cet1_amount=:cet1_amount, "
                    "tier1_amount=:tier1_amount, total_capital_amount=:total_capital_amount, "
                    "leverage_ratio=:leverage_ratio, risk_weighted_assets=:risk_weighted_assets, "
                    "status=:status WHERE id = :id"
                ),
                {**pos, "id": existing[0]},
            )
        else:
            now = db.execute(text("SELECT now()")).scalar()
            db.execute(
                text(
                    "INSERT INTO crd_capital_position "
                    "(entity_id, reporting_date, cet1_ratio, tier1_ratio, total_capital_ratio, "
                    "cet1_amount, tier1_amount, total_capital_amount, leverage_ratio, "
                    "risk_weighted_assets, status, created_at) "
                    "VALUES (:entity_id, :reporting_date, :cet1_ratio, :tier1_ratio, "
                    ":total_capital_ratio, :cet1_amount, :tier1_amount, "
                    ":total_capital_amount, :leverage_ratio, :risk_weighted_assets, "
                    ":status, :created_at)"
                ),
                {**pos, "created_at": now},
            )

    db.commit()
    logger.info("Seeded %d CRD capital positions", len(positions))


def seed_crd_stress_test(db: Session):
    """Seed CRD stress test records."""
    tests = [
        {
            "entity_id": 1,
            "test_date": date(2025, 7, 15),
            "scenario_name": "ECB Joint EU-wide stress test 2025",
            "cet1_impact_pct": -2.8,
            "tier1_impact_pct": -2.5,
            "capital_ratio_post_test": 11.7,
            "competent_authority": "Banco de Espana",
            "status": "published",
        },
        {
            "entity_id": 2,
            "test_date": date(2025, 7, 15),
            "scenario_name": "ECB Joint EU-wide stress test 2025",
            "cet1_impact_pct": -3.1,
            "tier1_impact_pct": -2.9,
            "capital_ratio_post_test": 10.1,
            "competent_authority": "Banco de Espana",
            "status": "published",
        },
        {
            "entity_id": 3,
            "test_date": date(2025, 3, 10),
            "scenario_name": "Banco de Espana national stress test 2025",
            "cet1_impact_pct": -2.2,
            "tier1_impact_pct": -2.0,
            "capital_ratio_post_test": 12.9,
            "competent_authority": "Banco de Espana",
            "status": "published",
        },
    ]

    for test in tests:
        existing = db.execute(
            text(
                "SELECT id FROM crd_stress_test "
                "WHERE entity_id = :entity_id AND test_date = :test_date"
            ),
            {"entity_id": test["entity_id"], "test_date": test["test_date"]},
        ).fetchone()

        if existing:
            db.execute(
                text(
                    "UPDATE crd_stress_test SET "
                    "scenario_name=:scenario_name, cet1_impact_pct=:cet1_impact_pct, "
                    "tier1_impact_pct=:tier1_impact_pct, "
                    "capital_ratio_post_test=:capital_ratio_post_test, "
                    "competent_authority=:competent_authority, "
                    "status=:status WHERE id = :id"
                ),
                {**test, "id": existing[0]},
            )
        else:
            now = db.execute(text("SELECT now()")).scalar()
            db.execute(
                text(
                    "INSERT INTO crd_stress_test "
                    "(entity_id, test_date, scenario_name, cet1_impact_pct, tier1_impact_pct, "
                    "capital_ratio_post_test, competent_authority, status, created_at) "
                    "VALUES (:entity_id, :test_date, :scenario_name, :cet1_impact_pct, "
                    ":tier1_impact_pct, :capital_ratio_post_test, :competent_authority, "
                    ":status, :created_at)"
                ),
                {**test, "created_at": now},
            )

    db.commit()
    logger.info("Seeded %d CRD stress tests", len(tests))


def seed_brrd_bail_in(db: Session):
    """Seed BRRD bail-in / MREL records."""
    bail_ins = [
        {
            "entity_id": 1,
            "total_eligible_liabilities": 85000000000.00,
            "mrel_target_pct": 31.5,
            "mrel_compliance_pct": 32.1,
            "internal_mrel": 28.4,
            "resolution_status": "compliant",
            "status": "active",
        },
        {
            "entity_id": 2,
            "total_eligible_liabilities": 42000000000.00,
            "mrel_target_pct": 28.0,
            "mrel_compliance_pct": 27.5,
            "internal_mrel": 25.1,
            "resolution_status": "non_compliant",
            "status": "active",
        },
        {
            "entity_id": 3,
            "total_eligible_liabilities": 120000000000.00,
            "mrel_target_pct": 33.0,
            "mrel_compliance_pct": 34.2,
            "internal_mrel": 30.8,
            "resolution_status": "compliant",
            "status": "active",
        },
    ]

    for bi in bail_ins:
        existing = db.execute(
            text(
                "SELECT id FROM brrd_bail_in WHERE entity_id = :entity_id"
            ),
            {"entity_id": bi["entity_id"]},
        ).fetchone()

        if existing:
            db.execute(
                text(
                    "UPDATE brrd_bail_in SET "
                    "total_eligible_liabilities=:total_eligible_liabilities, "
                    "mrel_target_pct=:mrel_target_pct, mrel_compliance_pct=:mrel_compliance_pct, "
                    "internal_mrel=:internal_mrel, resolution_status=:resolution_status, "
                    "status=:status WHERE id = :id"
                ),
                {**bi, "id": existing[0]},
            )
        else:
            now = db.execute(text("SELECT now()")).scalar()
            db.execute(
                text(
                    "INSERT INTO brrd_bail_in "
                    "(entity_id, total_eligible_liabilities, mrel_target_pct, "
                    "mrel_compliance_pct, internal_mrel, resolution_status, status, created_at) "
                    "VALUES (:entity_id, :total_eligible_liabilities, :mrel_target_pct, "
                    ":mrel_compliance_pct, :internal_mrel, :resolution_status, "
                    ":status, :created_at)"
                ),
                {**bi, "created_at": now},
            )

    db.commit()
    logger.info("Seeded %d BRRD bail-in records", len(bail_ins))


def seed_emir_trade_report(db: Session):
    """Seed EMIR trade report records."""
    trades = [
        {
            "trade_id": "EMIR-2025-001-XYZ",
            "asset_class": "credit",
            "instrument_class": "CDS",
            "clearing_obligation_applied": True,
            "reporting_delay_days": 1,
            "counterparty_type": "financial",
            "status": "reported",
        },
        {
            "trade_id": "EMIR-2025-002-ABC",
            "asset_class": "interest-rate",
            "instrument_class": "IRS",
            "clearing_obligation_applied": True,
            "reporting_delay_days": 0,
            "counterparty_type": "financial",
            "status": "reported",
        },
        {
            "trade_id": "EMIR-2025-003-DEF",
            "asset_class": "equity",
            "instrument_class": "TRC",
            "clearing_obligation_applied": False,
            "reporting_delay_days": 2,
            "counterparty_type": "non-financial",
            "status": "reported",
        },
    ]

    for trade in trades:
        existing = db.execute(
            text(
                "SELECT id FROM emir_trade_report WHERE trade_id = :trade_id"
            ),
            {"trade_id": trade["trade_id"]},
        ).fetchone()

        if existing:
            db.execute(
                text(
                    "UPDATE emir_trade_report SET "
                    "asset_class=:asset_class, instrument_class=:instrument_class, "
                    "clearing_obligation_applied=:clearing_obligation_applied, "
                    "reporting_delay_days=:reporting_delay_days, "
                    "counterparty_type=:counterparty_type, "
                    "status=:status WHERE id = :id"
                ),
                {**trade, "id": existing[0]},
            )
        else:
            now = db.execute(text("SELECT now()")).scalar()
            db.execute(
                text(
                    "INSERT INTO emir_trade_report "
                    "(trade_id, asset_class, instrument_class, clearing_obligation_applied, "
                    "reporting_delay_days, counterparty_type, status, created_at) "
                    "VALUES (:trade_id, :asset_class, :instrument_class, "
                    ":clearing_obligation_applied, :reporting_delay_days, "
                    ":counterparty_type, :status, :created_at)"
                ),
                {**trade, "created_at": now},
            )

    db.commit()
    logger.info("Seeded %d EMIR trade reports", len(trades))


def seed_emir_clearing_member(db: Session):
    """Seed EMIR clearing member records."""
    members = [
        {
            "entity_id": 1,
            "emir_registration": "EMIR-CM-2024-00123",
            "clearing_type": "central",
            "status": "active",
        },
        {
            "entity_id": 2,
            "emir_registration": "EMIR-CM-2024-00456",
            "clearing_type": "otc",
            "status": "active",
        },
        {
            "entity_id": 3,
            "emir_registration": "EMIR-CM-2024-00789",
            "clearing_type": "central",
            "status": "active",
        },
    ]

    for member in members:
        existing = db.execute(
            text(
                "SELECT id FROM emir_clearing_member WHERE entity_id = :entity_id"
            ),
            {"entity_id": member["entity_id"]},
        ).fetchone()

        if existing:
            db.execute(
                text(
                    "UPDATE emir_clearing_member SET "
                    "emir_registration=:emir_registration, "
                    "clearing_type=:clearing_type, status=:status WHERE id = :id"
                ),
                {**member, "id": existing[0]},
            )
        else:
            now = db.execute(text("SELECT now()")).scalar()
            db.execute(
                text(
                    "INSERT INTO emir_clearing_member "
                    "(entity_id, emir_registration, clearing_type, status, created_at) "
                    "VALUES (:entity_id, :emir_registration, :clearing_type, "
                    ":status, :created_at)"
                ),
                {**member, "created_at": now},
            )

    db.commit()
    logger.info("Seeded %d EMIR clearing members", len(members))


def run(db: Session):
    """Run all CRD/BRRD/EMIR seed data ingestion."""
    seed_crd_capital_position(db)
    seed_crd_stress_test(db)
    seed_brrd_bail_in(db)
    seed_emir_trade_report(db)
    seed_emir_clearing_member(db)
    logger.info("CRD/BRRD/EMIR worker completed")
