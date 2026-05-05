"""add row completeness and provenance columns

# Revision ID: 20260504_0058_row_completeness_provenance
# Revises: 20260504_0057_dgt_queue_split
# Create Date: 2026-05-04 00:58:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260504_0058_row_completeness_provenance"
down_revision = "20260504_0057_dgt_queue_split"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso ADD COLUMN IF NOT EXISTS row_completeness TEXT DEFAULT 'complete'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso ADD COLUMN IF NOT EXISTS row_provenance TEXT DEFAULT 'official_exact'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS row_completeness TEXT DEFAULT 'partial'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ADD COLUMN IF NOT EXISTS row_provenance TEXT DEFAULT 'official_best_effort'"
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET row_completeness = COALESCE(row_completeness, 'complete'),
                row_provenance = COALESCE(row_provenance, 'official_exact')
            WHERE row_completeness IS NULL OR row_provenance IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE documento_interpretativo
            SET row_completeness = COALESCE(row_completeness, 'partial'),
                row_provenance = COALESCE(row_provenance, 'official_best_effort')
            WHERE row_completeness IS NULL OR row_provenance IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso ALTER COLUMN row_completeness SET DEFAULT 'complete'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso ALTER COLUMN row_provenance SET DEFAULT 'official_exact'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ALTER COLUMN row_completeness SET DEFAULT 'partial'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ALTER COLUMN row_provenance SET DEFAULT 'official_best_effort'"
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso ALTER COLUMN row_completeness SET NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso ALTER COLUMN row_provenance SET NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ALTER COLUMN row_completeness SET NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo ALTER COLUMN row_provenance SET NOT NULL"
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE modelo_recurso
                ADD CONSTRAINT ck_modelo_recurso_row_completeness
                CHECK (row_completeness IN ('complete', 'partial'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE modelo_recurso
                ADD CONSTRAINT ck_modelo_recurso_row_provenance
                CHECK (row_provenance IN ('official_exact', 'official_best_effort'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE documento_interpretativo
                ADD CONSTRAINT ck_documento_interpretativo_row_completeness
                CHECK (row_completeness IN ('complete', 'partial'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE documento_interpretativo
                ADD CONSTRAINT ck_documento_interpretativo_row_provenance
                CHECK (row_provenance IN ('official_exact', 'official_best_effort'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo DROP CONSTRAINT IF EXISTS ck_documento_interpretativo_row_provenance"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo DROP CONSTRAINT IF EXISTS ck_documento_interpretativo_row_completeness"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso DROP CONSTRAINT IF EXISTS ck_modelo_recurso_row_provenance"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE modelo_recurso DROP CONSTRAINT IF EXISTS ck_modelo_recurso_row_completeness"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo DROP COLUMN IF EXISTS row_provenance"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE documento_interpretativo DROP COLUMN IF EXISTS row_completeness"
        )
    )
    op.execute(
        sa.text("ALTER TABLE modelo_recurso DROP COLUMN IF EXISTS row_provenance")
    )
    op.execute(
        sa.text("ALTER TABLE modelo_recurso DROP COLUMN IF EXISTS row_completeness")
    )
