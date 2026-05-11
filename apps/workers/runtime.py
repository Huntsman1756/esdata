import logging
import os
import signal
import socket
import threading
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

DEFAULT_DATABASE_URL = "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata"
logger = logging.getLogger(__name__)


class GracefulShutdownRequested(Exception):
    """Raised to break out of the main worker loop on shutdown signal."""


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


_SQLITE_WARNING_SHOWN: bool = False


def _log_sqlite_fallback_warning(active_logger: logging.Logger) -> None:
    global _SQLITE_WARNING_SHOWN
    if _SQLITE_WARNING_SHOWN:
        return
    _SQLITE_WARNING_SHOWN = True
    url = getattr(active_logger, "effectiveLevel", None)
    try:
        import sqlalchemy as sa
        engine_url = active_logger.manager.loggerDict  # dummy
    except Exception:
        pass
    active_logger.warning(
        "SQLite detected: operating in reduced-quality mode. "
        "Vector search, fulltext, and pgvector features are unavailable. "
        "Use PostgreSQL for production."
    )


def ensure_database_connection(
    engine,
    *,
    attempts: int = 5,
    base_delay_seconds: int = 2,
    logger: logging.Logger | None = None,
) -> None:
    from sqlalchemy import engine as sa_engine

    active_logger = logger or logging.getLogger(__name__)
    engine_url = getattr(engine, "url", None)
    if getattr(engine_url, "drivername", None) == "sqlite":
        _log_sqlite_fallback_warning(active_logger)

    host = getattr(engine_url, "host", None) or "localhost"
    port = getattr(engine_url, "port", None) or 5432
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            try:
                resolved = socket.getaddrinfo(host, port)[0][4][0]
                active_logger.info("DB DNS resolved: %s -> %s", host, resolved)
            except socket.gaierror as exc:
                active_logger.warning("DNS probe failed for %s:%s: %s", host, port, exc)
                raise OSError(exc) from exc

            connect = getattr(engine, "connect", None)
            connection_context = connect() if callable(connect) else engine.begin()
            with connection_context as conn:
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
    shutdown_event=None,
) -> bool:
    if interval_seconds <= 0:
        return False

    heartbeat_touch = touch_fn or (lambda: touch_heartbeat(heartbeat_path))
    remaining = interval_seconds
    while remaining > 0:
        if shutdown_event is not None and shutdown_event.is_set():
            return True
        heartbeat_touch()
        sleep_for = min(chunk_seconds, remaining)
        time.sleep(sleep_for)
        remaining -= sleep_for

    return False


def finalize_partial_sync_status(
    *,
    base_status: str,
    missing_count: int,
    source_label: str,
) -> tuple[str, str | None]:
    if missing_count <= 0:
        return base_status, None

    final_status = "partial" if base_status == "ok" else base_status
    return final_status, f"Skipped {missing_count} {source_label} after fetch failures"


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


def register_signal_handlers(logger: logging.Logger) -> threading.Event:
    """Register SIGTERM/SIGINT handlers and return a shutdown event."""
    is_shutdown = threading.Event()

    def handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.warning("Received %s — initiating graceful shutdown", sig_name)
        is_shutdown.set()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    return is_shutdown


def graceful_shutdown_handler(
    logger: logging.Logger, is_shutdown: threading.Event
) -> None:
    """Stop the main loop gracefully. Call from worker entrypoints."""
    if is_shutdown.is_set():
        logger.info("Shutdown already signaled — exiting main loop")
        raise GracefulShutdownRequested()


def handle_worker_failure(
    engine,
    worker_name: str,
    entity_id: str,
    entity_type: str,
    exc: Exception,
    max_retries: int = 3,
) -> bool:
    """Handle a worker failure, adding to dead-letter queue if max retries exceeded.

    Returns True if the entity should be retried, False if moved to dead-letter.
    """
    import traceback

    import dead_letter

    error_msg = str(exc)[:5000]
    error_tb = traceback.format_exc()[:2000]

    retry_count = dead_letter.add_dead_letter(
        engine, worker_name, entity_id, entity_type, error_msg, error_tb, max_retries
    )

    if retry_count >= max_retries:
        logger.error(
            "Entity %s (%s) exceeded max retries (%d) in worker %s. Moved to dead-letter.",
            entity_id, entity_type, max_retries, worker_name,
        )
        return False  # Stop retrying

    logger.warning(
        "Entity %s (%s) failed in worker %s (retry %d/%d). Will retry.",
        entity_id, entity_type, worker_name, retry_count, max_retries,
    )
    return True  # Retry is still allowed
