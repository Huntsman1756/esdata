#!/usr/bin/env python
"""Static gate for answer verifiability in MCP/API responses.

This gate protects the core product promise: a useful answer must carry
source locators that a human can inspect, or it must remain fail-closed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GateIssue:
    check: str
    path: str
    message: str


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _contains_all(text: str, markers: list[str]) -> list[str]:
    return [marker for marker in markers if marker not in text]


def check_consulta_response_contract() -> list[GateIssue]:
    path = "apps/api/schemas.py"
    text = _read(path)
    required = [
        "class ChunkCitation",
        "source_url: str | None",
        "source_hash: str | None",
        "class ClaimCitation",
        "class ConsultaFiscalResponse",
        "safe_to_answer: bool | None",
        "evidence_notice: str | None",
        "result_metadata: dict",
        "cited_chunks: list[ChunkCitation]",
        "claim_citations: list[ClaimCitation]",
    ]
    return [
        GateIssue("consulta_response_contract", path, f"Missing marker: {marker}")
        for marker in _contains_all(text, required)
    ]


def check_consulta_source_verification_logic() -> list[GateIssue]:
    path = "apps/api/routers/consulta.py"
    text = _read(path)
    required = [
        "def _collect_verifiable_source_urls",
        "source_verification",
        "source_urls",
        "required_for_safe_answer",
        "safe_to_answer\"] and not verifiable_source_urls",
        "cited_chunks",
        "claim_citations",
        "source_hash",
    ]
    return [
        GateIssue("consulta_source_verification_logic", path, f"Missing marker: {marker}")
        for marker in _contains_all(text, required)
    ]


def check_mcp_policy() -> list[GateIssue]:
    path = "apps/api/mcp_catalog.py"
    text = _read(path)
    required = [
        "REGLA DE VERIFICABILIDAD",
        "source_url",
        "source_hash",
        "cited_chunks",
        "claim_citations",
        "result_metadata.source_verification",
        "safe_to_answer must be false",
    ]
    return [
        GateIssue("mcp_policy", path, f"Missing marker: {marker}")
        for marker in _contains_all(text, required)
    ]


def check_openapi_contract() -> list[GateIssue]:
    issues: list[GateIssue] = []
    for path in [
        "docs/openapi-gpt.json",
        "docs/openapi-gpt-3.0.json",
        "docs/openapi-gpt-actions-30.json",
        "docs/openapi-gpt-actions-30-3.0.json",
    ]:
        text = _read(path)
        required = [
            "source_hash",
            "result_metadata.source_verification",
            "claim_citations",
            "cited_chunks",
        ]
        issues.extend(
            GateIssue("openapi_contract", path, f"Missing marker: {marker}")
            for marker in _contains_all(text, required)
        )
    return issues


def run_gate() -> dict:
    issues: list[GateIssue] = []
    issues.extend(check_consulta_response_contract())
    issues.extend(check_consulta_source_verification_logic())
    issues.extend(check_mcp_policy())
    issues.extend(check_openapi_contract())

    return {
        "ok": not issues,
        "checks": {
            "consulta_response_contract": not any(i.check == "consulta_response_contract" for i in issues),
            "consulta_source_verification_logic": not any(
                i.check == "consulta_source_verification_logic" for i in issues
            ),
            "mcp_policy": not any(i.check == "mcp_policy" for i in issues),
            "openapi_contract": not any(i.check == "openapi_contract" for i in issues),
        },
        "issues": [asdict(issue) for issue in issues],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify ESData answer-source verifiability contract")
    parser.parse_args()

    result = run_gate()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
