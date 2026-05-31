#!/usr/bin/env python
"""Static source-assurance gate for final v1 maintenance.

This gate blocks the most dangerous failure mode for this project: broad source
coverage claims that exceed the loaded, verified and fail-closed corpus.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PUBLIC_DOC_GLOBS = [
    "PROJECT_STATE.md",
    "RELEASE-CLOSEOUT.md",
    "docs/master-execution-roadmap.md",
    "docs/final-product-coverage-matrix.md",
    "docs/final-product-acceptance-plan.md",
    "docs/source-assurance-certification-20260531.md",
    "docs/manual-usuario/*.md",
    "docs/integrations/*.md",
    "docs/openapi-gpt*.json",
    "scripts/ops/export-gpt-openapi.py",
    "apps/api/routers/modelos.py",
]

DANGEROUS_PATTERNS = [
    re.compile(r"\bList all AEAT tax form models\b", re.IGNORECASE),
    re.compile(r"Lista todos los modelos AEAT disponibles", re.IGNORECASE),
    re.compile(r"\btodas las leyes\b", re.IGNORECASE),
    re.compile(r"\btodos los modelos\b", re.IGNORECASE),
    re.compile(r"\bfull details\b", re.IGNORECASE),
    re.compile(r"\bdetalle completo\b", re.IGNORECASE),
    re.compile(r"\bvista completa\b", re.IGNORECASE),
    re.compile(r"\bcatalogo completo\b", re.IGNORECASE),
    re.compile(r"\bcatálogo completo\b", re.IGNORECASE),
    re.compile(r"\bdatos operativos completos\b", re.IGNORECASE),
    re.compile(r"\bLista todas las claves\b", re.IGNORECASE),
    re.compile(
        r"\bcobertura completa de (Hacienda|AEAT|BOE|CNMV|ESMA|EUR-Lex|Banco de Espa[ñn]a)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcomplete coverage of (Hacienda|AEAT|BOE|CNMV|ESMA|EUR-Lex|Bank of Spain|Banco de Espa[ñn]a)\b",
        re.IGNORECASE,
    ),
]

NEGATION_MARKERS = (
    "no ",
    "not ",
    "must not",
    "do not",
    "does not",
    "no afirmar",
    "no implica",
    "no claim",
    "not a claim",
    "not claim",
    "sin afirmar",
)

MANDATORY_MATRIX_STATES = {
    "BOE legislation": "usable",
    "AEAT models": "partial",
    "CNMV": "partial",
    "EUR-Lex market acts": "usable",
    "ESMA MiFIR schemas/reporting": "partial",
    "ESMA FIRDS/FITRS": "very_limited",
    "MiCA CASP register": "usable",
    "Screening OFAC SDN": "usable",
    "Screening EU sanctions": "usable",
    "Screening UN / SEPBLAC / PEP": "not_exposed",
    "AEPD": "partial",
    "SEPBLAC": "partial",
    "BDE": "partial",
    "BORME": "partial",
    "BOE diario": "partial",
    "BDNS": "partial_loaded",
    "CENDOJ": "very_limited",
    "CDI / DTA convenios": "partial",
    "CRS / DAC2 / FATCA / GIIN": "partial",
    "PSD2 / SEPA": "partial",
    "PGC / XBRL / ESEF": "partial",
    "DORA / SFDR / CSRD / AIFMD / UCITS / CRD / EMIR / MiFID / MAR / PRIIPs / PBC / fraud": "out_of_scope",
}

MANDATORY_REGISTER_FAMILIES = [
    "AEAT modelos",
    "BOE legislacion",
    "DGT / PETETE",
    "TEAC / DYCTEA",
    "CNMV",
    "SEPBLAC",
    "Banco de Espana",
    "AEPD",
    "BDNS",
    "CENDOJ",
    "EUR-Lex",
    "ESMA",
    "OFAC SDN",
    "EU sanctions",
    "GIIN / IRS FATCA",
    "CDI / DTA conventions",
    "PSD2 / SEPA",
    "PGC / XBRL / ESEF",
]

CERTIFICATION_DOC = ROOT / "docs" / "source-assurance-certification-20260531.md"
FINAL_MATRIX = ROOT / "docs" / "final-product-coverage-matrix.md"
SOURCE_REGISTER = ROOT / "docs" / "reference" / "source-compliance-register.md"


@dataclass(frozen=True)
class GateIssue:
    check: str
    ok: bool
    reason: str
    path: str | None = None
    line: int | None = None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _public_files() -> list[Path]:
    files: list[Path] = []
    for pattern in PUBLIC_DOC_GLOBS:
        files.extend(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(set(files))


def _is_negated(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in NEGATION_MARKERS)


def scan_dangerous_claims() -> list[GateIssue]:
    issues: list[GateIssue] = []
    for path in _public_files():
        lines = _read(path).splitlines()
        if path.name == "master-execution-roadmap.md":
            lines = lines[:140]
        for line_no, line in enumerate(lines, start=1):
            if _is_negated(line):
                continue
            for pattern in DANGEROUS_PATTERNS:
                if pattern.search(line):
                    issues.append(
                        GateIssue(
                            "dangerous_claim_scan",
                            False,
                            f"dangerous broad source claim: {pattern.pattern}",
                            str(path.relative_to(ROOT)),
                            line_no,
                        )
                    )
    return issues


def _parse_final_matrix() -> dict[str, str]:
    states: dict[str, str] = {}
    for line in _read(FINAL_MATRIX).splitlines():
        if not line.startswith("| ") or line.startswith("| Domain ") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        state = cells[1].strip("`")
        states[cells[0]] = state
    return states


def check_final_matrix_states() -> list[GateIssue]:
    issues: list[GateIssue] = []
    states = _parse_final_matrix()
    for domain, expected_state in MANDATORY_MATRIX_STATES.items():
        actual = states.get(domain)
        if actual != expected_state:
            issues.append(
                GateIssue(
                    "final_matrix_state",
                    False,
                    f"{domain!r} state is {actual!r}, expected {expected_state!r}",
                    str(FINAL_MATRIX.relative_to(ROOT)),
                )
            )
    for domain, state in states.items():
        if state in {"complete", "complete_loaded", "exhaustive"}:
            issues.append(
                GateIssue(
                    "final_matrix_no_complete_claim",
                    False,
                    f"{domain!r} uses forbidden final state {state!r}",
                    str(FINAL_MATRIX.relative_to(ROOT)),
                )
            )
    matrix_text = _read(FINAL_MATRIX)
    if "/v1/cdi/convenios" in matrix_text:
        issues.append(
            GateIssue(
                "final_matrix_endpoint",
                False,
                "CDI/DTA final matrix references stale /v1/cdi/convenios path",
                str(FINAL_MATRIX.relative_to(ROOT)),
            )
        )
    for marker in ("inventory-only until source provenance fields are added", "source assurance not certified"):
        if marker not in matrix_text:
            issues.append(
                GateIssue(
                    "final_matrix_inventory_only",
                    False,
                    f"missing inventory-only limitation marker {marker!r}",
                    str(FINAL_MATRIX.relative_to(ROOT)),
                )
            )
    return issues


def check_source_register() -> list[GateIssue]:
    text = _read(SOURCE_REGISTER)
    issues: list[GateIssue] = []
    for family in MANDATORY_REGISTER_FAMILIES:
        if family not in text:
            issues.append(
                GateIssue(
                    "source_register_family",
                    False,
                    f"missing source-compliance family {family!r}",
                    str(SOURCE_REGISTER.relative_to(ROOT)),
                )
            )
    return issues


def check_certification_doc() -> list[GateIssue]:
    if not CERTIFICATION_DOC.exists():
        return [
            GateIssue(
                "source_assurance_certification_doc",
                False,
                "missing source assurance certification document",
                str(CERTIFICATION_DOC.relative_to(ROOT)),
            )
        ]
    text = _read(CERTIFICATION_DOC)
    required = [
        "No domain is certified as exhaustive",
        "Certification Classes",
        "Forbidden Product Claims",
        "Canary Gate Coverage",
    ]
    issues: list[GateIssue] = []
    for marker in required:
        if marker not in text:
            issues.append(
                GateIssue(
                    "source_assurance_certification_doc",
                    False,
                    f"missing required marker {marker!r}",
                    str(CERTIFICATION_DOC.relative_to(ROOT)),
                )
            )
    return issues


def run_gate() -> dict[str, Any]:
    issues = [
        *scan_dangerous_claims(),
        *check_final_matrix_states(),
        *check_source_register(),
        *check_certification_doc(),
    ]
    return {
        "ok": not issues,
        "checks": {
            "dangerous_claim_scan": not any(issue.check == "dangerous_claim_scan" for issue in issues),
            "final_matrix_state": not any(issue.check.startswith("final_matrix") for issue in issues),
            "source_register_family": not any(issue.check == "source_register_family" for issue in issues),
            "source_assurance_certification_doc": not any(
                issue.check == "source_assurance_certification_doc" for issue in issues
            ),
        },
        "issues": [asdict(issue) for issue in issues],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    result = run_gate()
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_out:
        Path(args.json_out).write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
