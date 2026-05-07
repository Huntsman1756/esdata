#!/usr/bin/env python
"""Inspect and manage the dead-letter queue in the esdata database.

Connects to the database using DATABASE_URL environment variable and
provides a CLI to view and resolve dead-letter entries.

Usage:
    python show_dead_letter_queue.py              # Show unacknowledged entries
    python show_dead_letter_queue.py --all         # Show all entries including resolved
    python show_dead_letter_queue.py --worker boe  # Filter by worker
    python show_dead_letter_queue.py resolve 123 "Fixed the issue"
    python show_dead_letter_queue.py counts        # Show counts per worker
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

DEFAULT_DATABASE_URL = "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata"


def get_engine():
    """Create engine from DATABASE_URL env var."""
    db_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return create_engine(db_url, future=True)


def ensure_connection(engine):
    """Test database connection, exit on failure."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as exc:
        print(f"Error: cannot connect to database: {exc}")
        print(f"  DATABASE_URL={os.environ.get('DATABASE_URL', '<not set>')}")
        sys.exit(1)


def fmt_value(val, max_len=60):
    """Format a value for display, truncating long strings."""
    if val is None:
        return "-"
    s = str(val)
    if len(s) > max_len:
        return s[:max_len - 3] + "..."
    return s


def show_dead_letters(engine, resolved=False, worker_name=None, limit=100):
    """Fetch and display dead-letter entries."""
    conditions = ["resolved = 0"] if not resolved else ["resolved = 1"]
    params = {}

    if worker_name:
        conditions.append("worker_name = :worker")
        params["worker"] = worker_name

    where = " AND ".join(conditions) if conditions else "1=1"

    with engine.begin() as conn:
        rows = conn.execute(
            text(f"""
                SELECT id, worker_name, entity_id, entity_type,
                       error_message, retry_count, max_retries,
                       first_failed_at, last_failed_at,
                       resolved_at, resolved_by, notes
                FROM sync_dead_letter
                WHERE {where}
                ORDER BY last_failed_at DESC
                LIMIT :limit
            """),
            {**params, "limit": limit},
        ).mappings()
        results = [dict(row) for row in rows]

    if not results:
        print("No entries found.")
        return results

    # Header
    print(f"{'ID':<6} {'Worker':<30} {'Entity':<20} {'Type':<15} {'Retries':<8} {'Last Failed':<22} {'Status'}")
    print("-" * 120)

    for row in results:
        retry_str = f"{row['retry_count']}/{row['max_retries']}"
        last_failed = row["last_failed_at"][:19] if row["last_failed_at"] else "-"
        status = "RESOLVED" if row["resolved"] else "UNACK"
        print(
            f"{row['id']:<6} "
            f"{row['worker_name']:<30} "
            f"{row['entity_id']:<20} "
            f"{row['entity_type']:<15} "
            f"{retry_str:<8} "
            f"{last_failed:<22} "
            f"{status}"
        )

    # Error preview for each
    print()
    for row in results:
        print(f"  [{row['id']}] {row['worker_name']} | {row['entity_id']} | {row['entity_type']}")
        print(f"    Error: {fmt_value(row['error_message'], 120)}")
        if row.get("notes"):
            print(f"    Notes: {row['notes']}")
        print()

    print(f"Total: {len(results)} entries (limit={limit})")
    return results


