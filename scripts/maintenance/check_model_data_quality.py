#!/usr/bin/env python
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIC_PATHS = [
    ROOT / "scripts" / "seed-modelos.py",
    ROOT / "scripts" / "seed-modelos-v2.py",
    ROOT / "scripts" / "data" / "seed_modelo_articulo.py",
]
CANONICAL_AEAT_HOST = "sede.agenciatributaria.gob.es"
CANONICAL_BOE_HOST = "www.boe.es"
SUSPICIOUS_NORMA_VALUES = {
    "IRPF",
    "IS",
    "IVA",
    "OP.347",
    "FACTA",
    "IVA.A",
    "IRPF.T",
    "DAC2",
    "SII",
    "BIEN.EX",
    "PROV.NR",
}
URL_RE = re.compile(r"https?://[^\s'\"`]+")


@dataclass
class Finding:
    check_id: str
    severity: str
    location: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgres://"):
        return "postgresql+psycopg://" + db_url.removeprefix("postgres://")
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + db_url.removeprefix("postgresql://")
    return db_url


def classify_url_host(raw_url: str) -> str | None:
    parsed = urlparse(raw_url)
    if not parsed.hostname:
        return None
    return parsed.hostname.lower()


def validate_canonical_host(raw_url: str, allowed_hosts: set[str]) -> str | None:
    cleaned_url = raw_url.strip()
    if cleaned_url.startswith("http://"):
        return "http_url"

    host = classify_url_host(cleaned_url)
    if host is None or host not in allowed_hosts:
        return "non_canonical_host"

    return None


def _finding_from_url_issue(
    check_scope: str,
    location: str,
    raw_url: str,
    issue: str,
    message_prefix: str,
) -> Finding:
    suffix = "http_url" if issue == "http_url" else "non_canonical_host"
    separator = "_" if check_scope.startswith("db.") else "."

    if issue == "http_url":
        return Finding(
            check_id=f"{check_scope}{separator}{suffix}",
            severity="high",
            location=location,
            message=f"{message_prefix}: {raw_url}",
        )

    return Finding(
        check_id=f"{check_scope}{separator}{suffix}",
        severity="high",
        location=location,
        message=f"{message_prefix}: {raw_url}",
    )


