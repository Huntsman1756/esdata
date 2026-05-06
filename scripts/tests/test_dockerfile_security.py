from __future__ import annotations

import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERIGNORE = ROOT / ".dockerignore"
DOCKERFILES = [
    ROOT / "apps/api/Dockerfile",
    ROOT / "apps/workers/Dockerfile",
    ROOT / "apps/workers/Dockerfile.worker",
    ROOT / "apps/workers/Dockerfile.aeat",
    ROOT / "infra/deploy/Dockerfile.ops",
]
FORBIDDEN_COPY_TOKENS = (".env", "credentials", "secret", "id_rsa", "id_ed25519", ".ssh")
FORBIDDEN_FILE_NAMES = {
    ".env",
    ".secret",
    ".secrets",
    "authorized_keys",
    "credentials",
    "id_ed25519",
    "id_rsa",
    "identity",
    "known_hosts",
    "secret",
    "secrets",
}
FORBIDDEN_FILE_PREFIXES = (".credential", ".secret", "credential.", "credentials.", "secret.", "secrets.")
FORBIDDEN_KEY_SUFFIXES = (".private_key", ".ssh_key")
REQUIRED_DOCKERIGNORE_PATTERNS = (
    ".env",
    ".env.*",
    "!.env.example",
    "**/.env",
    "**/.env.*",
    "!**/.env.example",
    "**/.ssh",
    "**/*secret*",
    "**/*credential*",
    "**/*private_key*",
    "**/id_rsa*",
    "**/id_ed25519*",
)


def _meaningful_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _copy_source_paths(path: Path) -> list[Path]:
    source_paths = []
    for line in _meaningful_lines(path):
        if not line.upper().startswith(("COPY ", "ADD ")):
            continue
        parts = [part for part in shlex.split(line, posix=False)[1:] if not part.startswith("--")]
        if len(parts) < 2:
            continue
        for source in parts[:-1]:
            if "://" in source or source.startswith(("$", "${")):
                continue
            source_paths.append((ROOT / source.strip('"')).resolve())
    return source_paths


def _is_forbidden_source_file(path: Path) -> bool:
    if any(part.lower() == ".ssh" for part in path.parts):
        return True
    name = path.name.lower()
    if name == ".env.example":
        return False
    if name in FORBIDDEN_FILE_NAMES or name.startswith(".env."):
        return True
    return name.startswith(FORBIDDEN_FILE_PREFIXES) or name.endswith(FORBIDDEN_KEY_SUFFIXES)


def test_dockerfiles_run_as_non_root_runtime_user():
    for path in DOCKERFILES:
        lines = _meaningful_lines(path)

        assert any(line.startswith("USER ") for line in lines), f"{path.relative_to(ROOT)} must set USER"
        assert not lines[-1].startswith("USER root"), f"{path.relative_to(ROOT)} must not end as root"


def test_dockerfiles_do_not_use_latest_or_unpinned_python_bases():
    for path in DOCKERFILES:
        from_lines = [line for line in _meaningful_lines(path) if line.startswith("FROM ")]

        assert from_lines, f"{path.relative_to(ROOT)} must declare a base image"
        for line in from_lines:
            assert ":latest" not in line, f"{path.relative_to(ROOT)} must not use latest: {line}"
            if line.startswith("FROM python:"):
                assert "@sha256:" in line, f"{path.relative_to(ROOT)} must pin Python base by digest: {line}"


def test_dockerfiles_do_not_copy_env_files_or_secrets():
    for path in DOCKERFILES:
        copy_lines = [
            line.lower()
            for line in _meaningful_lines(path)
            if line.upper().startswith(("COPY ", "ADD "))
        ]

        for line in copy_lines:
            assert not any(token in line for token in FORBIDDEN_COPY_TOKENS), (
                f"{path.relative_to(ROOT)} must not copy env files or secrets: {line}"
            )


def test_dockerfiles_do_not_broad_copy_forbidden_source_files():
    for dockerfile in DOCKERFILES:
        for source in _copy_source_paths(dockerfile):
            assert source.exists(), f"{dockerfile.relative_to(ROOT)} copies missing source {source}"
            files = source.rglob("*") if source.is_dir() else [source]

            forbidden = [
                path.relative_to(ROOT).as_posix()
                for path in files
                if path.is_file() and _is_forbidden_source_file(path)
            ]

            assert forbidden == [], f"{dockerfile.relative_to(ROOT)} copies forbidden source files: {forbidden}"


def test_root_dockerignore_excludes_runtime_env_and_secret_files():
    assert DOCKERIGNORE.exists(), ".dockerignore must exist at repo root"

    patterns = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    for pattern in REQUIRED_DOCKERIGNORE_PATTERNS:
        assert pattern in patterns, f".dockerignore missing {pattern}"