def show_counts(engine, resolved=False):
    """Show counts per worker and entity_type."""
    conditions = ["resolved = 0"] if not resolved else ["resolved = 1"]
    where = " AND ".join(conditions) if conditions else "1=1"

    with engine.begin() as conn:
        # Per worker
        rows = conn.execute(
            text(f"""
                SELECT worker_name, COUNT(*) as cnt
                FROM sync_dead_letter
                WHERE {where}
                GROUP BY worker_name
                ORDER BY cnt DESC
            """)
        ).mappings()
        worker_counts = [dict(r) for r in rows]

        # Per entity_type
        rows2 = conn.execute(
            text(f"""
                SELECT entity_type, COUNT(*) as cnt
                FROM sync_dead_letter
                WHERE {where}
                GROUP BY entity_type
                ORDER BY cnt DESC
            """)
        ).mappings()
        type_counts = [dict(r) for r in rows2]

        # Total
        total = conn.execute(
            text(f"SELECT COUNT(*) as cnt FROM sync_dead_letter WHERE {where}")
        ).scalar()

    print(f"Total {('all' if resolved else 'unacknowledged')} entries: {total}")
    print()

    print("Per worker:")
    print(f"  {'Worker':<30} {'Count':<10}")
    print(f"  {'-'*40}")
    for r in worker_counts:
        print(f"  {r['worker_name']:<30} {r['cnt']:<10}")

    print()
    print("Per entity type:")
    print(f"  {'Type':<20} {'Count':<10}")
    print(f"  {'-'*30}")
    for r in type_counts:
        print(f"  {r['entity_type']:<20} {r['cnt']:<10}")

    return worker_counts


def resolve_dead_letter(engine, dead_letter_id, reason):
    """Mark a dead-letter entry as resolved."""
    resolved_by = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    now = datetime.now(UTC).isoformat()

    with engine.begin() as conn:
        # Check if exists
        row = conn.execute(
            text("SELECT id, worker_name, entity_id, resolved FROM sync_dead_letter WHERE id = :id"),
            {"id": dead_letter_id},
        ).mappings().first()

        if not row:
            print(f"Error: dead-letter entry {dead_letter_id} not found.")
            return False

        if row["resolved"]:
            print(f"Warning: entry {dead_letter_id} is already resolved.")
            return False

        result = conn.execute(
            text("""
                UPDATE sync_dead_letter
                SET resolved = 1, resolved_at = :now, resolved_by = :resolved_by, notes = :notes
                WHERE id = :id AND resolved = 0
            """),
            {"id": dead_letter_id, "now": now, "resolved_by": resolved_by, "notes": reason},
        )

        if result.rowcount > 0:
            print(f"Resolved dead-letter entry {dead_letter_id}:")
            print(f"  Worker: {row['worker_name']}")
            print(f"  Entity: {row['entity_id']}")
            print(f"  Resolved by: {resolved_by}")
            print(f"  Notes: {reason}")
            return True
        else:
            print(f"Error: failed to resolve entry {dead_letter_id} (already resolved or not found).")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and manage the dead-letter queue"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Show all entries including resolved",
    )
    parser.add_argument(
        "--worker", type=str, default=None,
        help="Filter by worker name",
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Maximum entries to show (default: 100)",
    )
    parser.add_argument(
        "command", nargs="?",
        choices=["resolve", "counts"],
        help="Command: 'resolve <id> <reason>' or 'counts'",
    )
    parser.add_argument(
        "id", nargs="?",
        help="Dead-letter entry ID (for resolve command)",
    )
    parser.add_argument(
        "reason", nargs="?",
        help="Resolution reason (for resolve command)",
    )

    args = parser.parse_args()

    engine = get_engine()
    ensure_connection(engine)

    if args.command == "counts":
        show_counts(engine, resolved=args.all)
    elif args.command == "resolve":
        if not args.id:
            print("Error: resolve requires an ID")
            print("Usage: show_dead_letter_queue.py resolve <id> <reason>")
            sys.exit(1)
        if not args.reason:
            print("Error: resolve requires a reason")
            print("Usage: show_dead_letter_queue.py resolve <id> <reason>")
            sys.exit(1)
        success = resolve_dead_letter(engine, int(args.id), args.reason)
        sys.exit(0 if success else 1)
    else:
        show_dead_letters(engine, resolved=args.all, worker_name=args.worker, limit=args.limit)


if __name__ == "__main__":
    main()
