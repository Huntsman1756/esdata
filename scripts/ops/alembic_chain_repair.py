#!/usr/bin/env python
"""Upgrade alembic chain in disposable DB to find runtime errors."""
import os
import sys
from sqlalchemy import create_engine, text
from alembic import command, config

DB_URL = "postgresql+psycopg2://testuser:testpass@127.0.0.1:54331/esdata_test"
PG_URL = "postgresql+psycopg2://testuser:testpass@127.0.0.1:54331/postgres"
ALEMBIC_CFG = "alembic.ini"

def main():
    # Recreate test DB
    print("=== Recreating test DB ===")
    engine = create_engine(PG_URL)
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        dbs = conn.execute(text("SELECT datname FROM pg_database WHERE datname = 'esdata_test'"))
        for db in dbs:
            conn.execute(text('DROP DATABASE "' + db.datname + '"'))
        conn.execute(text("CREATE DATABASE esdata_test"))
    print("Test DB ready")

    # Upgrade step by step
    alembic_cfg = config.Config(ALEMBIC_CFG)
    alembic_cfg.set_main_option("sqlalchemy.url", DB_URL)

    migrations = [
        "base",
        "20260424_0005_chunking_schema",
        "20260425_0006_eval_history",
        "20260425_0009_workflow_cases",
        "20260426_0012_screening",
        "20260426_0016_editorial_internal",
        "20260426_0017_playbooks_evidencia",
    ]

    for target in migrations:
        label = target if target != "base" else "base"
        print(f"\n=== Upgrading to {label} ===")
        try:
            if target == "base":
                command.stamp(alembic_cfg, target)
            else:
                command.upgrade(alembic_cfg, target)
            print(f"OK: {label}")
        except Exception as e:
            print(f"FAIL: {label}")
            print(f"Error: {e}")
            return False

    # Try to upgrade to head
    print("\n=== Upgrading to head ===")
    try:
        command.upgrade(alembic_cfg, "head")
        print("OK: head reached")
    except Exception as e:
        print(f"FAIL: head")
        print(f"Error: {e}")
        return False

    return True

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