def _find_seed_modelo_articulo_url_gaps(path: Path, content: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        module = ast.parse(content, filename=str(path))
    except SyntaxError:
        return findings

    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue

        if not any(isinstance(target, ast.Name) and target.id == "MAPPINGS" for target in node.targets):
            continue

        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return findings

        for entry in node.value.elts:
            if not isinstance(entry, (ast.Tuple, ast.List)) or len(entry.elts) < 7:
                continue

            url_value = entry.elts[6]
            if isinstance(url_value, ast.Constant) and url_value.value in (None, ""):
                findings.append(
                    Finding(
                        check_id="static.missing_url_fuente",
                        severity="high",
                        location=f"{path}:{entry.lineno}",
                        message="seed_modelo_articulo mapping is missing url_fuente",
                    )
                )

        return findings

    return findings


def find_static_url_issues(path: Path) -> list[dict[str, str]]:
    findings: list[Finding] = []
    content = path.read_text(encoding="utf-8")

    for line_number, line in enumerate(content.splitlines(), start=1):
        for raw_url in URL_RE.findall(line):
            issue = validate_canonical_host(raw_url, {CANONICAL_AEAT_HOST, CANONICAL_BOE_HOST})
            if issue is None:
                continue

            findings.append(
                _finding_from_url_issue(
                    check_scope="static",
                    location=f"{path}:{line_number}",
                    raw_url=raw_url,
                    issue=issue,
                    message_prefix="Model source URL failed canonical host validation",
                )
            )

    findings.extend(_find_seed_modelo_articulo_url_gaps(path, content))
    return [finding.to_dict() for finding in findings]


def _append_url_host_finding(
    findings: list[Finding],
    table: str,
    key: str,
    column: str,
    raw_url: str | None,
    allowed_hosts: set[str],
) -> None:
    if raw_url is None:
        return

    cleaned_url = str(raw_url).strip()
    if not cleaned_url:
        return

    issue = validate_canonical_host(cleaned_url, allowed_hosts)
    if issue is None:
        return

    findings.append(
        _finding_from_url_issue(
            check_scope=f"db.{table}",
            location=f"{table}:{key}",
            raw_url=cleaned_url,
            issue=issue,
            message_prefix=f"URL in {table}.{column} failed canonical host validation",
        )
    )


def _find_modelo_articulo_issues(conn, findings: list[Finding]) -> None:
    weak_rows = conn.execute(
        text(
            """
            SELECT modelo_id, norma, numero, metodo_enlace, confianza_enlace, url_fuente
            FROM modelo_articulo
            WHERE COALESCE(TRIM(url_fuente), '') = ''
               OR COALESCE(metodo_enlace, '') != 'manual_official'
               OR confianza_enlace IS NULL
               OR confianza_enlace != 1.0
            """
        )
    ).mappings()

    findings.extend(
        Finding(
            check_id="db.modelo_articulo_weak_provenance",
            severity="high",
            location=(
                "modelo_articulo:"
                f"modelo_id={row['modelo_id']},norma={row.get('norma')},numero={row.get('numero')}"
            ),
            message="modelo_articulo row does not meet the strong provenance contract",
        )
        for row in weak_rows
    )

    suspicious_params = {
        f"norma_{index}": value
        for index, value in enumerate(sorted(SUSPICIOUS_NORMA_VALUES))
    }
    suspicious_placeholders = ", ".join(f":{name}" for name in suspicious_params)
    suspicious_rows = conn.execute(
        text(
            f"""
            SELECT modelo_id, norma, numero
            FROM modelo_articulo
            WHERE norma IN ({suspicious_placeholders})
            """
        ),
        suspicious_params,
    ).mappings()

    findings.extend(
        Finding(
            check_id="db.modelo_articulo_suspicious_norma",
            severity="medium",
            location=(
                "modelo_articulo:"
                f"modelo_id={row['modelo_id']},norma={row['norma']},numero={row.get('numero')}"
            ),
            message=f"Suspicious pseudo-norma value in modelo_articulo.norma: {row['norma']}",
        )
        for row in suspicious_rows
    )

    host_rows = conn.execute(
        text(
            """
            SELECT modelo_id, articulo_id, norma, numero, url_fuente
            FROM modelo_articulo
            WHERE COALESCE(TRIM(url_fuente), '') != ''
            """
        )
    ).mappings()

    for row in host_rows:
        key = (
            f"modelo_id={row['modelo_id']},articulo_id={row.get('articulo_id')},"
            f"norma={row.get('norma')},numero={row.get('numero')}"
        )
        _append_url_host_finding(
            findings,
            table="modelo_articulo",
            key=key,
            column="url_fuente",
            raw_url=row.get("url_fuente"),
            allowed_hosts={CANONICAL_AEAT_HOST, CANONICAL_BOE_HOST},
        )


def _find_operativa_issues(conn, findings: list[Finding]) -> None:
    operativa_rows = conn.execute(
        text(
            """
            SELECT campana_id, origen_metadato, estado_metadato
            FROM modelo_campana_operativa
            WHERE (origen_metadato IN ('seed_curado', 'manual_curado') AND estado_metadato IN ('borrador', 'inferido'))
               OR (origen_metadato = 'worker_derivado' AND estado_metadato = 'curado')
            """
        )
    ).mappings()

    findings.extend(
        Finding(
            check_id="db.operativa_curated_state_conflict",
            severity="high",
            location=f"modelo_campana_operativa:campana_id={row['campana_id']}",
            message=(
                "modelo_campana_operativa has inconsistent curated provenance/state "
                f"({row['origen_metadato']} / {row['estado_metadato']})"
            ),
        )
        for row in operativa_rows
    )


def _find_db_url_host_issues(conn, findings: list[Finding]) -> None:
    aeat_rows = conn.execute(
        text(
            """
            SELECT id, codigo, url_info
            FROM aeat_modelo
            WHERE COALESCE(TRIM(url_info), '') != ''
            """
        )
    ).mappings()
    for row in aeat_rows:
        _append_url_host_finding(
            findings,
            table="aeat_modelo",
            key=f"id={row['id']},codigo={row['codigo']}",
            column="url_info",
            raw_url=row.get("url_info"),
            allowed_hosts={CANONICAL_AEAT_HOST},
        )

    campana_rows = conn.execute(
        text(
            """
            SELECT id, modelo_id, campana, url_instrucciones, url_normativa, url_formato
            FROM modelo_campana
            """
        )
    ).mappings()
    for row in campana_rows:
        key = f"id={row['id']},modelo_id={row['modelo_id']},campana={row['campana']}"
        _append_url_host_finding(
            findings,
            table="modelo_campana",
            key=key,
            column="url_instrucciones",
            raw_url=row.get("url_instrucciones"),
            allowed_hosts={CANONICAL_AEAT_HOST},
        )
        _append_url_host_finding(
            findings,
            table="modelo_campana",
            key=key,
            column="url_normativa",
            raw_url=row.get("url_normativa"),
            allowed_hosts={CANONICAL_AEAT_HOST, CANONICAL_BOE_HOST},
        )
        _append_url_host_finding(
            findings,
            table="modelo_campana",
            key=key,
            column="url_formato",
            raw_url=row.get("url_formato"),
            allowed_hosts={CANONICAL_AEAT_HOST},
        )

    normativa_rows = conn.execute(
        text(
            """
            SELECT id, modelo_id, boe_id, url_boe
            FROM modelo_normativa
            WHERE COALESCE(TRIM(url_boe), '') != ''
            """
        )
    ).mappings()
    for row in normativa_rows:
        _append_url_host_finding(
            findings,
            table="modelo_normativa",
            key=f"id={row['id']},modelo_id={row['modelo_id']},boe_id={row.get('boe_id')}",
            column="url_boe",
            raw_url=row.get("url_boe"),
            allowed_hosts={CANONICAL_BOE_HOST},
        )


def find_db_issues(db_url: str) -> list[dict[str, str]]:
    engine = create_engine(normalize_db_url(db_url), future=True)
    findings: list[Finding] = []

    try:
        with engine.connect() as conn:
            _find_db_url_host_issues(conn, findings)
            _find_modelo_articulo_issues(conn, findings)
            _find_operativa_issues(conn, findings)
    finally:
        engine.dispose()

    return [finding.to_dict() for finding in findings]


def run(
    static_paths: list[Path] | None = None,
    db_url: str | None = None,
    static_only: bool = False,
    db_only: bool = False,
) -> tuple[int, list[dict[str, str]]]:
    if static_only and db_only:
        return 2, []

    findings: list[dict[str, str]] = []
    selected_static_paths = DEFAULT_STATIC_PATHS if static_paths is None else static_paths

    if not db_only:
        for path in selected_static_paths:
            findings.extend(find_static_url_issues(path))

    if static_only:
        return (1 if findings else 0), findings

    resolved_db_url = db_url or os.getenv("DATABASE_URL")
    if not resolved_db_url:
        return 2, findings

    findings.extend(find_db_issues(resolved_db_url))
    return (1 if findings else 0), findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check model data quality guardrails")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON")
    parser.add_argument("--db-url", help="Override DATABASE_URL")
    parser.add_argument("--static-only", action="store_true", help="Run only static checks")
    parser.add_argument("--db-only", action="store_true", help="Run only DB checks")
    args = parser.parse_args()

    exit_code, findings = run(
        db_url=args.db_url,
        static_only=args.static_only,
        db_only=args.db_only,
    )

    if args.json:
        print(
            json.dumps(
                {"exit_code": exit_code, "total": len(findings), "findings": findings},
                indent=2,
                ensure_ascii=True,
            )
        )
        return exit_code

    if exit_code == 2:
        if args.static_only and args.db_only:
            print("MODEL DATA QUALITY CHECK FAILED: --static-only and --db-only are mutually exclusive", file=sys.stderr)
        else:
            print("MODEL DATA QUALITY CHECK FAILED: DATABASE_URL is not set", file=sys.stderr)
        return exit_code

    if findings:
        print("MODEL DATA QUALITY CHECK FAILED", file=sys.stderr)
        for finding in findings:
            print(
                f"- [{finding['severity']}] {finding['check_id']} {finding['location']}: {finding['message']}",
                file=sys.stderr,
            )
        return exit_code

    print("Model data quality OK")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
