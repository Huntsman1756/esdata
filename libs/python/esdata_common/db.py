"""Motor de base de datos y gestion de sesiones compartida."""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


def create_engine_instance(database_url: str | None = None) -> Engine:
    """Crear engine SQLAlchemy con configuracion por defecto.

    Los valores de pool se leen de variables de entorno para permitir
    ajuste sin tocar codigo. Los default son seguros para 14+ servicios
    sobre una sola instancia PostgreSQL (max_connections=100).

    Variables de entorno:
        DB_POOL_SIZE: conexiones fijas por pool (default 5)
        DB_POOL_MAX_OVERFLOW: conexiones temporales extras (default 10)
        DB_POOL_RECYCLE: segundos antes de reciclar conexion (default 1800)

    Args:
        database_url: URL de base de datos. Si None, usa DATABASE_URL del entorno.
    """
    if database_url is None:
        from .config import get_database_url
        database_url = get_database_url()

    pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))
    max_overflow = int(os.environ.get("DB_POOL_MAX_OVERFLOW", "10"))
    pool_recycle = int(os.environ.get("DB_POOL_RECYCLE", "1800"))

    logger.info(
        "DB pool: size=%s max_overflow=%s recycle=%ds",
        pool_size,
        max_overflow,
        pool_recycle,
    )

    engine_kwargs: dict[str, Any] = {
        "future": True,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": pool_recycle,
    }
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    return create_engine(database_url, **engine_kwargs)


# Engine global (se crea al importar)
engine = create_engine_instance()

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency para obtener session de DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager para obtener session de DB.

    Uso:
        with db.db_session() as session:
            result = session.query(...).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
