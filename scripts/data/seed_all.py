#!/usr/bin/env python
"""Unified seed runner for local development.

Fixes all seed scripts that use 'postgres:5432' (Docker hostname)
to use 'localhost:5434' (local port mapping).

Usage:
    python scripts/data/seed_all.py
"""

import importlib.util
import os
import re
import sys

DB_URL = "postgresql://esdata:esdata_dev@localhost:5434/esdata"
SEED_DIR = os.path.join(os.path.dirname(__file__))
SEED_FILES = [
    "seed_modelos.py",
    "seed_tax_data.py",
    "seed_sfdr.py",
    "seed_csrd.py",
    "seed_aifmd.py",
    "seed_ucits.py",
    "seed_crd.py",
    "seed_emir.py",
    "seed_psd2.py",
    "seed_facta.py",
    "seed_internacional.py",
    "seed_iva_rates.py",
    "seed_irpf_brackets.py",
    "seed_ss_rates.py",
    "seed_fiscal_calendar.py",
    "seed_fiscal_indicators.py",
    "seed_calendario_fiscal.py",
    "seed_w8_forms.py",
    "seed_irs_modelos.py",
]


def patch_and_run(seed_filename):
    """Read seed file, patch DB URL, and execute it."""
    seed_path = os.path.join(SEED_DIR, seed_filename)
    if not os.path.exists(seed_path):
        print(f"  SKIP: {seed_filename} (file not found)")
        return False

    with open(seed_path, "r") as f:
        source = f.read()

    # Patch DB URL — preserve variable name (DB or DB_URL)
    patched = re.sub(
        r'(DB_URL|DB)\s*=\s*"[^"]*postgres[^"]*"',
        f'\\1 = "{DB_URL}"',
        source,
    )

    # Write to temp and import
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=SEED_DIR
    ) as tmp:
        tmp.write(patched)
        tmp_path = tmp.name

    try:
        spec = importlib.util.spec_from_file_location(
            f"seed_{seed_filename.replace('.py', '')}", tmp_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Run main function
        if hasattr(module, "main"):
            module.main()
        elif hasattr(module, "seed"):
            module.seed()
        else:
            print(f"  SKIP: {seed_filename} (no main() or seed() function)")
            return False

        print(f"  OK: {seed_filename}")
        return True
    except Exception as e:
        print(f"  FAIL: {seed_filename} — {e}")
        return False
    finally:
        os.unlink(tmp_path)


def main():
    print(f"Seeding database: {DB_URL}")
    print(f"Seeds to run: {len(SEED_FILES)}")
    print("=" * 60)

    success = 0
    failed = 0

    for seed_file in SEED_FILES:
        if patch_and_run(seed_file):
            success += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Done: {success} succeeded, {failed} failed/skipped")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
