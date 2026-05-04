import logging
import os
import socket
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

DEFAULT_DATABASE_URL = "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_interval_seconds(env_name: str, default: int) -> int:
    return int(os.getenv(env_name, str(default)))


def get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def configure_logging(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return logging.getLogger(name)


def ensure_database_connection(
    engine,
    *,
    attempts: int = 5,
    base_delay_seconds: int = 2,
    logger: logging.Logger | None = None,
) -> None:
    active_logger = logger or logging.getLogger(__name__)
    host = getattr(engine.url, "host", None) or "localhost"
    port = getattr(engine.url, "port", None) or 5432
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            try:
                resolved = socket.getaddrinfo(host, port)[0][4][0]
                active_logger.info("DB DNS resolved: %s -> %s", host, resolved)
            except socket.gaierror as exc:
                active_logger.warning("DNS probe failed for %s:%s: %s", host, port, exc)
                raise OSError(exc) from exc

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            active_logger.info("DB connection established")
            return
        except (OperationalError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                raise
            active_logger.warning(
                "DB connection attempt %s/%s failed: %s",
                attempt,
                attempts,
                exc,
            )
            time.sleep(min(base_delay_seconds * (2 ** (attempt - 1)), 30))

    if last_error is not None:
        raise last_error


def touch_heartbeat(path: str = "/tmp/worker_heartbeat") -> None:
    Path(path).touch()


def sleep_with_heartbeat(
    interval_seconds: int,
    *,
    chunk_seconds: int = 60,
    heartbeat_path: str = "/tmp/worker_heartbeat",
    touch_fn=None,
) -> None:
    if interval_seconds <= 0:
        return

    heartbeat_touch = touch_fn or (lambda: touch_heartbeat(heartbeat_path))
    remaining = interval_seconds
    while remaining > 0:
        heartbeat_touch()
        sleep_for = min(chunk_seconds, remaining)
        time.sleep(sleep_for)
        remaining -= sleep_for


def init_sentry(worker_name: str) -> None:
    """Initialize Sentry error monitoring for workers (optional)."""
    dsn = os.environ.get("ESDATA_SENTRY_DSN")
    if not dsn:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get("APP_ENV", "production"),
    )
    sentry_sdk.set_tag("worker", worker_name)
    logging.getLogger(__name__).info("Sentry enabled for worker %s", worker_name)
