#!/usr/bin/env python
"""Secrets audit — escanea el repositorio buscando credenciales expuestas.

Busca en todo el codigo fuentes de claves API, passwords, tokens JWT,
certificados y cualquier string que parezca secreto.

Uso:
    python scripts/secrets_audit.py          # modo normal
    python scripts/secrets_audit.py --fix    # marcar lineas problematicas como TODO
    python scripts/secrets_audit.py --json   # salida JSON para CI
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import List


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    file: str
    line: int
    pattern: str
    severity: str
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)


# Patrones de busqueda de secretos
PATTERNS: List[tuple] = [
    # AWS
    (
        r"AKIA[0-9A-Z]{16}",
        "AWS Access Key ID",
        Severity.HIGH,
        "Clave de acceso AWS expuesta",
        "Usar IAM roles o AWS Secrets Manager",
    ),
    (
        r"aws_secret_access_key\s*=\s*['\"][^'\"]+['\"]",
        "AWS Secret Key",
        Severity.HIGH,
        "Clave secreta AWS en codigo",
        "Usar IAM roles o AWS Secrets Manager",
    ),
    # GCP
    (
        r"AIza[0-9A-Za-z\\-_]{35}",
        "GCP API Key",
        Severity.HIGH,
        "Clave API de Google Cloud expuesta",
        "Usar Workload Identity o Secret Manager",
    ),
    (
        r"ya29\\.[A-Za-z0-9\\-_]+",
        "GCP OAuth Token",
        Severity.HIGH,
        "Token OAuth de Google expuesto",
        "Usar Service Account credentials",
    ),
    # Azure
    (
        r"msiam_account_[0-9a-f]{32}",
        "Azure Service Principal",
        Severity.HIGH,
        "Credenciales Azure expuestas",
        "Usar Managed Identity",
    ),
    # PostgreSQL
    (
        r"(?i)(postgres|postgresql|psql)://[^:]+:[^@]+@[^/]+",
        "DB Connection String",
        Severity.HIGH,
        "Cadena de conexion con password en codigo",
        "Usar variable de entorno DATABASE_URL",
    ),
    # JWT
    (
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "JWT Token",
        Severity.HIGH,
        "Token JWT expuesto en codigo",
        "Nunca hardcodear tokens JWT",
    ),
    # GitHub
    (
        r"ghp_[A-Za-z0-9]{36}",
        "GitHub Personal Access Token",
        Severity.HIGH,
        "Token de acceso personal de GitHub expuesto",
        "Usar GitHub Apps o OIDC",
    ),
    (
        r"github_pat_[A-Za-z0-9_]{36,}",
        "GitHub PAT (App)",
        Severity.HIGH,
        "GitHub Personal Access Token expuesto",
        "Usar GitHub Apps o OIDC",
    ),
    # Slack
    (
        r"xoxb-[0-9]+-[A-Za-z0-9]+",
        "Slack Bot Token",
        Severity.HIGH,
        "Token de Slack expuesto",
        "Usar Slack App credentials via env vars",
    ),
    (
        r"xoxp-[0-9]+-[A-Za-z0-9]+",
        "Slack User Token",
        Severity.HIGH,
        "Token de usuario de Slack expuesto",
        "Usar Slack App credentials via env vars",
    ),
    # SendGrid
    (
        r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}",
        "SendGrid API Key",
        Severity.HIGH,
        "Clave API de SendGrid expuesta",
        "Usar variable de entorno SENDGRID_API_KEY",
    ),
    # Stripe
    (
        r"sk_live_[0-9a-zA-Z]{24,}",
        "Stripe Live Secret Key",
        Severity.HIGH,
        "Clave secreta de Stripe en codigo",
        "Usar variable de entorno STRIPE_SECRET_KEY",
    ),
    (
        r"rk_live_[0-9a-zA-Z]{24,}",
        "Stripe Live Restricted Key",
        Severity.HIGH,
        "Clave restringida de Stripe en codigo",
        "Usar variable de entorno STRIPE_SECRET_KEY",
    ),
    # Twilio
    (
        r"SK[0-9a-fA-F]{32}",
        "Twilio Account SID",
        Severity.HIGH,
        "SID de cuenta Twilio expuesto",
        "Usar variable de entorno TWILIO_ACCOUNT_SID",
    ),
    # Heroku
    (
        r"heroku\s*[=:]\s*[0-9a-f-]{36}",
        "Heroku API Key",
        Severity.MEDIUM,
        "Clave de Heroku en codigo",
        "Usar variable de entorno HEROKU_API_KEY",
    ),
    # Generic passwords
    (
        r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]",
        "Hardcoded Password",
        Severity.HIGH,
        "Password hardcodeado en codigo",
        "Usar variable de entorno o secrets manager",
    ),
    # Generic API keys
    (
        r"(?i)(api_key|apikey|api_secret)\s*[=:]\s*['\"][^'\"]{16,}['\"]",
        "Hardcoded API Key",
        Severity.HIGH,
        "API Key hardcodeada en codigo",
        "Usar variable de entorno",
    ),
    # Generic secrets
    (
        r"(?i)(secret|token|auth)\s*[=:]\s*['\"][^'\"]{16,}['\"]",
        "Hardcoded Secret",
        Severity.MEDIUM,
        "Secret hardcodeado en codigo",
        "Usar variable de entorno o secrets manager",
    ),
    # Private keys
    (
        r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----",
        "Private Key",
        Severity.HIGH,
        "Clave privada en codigo",
        "Usar archivo de clave protegido o vault",
    ),
    # Base64 encoded secrets (long strings that look like encoded data)
    (
        r"(?i)(password|secret|key|token)\s*=\s*['\"]base64[:(]\s*['\"]?[A-Za-z0-9+/]{40,}['\"]?",
        "Encoded Secret",
        Severity.MEDIUM,
        "Secreto codificado en codigo",
        "Usar variable de entorno",
    ),
    # Datadog
    (
        r"DD_API_KEY\s*=\s*[A-Fa-f0-9]{32,64}",
        "Datadog API Key",
        Severity.MEDIUM,
        "Clave de Datadog en codigo",
        "Usar variable de entorno DD_API_KEY",
    ),
    # Sentry
    (
        r"sentry.*=\s*['\"]https://[a-f0-9]+@.*sentry\.io['\"]",
        "Sentry DSN",
        Severity.MEDIUM,
        "Sentry DSN en codigo (puede revelar datos internos)",
        "Usar variable de entorno SENTRY_DSN",
    ),
    # Algolia
    (
        r"[a-f0-9]{32}-[a-f0-9]{8}-[a-f0-9]{8}",
        "Algolia Admin Key?",
        Severity.LOW,
        "Posible clave de Algolia",
        "Verificar si es un admin key y mover a env var",
    ),
]

# Archivos a excluir del escaneo
EXCLUDE_PATTERNS = (
    ".git/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.egg-info/",
    ".venv/",
    "venv/",
    "node_modules/",
    ".pytest_cache/",
    "*.log",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.lock",
    "*.lockb",
    "alembic/",
    "migrations/",
    "tests/",
    "test_",
    "conftest.py",
    ".tox/",
    ".ruff_cache/",
    "htmlcov/",
    "docs/archive/",
    "docs/superpowers/",
    ".agents/",
    "scripts/tests/.tmp_secrets_audit/",
)

PLACEHOLDER_DB_URL_RE = re.compile(
    r"(?i)(?:postgres|postgresql|psql)://"
    r"(?:esdata|dummy|user):(?:esdata_dev|esdata_test|testpass|dummy|pass|password)@"
    r"(?:localhost|postgres|host)(?::\d+)?/[-_a-z0-9]+"
)


def is_known_placeholder(line: str, pattern_name: str) -> bool:
    """Allow documented local-only fixture DSNs while still flagging real hosts."""
    if pattern_name != "DB Connection String":
        return False
    return bool(PLACEHOLDER_DB_URL_RE.search(line))


def should_skip(path: Path) -> bool:
    """Determinar si un archivo debe ser excluido del escaneo."""
    str_path = path.as_posix()
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*."):
            if path.suffix == pattern:
                return True
        elif pattern.endswith("/"):
            if pattern in str_path:
                return True
    return False


def scan_file(filepath: Path) -> List[Finding]:
    """Escanear un archivo en busca de patrones de secretos."""
    findings: List[Finding] = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return findings

    lines = content.splitlines()
    for i, line in enumerate(lines, start=1):
        # Saltar lineas vacias y comentarios largos
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for pattern, name, severity, description, suggestion in PATTERNS:
            if re.search(pattern, line):
                if is_known_placeholder(line, name):
                    continue
                try:
                    finding_file = str(filepath.relative_to(Path.cwd()))
                except ValueError:
                    finding_file = str(filepath)
                findings.append(
                    Finding(
                        file=finding_file,
                        line=i,
                        pattern=name,
                        severity=severity.value,
                        description=description,
                        suggestion=suggestion,
                    )
                )
    return findings


def scan_directory(root: Path) -> List[Finding]:
    """Escanear un directorio completo."""
    all_findings: List[Finding] = []
    for filepath in sorted(root.rglob("*")):
        if filepath.is_file() and should_skip(filepath):
            continue
        findings = scan_file(filepath)
        all_findings.extend(findings)
    return all_findings


def deduplicate(findings: List[Finding]) -> List[Finding]:
    """Eliminar duplicados basados en archivo + linea + patron."""
    seen = set()
    unique = []
    for f in findings:
        key = (f.file, f.line, f.pattern)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def print_report(findings: List[Finding]) -> None:
    """Imprimir reporte de hallazgos en formato legible."""
    if not findings:
        print("No se encontraron secretos expuestos.")
        return

    # Contar por severidad
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    print(f"\n{'=' * 70}")
    print(f"SECRETS AUDIT — {len(findings)} hallazgo(s) encontrado(s)")
    print(f"{'=' * 70}")

    for sev in ["high", "medium", "low", "info"]:
        count = counts.get(sev, 0)
        if count > 0:
            print(f"\n{sev.upper()}: {count}")

    for f in findings:
        print(f"\n  {f.file}:{f.line} [{f.severity.upper()}]")
        print(f"     Patron: {f.pattern}")
        print(f"     {f.description}")
        print(f"     Sugerencia: {f.suggestion}")

    print(f"\n{'=' * 70}")
    total_high = counts.get("high", 0)
    if total_high > 0:
        print(f"{total_high} hallazgo(s) CRITICO(S) — deben resolverse antes de merge")
    else:
        print("No hay hallazgos criticos.")
    print(f"{'=' * 70}")


def main() -> int:
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Secrets audit for esdata repo")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} no es un directorio valido", file=sys.stderr)
        return 1

    findings = scan_directory(root)
    findings = deduplicate(findings)

    if args.json:
        output = {
            "total": len(findings),
            "by_severity": {},
            "findings": [f.to_dict() for f in findings],
        }
        for f in findings:
            output["by_severity"][f.severity] = output["by_severity"].get(f.severity, 0) + 1
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_report(findings)

    # Exit code: 0 = ok, 1 = critical findings
    has_high = any(f.severity == "high" for f in findings)
    return 1 if has_high else 0


if __name__ == "__main__":
    sys.exit(main())
