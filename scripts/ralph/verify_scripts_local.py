"""Local Ralph gate for scripts and operational tooling.

The goal is classification, not optimistic execution. Data mutators and
deployment scripts are not run unless they expose a safe help/dry-run surface.
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

MUTATIVE_NAME_TOKENS = (
    "seed",
    "backfill",
    "ingest",
    "apply_schema",
    "fix_dates",
    "quick_backfill",
    "update_chunks",
)

SAFE_HELP_PROBES = {
    "scripts/maintenance/check_model_data_quality.py": ["--help"],
    "scripts/maintenance/integrate_dead_letter.py": ["--help"],
    "scripts/maintenance/secrets_audit.py": ["--help"],
    "scripts/maintenance/validate-cron-run.py": ["--help"],
    "scripts/maintenance/verify-doc-artifacts.py": ["--help"],
    "scripts/maintenance/verify-doc-contracts.py": ["--help"],
    "scripts/ops/export-gpt-openapi.py": ["--help"],
    "scripts/ops/smoke-check.py": ["--help"],
    "scripts/ops/worker_scheduler_guard.py": ["--help"],
    "scripts/ralph/table_registry.py": ["--help"],
    "scripts/ralph/verify_workers_local.py": ["--help"],
}

SAFE_EXEC_PROBES = {
    "scripts/maintenance/check_model_data_quality.py": [
        "--static-only",
        "--json",
    ],
    "scripts/maintenance/integrate_dead_letter.py": ["--dry-run"],
}


@dataclass
class ScriptRecord:
    path: str
    kind: str
    category: str
    status: str
    evidence: list[str]
    blocker: str | None = None


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def iter_script_files() -> Iterable[Path]:
    for path in sorted(SCRIPTS.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".py", ".ps1", ".sh", ".sql"}:
            yield path


def category_for(path: Path) -> str:
    parts = path.relative_to(SCRIPTS).parts
    if parts[0] == "tests":
        return "test"
    if parts[0] in {"maintenance", "ops", "ralph", "data", "dev", "eval"}:
        return parts[0]
    return "root"


def is_mutative(path: Path) -> bool:
    name = path.name.lower()
    rel_path = rel(path).lower()
    if path.suffix.lower() == ".sql":
        return True
    return any(token in name or f"/{token}" in rel_path for token in MUTATIVE_NAME_TOKENS)


def run_probe(path: Path, args: list[str]) -> tuple[bool, str]:
    cmd = [sys.executable, str(path), *args]
    env = os.environ.copy()
    env.setdefault("APP_ENV", "test")
    env.setdefault("ESDATA_API_KEY", "test-secret-key")
    env.setdefault("MCP_API_KEY", "test-mcp-key")
    env["PYTHONPATH"] = os.pathsep.join(
        str(ROOT / p) for p in ("apps", "apps/api", "apps/workers")
    )
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    output = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    first_line = output.splitlines()[0] if output else "no output"
    return proc.returncode == 0, f"`{' '.join(cmd)}` => exit {proc.returncode}: {first_line[:240]}"


def bash_path(path: Path) -> str:
    raw = str(path)
    if raw.startswith("G:\\"):
        return "/mnt/g/" + raw[3:].replace("\\", "/")
    return raw.replace("\\", "/")


def verify_syntax(path: Path) -> tuple[bool, str]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            return False, f"py_compile failed: {exc.msg}"
        return True, "py_compile OK"
    if suffix == ".ps1":
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$tokens=$null;$errors=$null;"
                f"[System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$tokens,[ref]$errors) > $null;"
                "if ($errors.Count) { $errors | ForEach-Object { $_.Message }; exit 1 }"
            ),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            return False, (proc.stdout or proc.stderr).strip()
        return True, "PowerShell parser OK"
    if suffix == ".sh":
        if not shutil.which("bash"):
            return False, "bash executable not found"
        proc = subprocess.run(
            ["bash", "-n", bash_path(path)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            return False, (proc.stdout or proc.stderr).strip()
        return True, "bash -n OK"
    if suffix == ".sql":
        return True, "SQL file readable; execution not attempted"
    return False, f"unsupported suffix {suffix}"


def build_record(path: Path, *, run_safe_probes: bool) -> ScriptRecord:
    relative = rel(path)
    category = category_for(path)
    syntax_ok, syntax_evidence = verify_syntax(path)
    evidence = [syntax_evidence]
    kind = path.suffix.lower().lstrip(".")

    if not syntax_ok:
        return ScriptRecord(relative, kind, category, "fail", evidence, syntax_evidence)

    if relative in SAFE_HELP_PROBES and run_safe_probes:
        ok, probe_evidence = run_probe(path, SAFE_HELP_PROBES[relative])
        evidence.append(probe_evidence)
        if not ok:
            return ScriptRecord(relative, kind, category, "fail", evidence, probe_evidence)

    if relative in SAFE_EXEC_PROBES and run_safe_probes:
        ok, probe_evidence = run_probe(path, SAFE_EXEC_PROBES[relative])
        evidence.append(probe_evidence)
        if not ok:
            return ScriptRecord(relative, kind, category, "fail", evidence, probe_evidence)

    if is_mutative(path):
        return ScriptRecord(
            relative,
            kind,
            category,
            "blocked_runtime",
            evidence,
            "Mutative data/schema script; not executed without explicit dry-run and official-source review.",
        )

    if category == "ops" and path.suffix.lower() in {".sh", ".ps1"}:
        return ScriptRecord(
            relative,
            kind,
            category,
            "blocked_runtime",
            evidence,
            "Operational/deployment script; syntax verified but not executed against local/VPS infrastructure.",
        )

    return ScriptRecord(relative, kind, category, "verified", evidence)


def summarize(records: list[ScriptRecord]) -> dict[str, int]:
    summary: dict[str, int] = {"total": len(records)}
    for record in records:
        summary[record.status] = summary.get(record.status, 0) + 1
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, help="Write JSON registry to this path")
    parser.add_argument("--verify-json", type=Path, help="Verify an existing JSON registry")
    parser.add_argument("--gate", type=Path, help="Fail if registry has unclassified or fail records")
    parser.add_argument("--run-safe-probes", action="store_true", help="Run allowlisted help/dry-run probes")
    args = parser.parse_args()

    if args.verify_json or args.gate:
        target = args.verify_json or args.gate
        data = json.loads(target.read_text(encoding="utf-8"))
        records = [ScriptRecord(**item) for item in data["records"]]
        live_paths = {rel(path) for path in iter_script_files()}
        registry_paths = {record.path for record in records}
        missing = sorted(live_paths - registry_paths)
        extra = sorted(registry_paths - live_paths)
        failures = [record.path for record in records if record.status == "fail"]
        if missing or extra or failures:
            print(json.dumps({"missing": missing, "extra": extra, "failures": failures}, indent=2))
            return 2
        print(f"OK: verified {target}")
        if args.gate:
            print(json.dumps(data["summary"], indent=2))
            print(f"OK: local script gate passed for {target}")
        return 0

    records = [build_record(path, run_safe_probes=args.run_safe_probes) for path in iter_script_files()]
    data = {
        "generated_by": rel(Path(__file__).resolve()),
        "scope": "local scripts under scripts/",
        "policy": "Syntax is required for every script. Runtime execution is blocked for mutative data/schema/deployment scripts unless a safe probe is allowlisted.",
        "summary": summarize(records),
        "records": [asdict(record) for record in records],
    }

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(",".join(str(data["summary"].get(key, 0)) for key in ("total", "verified", "blocked_runtime", "fail")))
    return 0 if data["summary"].get("fail", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
