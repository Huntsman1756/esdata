from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import create_engine, pool
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table, text

ALEMBIC_VERSION_NUM_LENGTH = 128


def _version_table_impl(self, *, version_table: str, version_table_schema: str | None, version_table_pk: bool, **kw):
    # Repo revision ids are descriptive and exceed Alembic's default String(32).
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", String(ALEMBIC_VERSION_NUM_LENGTH), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(
            PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
        )
    return vt


DefaultImpl.version_table_impl = _version_table_impl


def _widen_existing_version_table_if_needed(connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    connection.execute(
        text(
            f"ALTER TABLE IF EXISTS alembic_version "
            f"ALTER COLUMN version_num TYPE VARCHAR({ALEMBIC_VERSION_NUM_LENGTH})"
        )
    )

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + db_url.removeprefix("postgresql://")
    return db_url


def get_url() -> str:
    return normalize_db_url(
        os.getenv(
            "DATABASE_URL",
            config.get_main_option("sqlalchemy.url"),
        )
    )


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool, future=True)

    with connectable.connect() as connection:
        _widen_existing_version_table_if_needed(connection)
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
