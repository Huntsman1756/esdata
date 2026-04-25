"""Motor de base de datos y gestion de sesiones compartida."""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine_instance(database_url: str | None = None) -> "engine":
    """Crear engine SQLAlchemy con configuracion por defecto.

    Args:
        database_url: URL de base de datos. Si None, usa DATABASE_URL del entorno.
    """
    if database_url is None:
        from .config import get_database_url
        database_url = get_database_url()

    engine_kwargs = {"future": True, "pool_size": 50, "max_overflow": 100, "pool_pre_ping": True}
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
