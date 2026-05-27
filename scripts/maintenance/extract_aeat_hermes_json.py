#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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
