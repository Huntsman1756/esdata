"""extend AEAT model instructions, keys, and inclusion rules

Revision ID: 20260514_0077_aeat_instruction_key_tables
Revises: 20260513_0076_liva_163_sexvicies_typo
Create Date: 2026-05-14

The original AEAT model schema stored basic keys and instructions but did not
carry per-row provenance or inclusion/exclusion rules. This revision is
additive: existing seed data remains readable while new official instruction
loads can store source URL, hash, capture date, routing keywords, and explicit
inclusion rules.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260514_0077_aeat_instruction_key_tables"
down_revision = "20260513_0076_liva_163_sexvicies_typo"
branch_labels = None
depends_on = None


TABLES_WITH_RLS = (
    "modelo_regla_inclusion",
    "modelo_trigger_keyword",
)


def _enable_rls(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = '{table_name}'
                      AND policyname = 'esdata_all'
                ) THEN
                    EXECUTE 'CREATE POLICY esdata_all ON {table_name} TO esdata USING (true) WITH CHECK (true)';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = '{table_name}'
                      AND policyname = 'service_role_all'
                ) THEN
                    EXECUTE 'CREATE POLICY service_role_all ON {table_name} TO service_role USING (true) WITH CHECK (true)';
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE modelo_clave
                ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'CLAVE',
                ADD COLUMN IF NOT EXISTS criterio_aplicacion TEXT,
                ADD COLUMN IF NOT EXISTS exclusiones TEXT,
                ADD COLUMN IF NOT EXISTS source_url TEXT,
                ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64),
                ADD COLUMN IF NOT EXISTS capture_date DATE
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE modelo_clave
            SET tipo = COALESCE(NULLIF(tipo, ''), NULLIF(tipo_clave, ''), 'CLAVE')
            WHERE tipo IS NULL OR tipo = ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_clave_campana_tipo_codigo
            ON modelo_clave(campana_id, tipo, codigo)
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE modelo_instruccion
                ADD COLUMN IF NOT EXISTS texto TEXT,
                ADD COLUMN IF NOT EXISTS casilla_referencia VARCHAR(20),
                ADD COLUMN IF NOT EXISTS source_url TEXT,
                ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64),
                ADD COLUMN IF NOT EXISTS capture_date DATE
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE modelo_instruccion
            SET texto = contenido
            WHERE texto IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS modelo_regla_inclusion (
                id SERIAL PRIMARY KEY,
                campana_id INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
                supuesto TEXT NOT NULL,
                decision VARCHAR(20) NOT NULL,
                condicion TEXT,
                umbral TEXT,
                fuente_normativa TEXT,
                source_url TEXT NOT NULL,
                source_hash VARCHAR(64),
                capture_date DATE,
                creado_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT ck_modelo_regla_inclusion_decision
                    CHECK (decision IN ('INCLUIR', 'EXCLUIR', 'CONDICIONAL', 'EVIDENCE_LIMITED'))
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_regla_inclusion_campana_supuesto
            ON modelo_regla_inclusion(campana_id, supuesto)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_modelo_regla_inclusion_campana
            ON modelo_regla_inclusion(campana_id)
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS modelo_trigger_keyword (
                id SERIAL PRIMARY KEY,
                modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
                keyword VARCHAR(100) NOT NULL,
                dominio VARCHAR(50),
                creado_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_trigger_keyword_modelo_keyword
            ON modelo_trigger_keyword(modelo_id, lower(keyword))
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_modelo_trigger_keyword_dominio
            ON modelo_trigger_keyword(dominio)
            """
        )
    )

    for table_name in TABLES_WITH_RLS:
        _enable_rls(table_name)


def downgrade() -> None:
    for table_name in reversed(TABLES_WITH_RLS):
        op.execute(sa.text(f"DROP POLICY IF EXISTS service_role_all ON {table_name}"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS esdata_all ON {table_name}"))
        op.execute(sa.text(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY"))

    op.execute(sa.text("DROP TABLE IF EXISTS modelo_trigger_keyword"))
    op.execute(sa.text("DROP TABLE IF EXISTS modelo_regla_inclusion"))

    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS ux_modelo_clave_campana_tipo_codigo"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE modelo_instruccion
                DROP COLUMN IF EXISTS texto,
                DROP COLUMN IF EXISTS casilla_referencia,
                DROP COLUMN IF EXISTS source_url,
                DROP COLUMN IF EXISTS source_hash,
                DROP COLUMN IF EXISTS capture_date
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE modelo_clave
                DROP COLUMN IF EXISTS tipo,
                DROP COLUMN IF EXISTS criterio_aplicacion,
                DROP COLUMN IF EXISTS exclusiones,
                DROP COLUMN IF EXISTS source_url,
                DROP COLUMN IF EXISTS source_hash,
                DROP COLUMN IF EXISTS capture_date
            """
        )
    )
