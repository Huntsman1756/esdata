"""recover AEAT 111/115 profile obligations with unique source evidence

Revision ID: 20260524_0096_obligacion_perfil_recover_111_115
Revises: 20260524_0095_obligacion_perfil_global_fail_closed
Create Date: 2026-05-24

Sprint V intentionally failed all profile obligations closed when evidence was
not normalized. This revision recovers only the rows whose source URL has one
unambiguous source_revision hash for the exact AEAT model obligation.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0096_obligacion_perfil_recover_111_115"
down_revision = "20260524_0095_obligacion_perfil_global_fail_closed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH unique_revision AS (
                SELECT
                    dgt_url AS source_url,
                    CASE
                        WHEN source_entity_id = 'AEAT-MODELO-111' THEN '111'
                        WHEN source_entity_id = 'AEAT-MODELO-115' THEN '115'
                    END AS modelo_aeat,
                    MAX(content_hash_sha256) AS source_hash,
                    MAX(fetched_at)::date AS capture_date
                FROM source_revision
                WHERE source_entity_tipo = 'obligacion_regulatoria'
                  AND source_entity_id IN ('AEAT-MODELO-111', 'AEAT-MODELO-115')
                  AND content_hash_sha256 IS NOT NULL
                  AND fetched_at IS NOT NULL
                  AND dgt_url IS NOT NULL
                GROUP BY dgt_url, source_entity_id
                HAVING COUNT(DISTINCT content_hash_sha256) = 1
            )
            UPDATE obligacion_perfil op
            SET
                source_hash = ur.source_hash,
                capture_date = COALESCE(op.capture_date, ur.capture_date),
                verified = true,
                completeness = 'completa',
                safe_to_answer = true,
                notas = COALESCE(NULLIF(op.notas, ''), '')
                    || CASE
                        WHEN COALESCE(NULLIF(op.notas, ''), '') = '' THEN ''
                        WHEN op.notas LIKE '%111/115 profile obligation recovered from unique source_revision evidence%' THEN ''
                        ELSE E'\n'
                    END
                    || CASE
                        WHEN op.notas LIKE '%111/115 profile obligation recovered from unique source_revision evidence%' THEN ''
                        ELSE '111/115 profile obligation recovered from unique source_revision evidence.'
                    END
            FROM unique_revision ur
            WHERE op.modelo_aeat IN ('111', '115')
              AND op.modelo_aeat = ur.modelo_aeat
              AND op.source_url = ur.source_url
              AND op.source_hash IS NULL
              AND op.capture_date IS NOT NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET
                source_hash = NULL,
                verified = false,
                completeness = 'parcial',
                safe_to_answer = false,
                notas = NULLIF(
                    REPLACE(
                        COALESCE(notas, ''),
                        '111/115 profile obligation recovered from unique source_revision evidence.',
                        ''
                    ),
                    ''
                )
            WHERE modelo_aeat IN ('111', '115')
              AND notas LIKE '%111/115 profile obligation recovered from unique source_revision evidence%';
            """
        )
    )
