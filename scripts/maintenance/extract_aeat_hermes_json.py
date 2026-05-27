#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

BEGIN_MARKER = "BEGIN_AEAT_HERMES_JSON"
END_MARKER = "END_AEAT_HERMES_JSON"


def extract_json_block(text: str) -> dict:
    begins = [
        match.start()
        for match in re.finditer(re.escape(BEGIN_MARKER), text)
    ]
    ends = [
        match.start()
        for match in re.finditer(re.escape(END_MARKER), text)
    ]
    if not begins or not ends:
        raise ValueError("missing BEGIN_AEAT_HERMES_JSON/END_AEAT_HERMES_JSON markers")

    parse_errors: list[str] = []
    for begin in reversed(begins):
        end = next((candidate for candidate in ends if candidate > begin), -1)
        if end == -1:
            continue
        raw = text[begin + len(BEGIN_MARKER) : end].strip()
        try:
            return _parse_raw_json(raw)
        except Exception as exc:
            parse_errors.append(str(exc))

    raise ValueError("no parseable AEAT Hermes JSON block found: " + "; ".join(parse_errors))


def _parse_raw_json(raw: str) -> dict:
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("extracted JSON root must be an object")
    return _sanitize_payload(payload)


def _is_transactional_aeat_form_url(url: object) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    parsed = urlparse(url)
    return (
        parsed.netloc.lower() in {"www1.agenciatributaria.gob.es", "www2.agenciatributaria.gob.es"}
        and parsed.path.lower().startswith("/wlpl/ov16-")
    )


def _sanitize_payload(payload: dict) -> dict:
    sources = payload.get("official_sources")
    claims = payload.get("official_source_claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        return payload

    transactional_source_ids = {
        source.get("source_id")
        for source in sources
        if isinstance(source, dict) and _is_transactional_aeat_form_url(source.get("url"))
    }
    removed_claims = [
        claim
        for claim in claims
        if isinstance(claim, dict) and claim.get("source_id") in transactional_source_ids
    ]
    payload["official_source_claims"] = [
        claim
        for claim in claims
        if not (
            isinstance(claim, dict) and claim.get("source_id") in transactional_source_ids
        )
    ]

    referenced_source_ids = {
        claim.get("source_id")
        for claim in payload["official_source_claims"]
        if isinstance(claim, dict) and claim.get("source_id") is not None
    }
    if referenced_source_ids:
        payload["official_sources"] = [
            source
            for source in sources
            if (
                isinstance(source, dict)
                and source.get("source_id") in referenced_source_ids
                and source.get("source_id") not in transactional_source_ids
            )
        ]
    else:
        payload["official_sources"] = [
            source
            for source in sources
            if not (
                isinstance(source, dict)
                and source.get("source_id") in transactional_source_ids
            )
        ]

    rejected_claims = payload.get("rejected_claims")
    if isinstance(rejected_claims, list):
        for claim in removed_claims:
            payload["rejected_claims"].append(
                {
                    "claim": str(claim.get("claim", "Transactional AEAT form claim")),
                    "reason": "Transactional AEAT form URLs are not documentary evidence sources.",
                    "blocked_by": "insufficient_locator",
                }
            )

    removed_source_ids = transactional_source_ids | (
        {source.get("source_id") for source in sources if isinstance(source, dict)}
        - {
            source.get("source_id")
            for source in payload["official_sources"]
            if isinstance(source, dict)
        }
    )
    for claim in payload.get("derived_claims", []):
        if isinstance(claim, dict) and isinstance(claim.get("input_claim_ids"), list):
            claim["input_claim_ids"] = [
                item for item in claim["input_claim_ids"] if item not in removed_source_ids
            ]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract strict AEAT Hermes JSON block")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        payload = extract_json_block(args.input.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        print(f"invalid Hermes JSON block: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"extracted {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
