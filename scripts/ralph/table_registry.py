#!/usr/bin/env python
"""Build and verify the Ralph local table remediation registry.

This script intentionally reads local Docker Postgres. It is a local pre-VPS
gate helper; it must not connect to the VPS.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DRAFT = ROOT / "scripts" / "ralph" / "table-remediation-registry-draft.md"
DEFAULT_JSON = ROOT / "scripts" / "ralph" / "table-remediation-registry.json"
ALLOWED_CLASSIFICATIONS = {
    "populated",
    "blocker",
    "derived_blocker",
    "workflow_empty",
    "allowed_empty",
    "configured_but_unavailable",
}
ALLOWED_URL_DOMAINS = {
    "aeat.es",
    "agenciatributaria.gob.es",
    "boe.es",
    "eur-lex.europa.eu",
    "europa.eu",
    "aepd.es",
    "hacienda.gob.es",
    "bde.es",
    "bancodeespana.es",
    "cnmv.es",
    "sepblac.es",
    "poderjudicial.es",
    "infosubvenciones.es",
    "treasury.gov",
    "eba.europa.eu",
    "esma.europa.eu",
    "efrag.org",
    "ifrs.org",
    "epc-cep.eu",
    "eiopa.europa.eu",
    "irs.gov",
    "oecd.org",
}

POSTGRES_CONTAINER_CANDIDATES = (
    "esdata-postgres-1",
    "deploy-postgres-1",
)


@dataclass(frozen=True)
class DraftEntry:
    table: str
    classification: str
    action: str
    domain: str


def _run_psql(sql: str) -> str:
    container = os.getenv("ESDATA_POSTGRES_CONTAINER")
    if not container:
        for candidate in POSTGRES_CONTAINER_CANDIDATES:
            probe = subprocess.run(
                ["docker", "inspect", candidate],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if probe.returncode == 0:
                container = candidate
                break
    if not container:
        container = POSTGRES_CONTAINER_CANDIDATES[0]
    command = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        "esdata",
        "-d",
        "esdata",
        "-t",
        "-A",
        "-F",
        "\t",
        "-c",
        sql,
    ]
    return subprocess.check_output(command, cwd=ROOT, text=True)


def load_table_counts() -> dict[str, int]:
    sql = """
    SELECT relname,
           (xpath('/row/c/text()', query_to_xml(
                format('select count(*) c from %I.%I', schemaname, relname),
                false, true, ''
           )))[1]::text::bigint AS row_count
    FROM pg_stat_user_tables
    ORDER BY relname;
    """
    rows: dict[str, int] = {}
    for line in _run_psql(sql).splitlines():
        if not line.strip() or "\t" not in line:
            continue
        table, count = line.split("\t", 1)
        rows[table] = int(count)
    return rows


def load_rls_status() -> dict[str, bool]:
    sql = """
    SELECT relname, relrowsecurity
    FROM pg_class
    WHERE relnamespace = 'public'::regnamespace
      AND relkind = 'r'
    ORDER BY relname;
    """
    rows: dict[str, bool] = {}
    for line in _run_psql(sql).splitlines():
        if not line.strip() or "\t" not in line:
            continue
        table, enabled = line.split("\t", 1)
        rows[table] = enabled == "t"
    return rows


def load_url_columns() -> list[tuple[str, str]]:
    sql = """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND data_type IN ('text', 'character varying')
      AND column_name ILIKE '%url%'
    ORDER BY table_name, column_name;
    """
    columns: list[tuple[str, str]] = []
    for line in _run_psql(sql).splitlines():
        if not line.strip() or "\t" not in line:
            continue
        table, column = line.split("\t", 1)
        columns.append((table, column))
    return columns


def load_url_values(table: str, column: str) -> list[str]:
    safe_table = table.replace('"', '""')
    safe_column = column.replace('"', '""')
    sql = f"""
    SELECT DISTINCT "{safe_column}"::text
    FROM public."{safe_table}"
    WHERE "{safe_column}" IS NOT NULL
      AND btrim("{safe_column}"::text) <> ''
    LIMIT 500;
    """
    return [line.strip() for line in _run_psql(sql).splitlines() if line.strip()]


def parse_draft(path: Path) -> tuple[dict[str, DraftEntry], list[str]]:
    entries: dict[str, DraftEntry] = {}
    duplicates: list[str] = []
    domain = "Unscoped"
    row_re = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            domain = line[3:].strip()
            continue

        match = row_re.match(line)
        if not match:
            continue

        table, classification, action = match.groups()
        classification = classification.strip()
        if classification not in ALLOWED_CLASSIFICATIONS - {"populated"}:
            continue
        if table in entries:
            duplicates.append(table)
        entries[table] = DraftEntry(
            table=table,
            classification=classification,
            action=action.strip(),
            domain=domain,
        )
    return entries, duplicates


def infer_source_family(domain: str, action: str, classification: str) -> str:
    text = f"{domain} {action}".lower()
    if classification in {"allowed_empty", "workflow_empty"}:
        return "not_applicable_workflow_or_operational"
    mapping = [
        ("aifmd", "CNMV/ESMA official source"),
        ("aeat", "AEAT official portal"),
        ("boe", "BOE official text"),
        ("borme", "BORME official publication"),
        ("brrd", "EBA/Banco de Espana/BOE official source"),
        ("casp", "ESMA/CNMV/EUR-Lex official source"),
        ("consumer credit", "BOE/EUR-Lex/Banco de Espana official source"),
        ("crd", "EBA/Banco de Espana/BOE official source"),
        ("csrd", "EUR-Lex/EFRAG official source"),
        ("crypto", "ESMA/CNMV/EUR-Lex official source"),
        ("dac", "EUR-Lex/AEAT official source"),
        ("dgsfp", "DGSFP official source"),
        ("dora", "EUR-Lex/EBA/ESMA/EIOPA official source"),
        ("efrag", "EFRAG official source"),
        ("emir", "ESMA official source"),
        ("eur-lex", "EUR-Lex"),
        ("esma", "ESMA official source"),
        ("eba", "EBA official source"),
        ("epc", "EPC official source"),
        ("cnmv", "CNMV official source"),
        ("banco de espana", "Banco de Espana official source"),
        ("bde", "Banco de Espana official source"),
        ("fatca", "IRS official source"),
        ("sepblac", "SEPBLAC official source"),
        ("irs", "IRS official source"),
        ("oecd", "OECD official source"),
        ("idd", "DGSFP/CNMV/EUR-Lex official source"),
        ("ifrs", "IFRS official taxonomy"),
        ("livmc", "CNMV/BOE official source"),
        ("mar", "CNMV/EUR-Lex official source"),
        ("mica", "ESMA/CNMV/EUR-Lex official source"),
        ("mifid", "CNMV/EUR-Lex official source"),
        ("obligation", "BOE/EUR-Lex official source"),
        ("obligations", "BOE/EUR-Lex official source"),
        ("obligaciones", "BOE/EUR-Lex official source"),
        ("ownership", "BORME/official registry source"),
        ("pbc", "SEPBLAC/BOE official source"),
        ("pgc", "BOE official text"),
        ("priips", "CNMV/ESMA/EUR-Lex official source"),
        ("screening", "Official sanctions/screening list source"),
        ("sepa", "EPC official source"),
        ("sfdr", "EUR-Lex/CNMV official disclosure source"),
        ("solvency", "DGSFP/EIOPA official source"),
        ("transparency", "CNMV official source"),
        ("ubo", "BORME/official registry source"),
        ("ucits", "CNMV/ESMA official source"),
        ("wallet", "ESMA/CNMV/EUR-Lex official source"),
        ("xbrl", "CNMV/ESEF/ESMA official source"),
        ("esef", "ESEF official taxonomy"),
    ]
    found = [label for key, label in mapping if key in text]
    return "; ".join(dict.fromkeys(found)) if found else "official_source_required"


def infer_target_path(table: str, domain: str, classification: str) -> str:
    if classification in {"allowed_empty", "workflow_empty"}:
        return "gate_schema_rls_test"

    prefixes = [
        ("irnr_", "apps/workers/aeat_irnr.py"),
        ("modelo_", "apps/workers/aeat_models.py"),
        ("documento_", "apps/workers/document_decomposition.py"),
        ("pgc_", "apps/workers/pgc.py"),
        ("xbrl_", "apps/workers/xbrl.py"),
        ("irs_", "apps/workers/irs.py"),
        ("dac_", "apps/workers/dac_directives.py"),
        ("crypto_", "apps/workers/mica.py"),
        ("casp", "apps/workers/mica.py"),
        ("tokenized_asset", "apps/workers/mica.py"),
        ("wallet_custodian", "apps/workers/mica.py"),
        ("csrd_", "apps/workers/csrd.py"),
        ("sfdr_", "apps/workers/sfdr.py"),
        ("aifmd_", "apps/workers/aifmd.py"),
        ("ucits_", "apps/workers/ucits.py"),
        ("priips_", "apps/workers/priips.py"),
        ("solvency_ii_", "apps/workers/solvency_ii.py"),
        ("crd_", "apps/workers/crd_brrd_emir.py"),
        ("brrd_", "apps/workers/crd_brrd_emir.py"),
        ("emir_", "apps/workers/crd_brrd_emir.py"),
        ("dora_", "apps/workers/dora.py"),
        ("mifid_", "apps/workers/mifid.py"),
        ("mar_", "apps/workers/mar.py"),
        ("idd_", "apps/workers/idd.py"),
        ("livmc_", "apps/workers/livmc.py"),
        ("transparency_", "apps/workers/transparency.py"),
        ("psd2_", "apps/workers/psd2_eba.py"),
        ("sepa_", "apps/workers/sepa.py"),
        ("consumer_credit_", "apps/workers/consumer_credit.py"),
        ("beneficial_owner_", "apps/workers/ownership.py"),
        ("ownership_", "apps/workers/ownership.py"),
        ("ubo_", "apps/workers/ownership.py"),
        ("pbc_", "apps/workers/pbc.py"),
        ("fraud_", "apps/workers/fraud.py"),
        ("screening_", "apps/workers/screening.py"),
        ("suspicious_activity_", "apps/workers/pbc.py"),
        ("obligacion_", "apps/workers/obligaciones.py"),
        ("giin_registry", "apps/workers/giin.py"),
    ]
    for prefix, target in prefixes:
        if table == prefix or table.startswith(prefix):
            return target
    if "Document" in domain:
        return "apps/workers/document_decomposition.py"
    return "worker_or_script_required"


def build_registry(draft_path: Path) -> tuple[dict, list[str]]:
    draft_entries, duplicates = parse_draft(draft_path)
    counts = load_table_counts()
    rls = load_rls_status()

    entries = []
    errors = []

    for table in sorted(counts):
        row_count = counts[table]
        draft = draft_entries.get(table)
        if row_count > 0:
            classification = "populated"
            domain = "Already Populated"
            action = "Verify provenance and freshness in later gate stories."
        elif draft:
            classification = draft.classification
            domain = draft.domain
            action = draft.action
        else:
            classification = "unclassified"
            domain = "Unclassified"
            action = "Missing from table-remediation-registry-draft.md."
            errors.append(f"empty table is unclassified: {table}")

        source_family = infer_source_family(domain, action, classification)
        target_path = infer_target_path(table, domain, classification)
        if classification in {"blocker", "derived_blocker"}:
            if source_family == "official_source_required":
                errors.append(f"{table}: blocker lacks specific official source family")
            if target_path == "worker_or_script_required":
                errors.append(f"{table}: blocker lacks target worker/script")

        entries.append(
            {
                "table": table,
                "row_count": row_count,
                "classification": classification,
                "domain": domain,
                "official_source_family": source_family,
                "target_path": target_path,
                "action": action,
                "rls_enabled": rls.get(table, False),
                "verification_sql": f'SELECT count(*) FROM public."{table}";',
            }
        )

    for table in sorted(set(draft_entries) - set(counts)):
        errors.append(f"draft references non-existent table: {table}")
    for table in duplicates:
        errors.append(f"draft duplicates table: {table}")
    if len(entries) != len(counts):
        errors.append(f"registry row mismatch: entries={len(entries)} db_tables={len(counts)}")

    registry = {
        "project": "esdata",
        "generated_from": str(draft_path.relative_to(ROOT)),
        "scope": "local_pre_vps",
        "vps_target": "212.227.227.64",
        "rules": {
            "no_fake_seeds": True,
            "official_sources_required_for_compliance": True,
            "local_only": True,
        },
        "summary": {
            "total_tables": len(entries),
            "populated": sum(1 for item in entries if item["classification"] == "populated"),
            "blocker": sum(1 for item in entries if item["classification"] == "blocker"),
            "derived_blocker": sum(1 for item in entries if item["classification"] == "derived_blocker"),
            "workflow_empty": sum(1 for item in entries if item["classification"] == "workflow_empty"),
            "allowed_empty": sum(1 for item in entries if item["classification"] == "allowed_empty"),
            "unclassified": sum(1 for item in entries if item["classification"] == "unclassified"),
        },
        "tables": entries,
    }
    return registry, errors


def verify_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    seen: set[str] = set()
    for item in data.get("tables", []):
        table = item.get("table")
        if not table:
            errors.append("registry entry missing table")
            continue
        if table in seen:
            errors.append(f"registry duplicates table: {table}")
        seen.add(table)
        classification = item.get("classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{table}: invalid classification {classification!r}")
        if item.get("row_count", 0) == 0 and classification == "populated":
            errors.append(f"{table}: empty table classified as populated")
        if classification in {"blocker", "derived_blocker"}:
            if not item.get("official_source_family"):
                errors.append(f"{table}: missing official_source_family")
            if not item.get("target_path"):
                errors.append(f"{table}: missing target_path")

    counts = load_table_counts()
    missing = sorted(set(counts) - seen)
    extra = sorted(seen - set(counts))
    errors.extend(f"db table missing from registry: {table}" for table in missing)
    errors.extend(f"registry references non-existent table: {table}" for table in extra)
    return errors


def _url_allowed(value: str) -> bool:
    if value.startswith("/"):
        return True
    if not re.match(r"^https?://", value, re.IGNORECASE):
        return True
    return any(domain in value.lower() for domain in ALLOWED_URL_DOMAINS)


def run_gate(path: Path) -> tuple[dict, list[str]]:
    errors = verify_json(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    counts = load_table_counts()
    rls = load_rls_status()
    by_table = {item["table"]: item for item in data.get("tables", [])}
    blocker_tables: list[str] = []

    for table, item in sorted(by_table.items()):
        classification = item["classification"]
        row_count = counts.get(table, 0)
        if classification in {"blocker", "derived_blocker"} and row_count == 0:
            blocker_tables.append(table)
        if not rls.get(table, False):
            errors.append(f"{table}: RLS is not enabled")

    for table, column in load_url_columns():
        item = by_table.get(table)
        if not item or item["classification"] in {"allowed_empty", "workflow_empty"}:
            continue
        for value in load_url_values(table, column):
            if not _url_allowed(value):
                errors.append(f'{table}.{column}: non-official URL "{value[:160]}"')

    errors.extend(f"{table}: required table is empty" for table in blocker_tables)
    summary = {
        "total_tables": len(by_table),
        "blockers_empty": len(blocker_tables),
        "errors": len(errors),
    }
    return summary, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--write", type=Path, default=None)
    parser.add_argument("--verify-json", type=Path, default=None)
    parser.add_argument("--gate", type=Path, default=None)
    args = parser.parse_args()

    if args.gate:
        summary, errors = run_gate(args.gate)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(f"OK: local table gate passed for {args.gate}")
        return 0

    if args.verify_json:
        errors = verify_json(args.verify_json)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"OK: verified {args.verify_json}")
        return 0

    registry, errors = build_registry(args.draft)
    if args.write:
        args.write.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    writer = csv.DictWriter(sys.stdout, fieldnames=registry["summary"].keys())
    writer.writeheader()
    writer.writerow(registry["summary"])

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
