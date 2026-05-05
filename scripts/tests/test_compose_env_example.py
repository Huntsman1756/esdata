import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "infra" / "deploy" / "docker-compose.prod.yml"
ENV_EXAMPLE = ROOT / "infra" / "deploy" / "compose.env.example"
COMPOSE_VAR_REF_RE = re.compile(r"(?<!\$)\$\{([^}]+)\}")
ENV_VAR_NAME_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)")


def _parse_env_keys(env_file: Path = ENV_EXAMPLE) -> tuple[set[str], set[str]]:
    return _parse_env_lines(env_file.read_text(encoding="utf-8").splitlines())


def _parse_env_lines(lines: Iterable[str]) -> tuple[set[str], set[str]]:
    keys: set[str] = set()
    duplicates: set[str] = set()

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key = line.split("=", 1)[0].strip()
        if key in keys:
            duplicates.add(key)
            continue

        keys.add(key)

    return keys, duplicates


def _parse_compose_variable_refs() -> set[str]:
    keys: set[str] = set()
    for raw_line in COMPOSE_FILE.read_text(encoding="utf-8").splitlines():
        line = _strip_inline_comment(raw_line).strip()
        if line.startswith("#"):
            continue

        for match in COMPOSE_VAR_REF_RE.finditer(line):
            name_match = ENV_VAR_NAME_RE.match(match.group(1).strip())
            if name_match is None:
                continue

            keys.add(name_match.group(1))

    return keys


def _strip_inline_comment(line: str) -> str:
    in_single_quote = False
    in_double_quote = False

    for index, char in enumerate(line):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if char == "#" and not in_single_quote and not in_double_quote:
            if index == 0 or line[index - 1].isspace():
                return line[:index]

    return line


def test_compose_env_example_keeps_compose_runtime_boundary_keys():
    keys, duplicates = _parse_env_keys()
    expected_keys = _parse_compose_variable_refs()

    assert expected_keys
    assert not duplicates
    assert keys == expected_keys


def test_compose_env_example_rejects_legacy_frontend_key_even_if_commented():
    contents = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_API_BASE_URL" not in contents


def test_parse_env_keys_reports_duplicate_keys():
    keys, duplicates = _parse_env_lines(
        [
            "DATABASE_URL=postgresql+psycopg://first",
            "DATABASE_URL=postgresql+psycopg://second",
        ]
    )

    assert keys == {"DATABASE_URL"}
    assert duplicates == {"DATABASE_URL"}
