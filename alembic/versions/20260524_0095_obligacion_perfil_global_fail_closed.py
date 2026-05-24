"""fail-close profile obligations without normalized evidence

Revision ID: 20260524_0095_obligacion_perfil_global_fail_closed
Revises: 20260524_0094_aeat_fail_close_200_202_303_obligations
Create Date: 2026-05-24

This revision applies the same evidence rule globally: profile obligations are
not verified or safe to answer unless they have normalized hash/capture
evidence. Recovery should happen later by loading source_hash/capture_date from
authoritative source_revision/modelo_recurso rows, not by restoring legacy flags.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0095_obligacion_perfil_global_fail_closed"
down_revision = "20260524_0094_aeat_fail_close_200_202_303_obligations"
branch_labels = None
depends_on = None


NOTE = (
    "global profile obligation without normalized evidence: fail-closed until "
    "source_hash and capture_date are loaded."
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET
                safe_to_answer = false,
                verified = false,
                completeness = 'parcial',
                notas = COALESCE(NULLIF(notas, ''), '')
                    || CASE
                        WHEN COALESCE(NULLIF(notas, ''), '') = '' THEN ''
                        WHEN notas LIKE '%global profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.%' THEN ''
                        ELSE E'\\n'
                    END
                    || CASE
                        WHEN notas LIKE '%global profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.%' THEN ''
                        ELSE 'global profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.'
                    END
            WHERE source_url IS NOT NULL
              AND source_url <> ''
              AND (source_hash IS NULL OR capture_date IS NULL);
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET notas = NULLIF(
                REPLACE(
                    COALESCE(notas, ''),
                    'global profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.',
                    ''
                ),
                ''
            )
            WHERE notas LIKE '%global profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.%';
            """
        )
    )
