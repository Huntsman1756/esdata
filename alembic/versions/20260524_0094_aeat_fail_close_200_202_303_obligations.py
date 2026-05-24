"""fail-close legacy AEAT 200/202/303 profile obligations

Revision ID: 20260524_0094_aeat_fail_close_200_202_303_obligations
Revises: 20260524_0093_aeat_valores_187_198_contract
Create Date: 2026-05-24

The affected models remain partial as model contracts. This migration only
removes stored safe answers from legacy profile obligations that lack normalized
hash/capture evidence.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0094_aeat_fail_close_200_202_303_obligations"
down_revision = "20260524_0093_aeat_valores_187_198_contract"
branch_labels = None
depends_on = None


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
                        ELSE E'\n'
                    END
                    || '200/202/303 legacy profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.'
            WHERE modelo_aeat IN ('200', '202', '303')
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
                    '200/202/303 legacy profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.',
                    ''
                ),
                ''
            )
            WHERE modelo_aeat IN ('200', '202', '303');
            """
        )
    )
