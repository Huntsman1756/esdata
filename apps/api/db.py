import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from dotenv import load_dotenv

if "DATABASE_URL" not in os.environ:
    load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

db_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///./esdata-dev.db",
)
if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1).replace("postgres://", "postgresql+psycopg://", 1)
DATABASE_URL = db_url

engine_kwargs = {"future": True, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    logger = logging.getLogger(__name__)
    logger.warning(
        "SQLite detected: operating in reduced-quality mode. "
        "Vector search, fulltext, and pgvector features are disabled. "
        "Use PostgreSQL for production."
    )
else:
    # Pool conservador. Con PgBouncer (transaction pooling) delante, este pool
    # es por proceso de API; el pool agregado lo gestiona PgBouncer. Ajustable
    # via env si se opera sin PgBouncer.
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    close_resets_only=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
