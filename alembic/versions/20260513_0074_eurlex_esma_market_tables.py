"""add EUR-Lex and ESMA market coverage tables

Revision ID: 20260513_0074_eurlex_esma_market_tables
Revises: 20260513_0073_webhook_events
Create Date: 2026-05-13

Dedicated market-regulation storage for the EUR-Lex/ESMA coverage sprint.
This migration owns schema only. Data loading remains worker-owned and must
not create tables at runtime.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260513_0074_eurlex_esma_market_tables"
down_revision = "20260513_0073_webhook_events"
branch_labels = None
depends_on = None


TABLES = (
    "eurlex_act",
    "eurlex_article",
    "esma_reporting_document",
    "esma_schema",
    "esma_schema_field",
    "esma_validation_rule",
    "esma_firds_file",
    "esma_firds_instrument",
    "esma_fitrs_result",
    "esma_dlt_market_infrastructure",
    "esma_dlt_exemption",
)


def _enable_backend_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
    for policy_name, role_name in (
        ("esdata_all", "esdata"),
        ("service_role_all", "service_role"),
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {policy_name} ON {table_name}
                    TO {role_name}
                    USING (true)
                    WITH CHECK (true);
                """
            )
        )


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eurlex_act (
                id SERIAL PRIMARY KEY,
                celex VARCHAR(20) UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                tipo VARCHAR(50),
                fecha_publicacion DATE,
                fecha_vigor DATE,
                url_eurlex TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eurlex_article (
                id SERIAL PRIMARY KEY,
                act_id INTEGER NOT NULL REFERENCES eurlex_act(id) ON DELETE CASCADE,
                numero VARCHAR(20) NOT NULL,
                titulo TEXT,
                texto TEXT NOT NULL,
                url_eurlex TEXT,
                source_hash VARCHAR(64),
                capture_date DATE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(act_id, numero)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_reporting_document (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(50),
                titulo TEXT NOT NULL,
                referencia VARCHAR(100),
                url_esma TEXT NOT NULL,
                fecha_publicacion DATE,
                source_hash VARCHAR(64),
                capture_date DATE,
                dominio VARCHAR(50),
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_schema (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                version VARCHAR(20),
                dominio VARCHAR(50),
                url_esma TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(nombre, version, dominio)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_schema_field (
                id SERIAL PRIMARY KEY,
                schema_id INTEGER NOT NULL REFERENCES esma_schema(id) ON DELETE CASCADE,
                nombre_campo VARCHAR(200) NOT NULL,
                tipo VARCHAR(50),
                longitud INTEGER,
                obligatorio BOOLEAN,
                descripcion TEXT,
                rts_referencia VARCHAR(100),
                formato VARCHAR(100),
                source_url TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(schema_id, nombre_campo)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_validation_rule (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) NOT NULL,
                descripcion TEXT NOT NULL,
                campo_afectado VARCHAR(200),
                severidad VARCHAR(20),
                rts_referencia VARCHAR(100),
                source_url TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(codigo, source_url)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_firds_file (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(20),
                fecha DATE NOT NULL,
                url_esma TEXT NOT NULL,
                size_bytes BIGINT,
                source_hash VARCHAR(64),
                downloaded BOOLEAN NOT NULL DEFAULT false,
                processed BOOLEAN NOT NULL DEFAULT false,
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(tipo, fecha, url_esma)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_firds_instrument (
                id SERIAL PRIMARY KEY,
                isin VARCHAR(12),
                nombre TEXT,
                tipo_instrumento VARCHAR(50),
                fecha_admision DATE,
                mic VARCHAR(10),
                moneda VARCHAR(3),
                source_file_id INTEGER REFERENCES esma_firds_file(id) ON DELETE SET NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_fitrs_result (
                id SERIAL PRIMARY KEY,
                isin VARCHAR(12),
                tipo_transparencia VARCHAR(50),
                periodo DATE,
                resultado JSONB,
                source_url TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_dlt_market_infrastructure (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                pais VARCHAR(3),
                tipo VARCHAR(50),
                autoridad_competente TEXT,
                fecha_autorizacion DATE,
                url_esma TEXT,
                source_hash VARCHAR(64),
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT false,
                completeness VARCHAR(50) NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(nombre, pais, tipo)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS esma_dlt_exemption (
                id SERIAL PRIMARY KEY,
                infrastructure_id INTEGER REFERENCES esma_dlt_market_infrastructure(id) ON DELETE CASCADE,
                tipo_exencion TEXT,
                articulo_referencia TEXT,
                fecha_concesion DATE,
                source_url TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_eurlex_act_celex ON eurlex_act(celex);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_eurlex_article_act_numero ON eurlex_article(act_id, numero);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_reporting_document_dominio ON esma_reporting_document(dominio);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_schema_dominio ON esma_schema(dominio);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_schema_field_schema ON esma_schema_field(schema_id);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_validation_rule_codigo ON esma_validation_rule(codigo);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_firds_file_fecha_tipo ON esma_firds_file(fecha, tipo);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_firds_instrument_isin ON esma_firds_instrument(isin);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_fitrs_result_isin_periodo ON esma_fitrs_result(isin, periodo);"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_esma_dlt_market_infra_tipo ON esma_dlt_market_infrastructure(tipo);"))

    for table_name in TABLES:
        _enable_backend_rls(table_name)


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS service_role_all ON {table_name};"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS esdata_all ON {table_name};"))
        op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY;"))

    for table_name in reversed(TABLES):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
