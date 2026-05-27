#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _table(headers: list[str], rows: list[list[object]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        clean = [str(cell).replace("\n", " ").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(clean) + " |")
    return lines


def render_report(payload: dict) -> str:
    gate = payload["assertion_gate"]
    lines = [
        f"# Modelo {payload['model_code']} - Hermes AEAT structured curation",
        "",
        "## Decision",
        "",
        str(payload["decision"]),
        "",
        "## Assertion Gate",
        "",
        f"- campana_safe_to_assert: {gate['campana_safe_to_assert']}",
        f"- campana_afirmable: {gate['campana_afirmable']}",
        f"- campana_assertion_code: {gate['campana_assertion_code']}",
        f"- human_review_required: {payload['human_review_required']}",
        "",
        "## MCP Observations",
        "",
    ]

    lines.extend(
        _table(
            ["endpoint_or_tool", "field", "value", "purpose"],
            [
                [
                    item["endpoint_or_tool"],
                    item["field"],
                    json.dumps(item["value"], ensure_ascii=False),
                    item["purpose"],
                ]
                for item in payload["mcp_observations"]
            ],
        )
    )

    lines.extend(["", "## Official Sources", ""])
    lines.extend(
        _table(
            ["source_id", "authority", "url", "locator", "excerpt"],
            [
                [
                    item["source_id"],
                    item["authority"],
                    item["url"],
                    item["locator"],
                    item["excerpt"],
                ]
                for item in payload["official_sources"]
            ],
        )
    )

    lines.extend(["", "## Official Source Claims", ""])
    lines.extend(
        _table(
            ["claim", "source_id", "evidence_kind", "proves_campaign"],
            [
                [
                    item["claim"],
                    item["source_id"],
                    item["evidence_kind"],
                    item["proves_campaign"],
                ]
                for item in payload["official_source_claims"]
            ],
        )
    )

    lines.extend(["", "## Derived Claims", ""])
    lines.extend(
        _table(
            ["claim", "input_claim_ids", "confidence", "may_assert_campaign"],
            [
                [
                    item["claim"],
                    ", ".join(item["input_claim_ids"]),
                    item["confidence"],
                    item["may_assert_campaign"],
                ]
                for item in payload["derived_claims"]
            ],
        )
    )

    lines.extend(["", "## System Observed Claims", ""])
    lines.extend(
        _table(
            ["claim", "mcp_observation_indexes", "may_assert_campaign"],
            [
                [
                    item["claim"],
                    ", ".join(str(index) for index in item["mcp_observation_indexes"]),
                    item["may_assert_campaign"],
                ]
                for item in payload["system_observed_claims"]
            ],
        )
    )

    lines.extend(["", "## Rejected Claims", ""])
    lines.extend(
        _table(
            ["claim", "reason", "blocked_by"],
            [
                [item["claim"], item["reason"], item["blocked_by"]]
                for item in payload["rejected_claims"]
            ],
        )
    )

    lines.extend(
        [
            "",
            "## Rule",
            "",
            "This markdown is a rendered view of validated JSON. It is not the source of truth.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render validated AEAT Hermes JSON as markdown")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"invalid JSON report: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(payload), encoding="utf-8")
    print(f"rendered {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
