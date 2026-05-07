"""Stub for apps.workers.runtime — allows conftest.py to import without full worker runtime."""


class GracefulShutdownRequested(Exception):
    pass


def handle_worker_failure(exc: Exception) -> None:
    pass


def get_database_url() -> str:
    return "sqlite:///test.db"


def get_interval_seconds(env_name: str, default: int) -> int:
    return default


def get_bool_env(name: str, default: bool) -> bool:
    return default
