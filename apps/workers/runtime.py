import logging
import os


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
