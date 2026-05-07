"""Configuracion de logging unificada para API y workers.

Soporta formato texto (default) y JSON (LOG_FORMAT=json).
El formato JSON facilita la ingestion en sistemas centralizados
como ELK, Datadog, CloudWatch, etc.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure(
    name: str,
    level: str | None = None,
    format_str: str | None = None,
) -> logging.Logger:
    """Configurar logger con formato estandar.

    Args:
        name: Nombre del logger (usar __name__).
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR). Si None, usa LOG_LEVEL del entorno o INFO.
        format_str: Formato de log personalizado. Si None, usa formato por defecto.
            Si LOG_FORMAT=json, usa formato JSON estructurado.

    Returns:
        Logger configurado.

    Ejemplo:
        logger = configure(__name__)
        logger.info("Mensaje")
    """
    from .config import get_str_env

    if level is None:
        level = get_str_env("LOG_LEVEL", "INFO")

    log_format = get_str_env("LOG_FORMAT", "text")

    if log_format == "json":
        format_str = None  # usar formato JSON
    elif format_str is None:
        format_str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Evitar agregar handlers multiples
    if not logger.handlers:
        if log_format == "json":
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JsonFormatter())
        else:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(handler)

    return logger


class JsonFormatter(logging.Formatter):
    """Formatter que produce logs en JSON estructurado."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": _iso_now(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Añadir campos extras si existen
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Añadir excepcion si existe
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        # Añadir duration si existe
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data, ensure_ascii=False)


class LoggingMixin:
    """Mixin para agregar logger configurado a clases."""

    @property
    def logger(self):
        return configure(self.__class__.__name__)


def log_duration(logger: logging.Logger, label: str):
    """Context manager para medir duracion de operaciones.

    Ejemplo:
        with log_duration(logger, "fetch_boe"):
            response = fetch_boe()
        # Log: INFO fetch_boe completed in 1234ms
    """

    class DurationTimer:
        def __init__(self, logger, label):
            self.logger = logger
            self.label = label
            self.start = 0.0

        def __enter__(self):
            self.start = time.monotonic()
            return self

        def __exit__(self, *args):
            elapsed_ms = (time.monotonic() - self.start) * 1000
            extra = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"{self.label} completed in {elapsed_ms:.0f}ms",
                args=(),
                exc_info=None,
            )
            extra.duration_ms = elapsed_ms
            self.logger.handle(extra)

    return DurationTimer(logger, label)
