#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BEGIN_MARKER = "BEGIN_AEAT_HERMES_JSON"
END_MARKER = "END_AEAT_HERMES_JSON"


def extract_json_block(text: str) -> dict:
    begin = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if begin == -1 or end == -1:
        raise ValueError("missing BEGIN_AEAT_HERMES_JSON/END_AEAT_HERMES_JSON markers")
    if text.find(BEGIN_MARKER, begin + len(BEGIN_MARKER)) != -1:
        raise ValueError("multiple BEGIN_AEAT_HERMES_JSON markers")
    if text.find(END_MARKER, end + len(END_MARKER)) != -1:
        raise ValueError("multiple END_AEAT_HERMES_JSON markers")
    if end <= begin:
        raise ValueError("END_AEAT_HERMES_JSON appears before BEGIN_AEAT_HERMES_JSON")

    raw = text[begin + len(BEGIN_MARKER) : end].strip()
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
