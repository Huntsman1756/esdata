"""recover AEAT 200 profile obligations with unique source evidence

Revision ID: 20260525_0099_obligacion_perfil_recover_200
Revises: 20260524_0098_aeat_289_documental_source_refresh
Create Date: 2026-05-25

Recover only Modelo 200 profile rows whose persisted source URL has one
unambiguous source_revision hash for AEAT-MODELO-200. This deliberately does
not recover Modelo 303, whose IVA applicability remains caveated by activity,
or Modelo 290, whose FATCA source URL has multiple hashes.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0099_obligacion_perfil_recover_200"
down_revision = "20260524_0098_aeat_289_documental_source_refresh"
branch_labels = None
depends_on = None


RECOVERY_NOTE = "200 profile obligation recovered from unique source_revision evidence."


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH unique_revision AS (
                SELECT
                    dgt_url AS source_url,
                    MAX(content_hash_sha256) AS source_hash,
                    MAX(fetched_at)::date AS capture_date
                FROM source_revision
                WHERE source_entity_tipo = 'obligacion_regulatoria'
                  AND source_entity_id = 'AEAT-MODELO-200'
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
                        WHEN op.notas LIKE '%' || :recovery_note || '%' THEN ''
                        ELSE E'\\n'
                    END
                    || CASE
                        WHEN op.notas LIKE '%' || :recovery_note || '%' THEN ''
                        ELSE :recovery_note
                    END
            FROM unique_revision ur
            WHERE op.modelo_aeat = '200'
              AND op.perfil_codigo IN (
                  'sociedad_valores',
                  'agencia_valores',
                  'eaf',
                  'entidad_credito',
                  'empresa_servicios_pago',
                  'sgiic'
              )
              AND op.source_url = ur.source_url
              AND op.source_hash IS NULL
              AND op.capture_date IS NOT NULL;
            """
        ),
        {"recovery_note": RECOVERY_NOTE},
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
                    REPLACE(COALESCE(notas, ''), :recovery_note, ''),
                    ''
                )
            WHERE modelo_aeat = '200'
              AND notas LIKE '%' || :recovery_note || '%';
            """
        ),
        {"recovery_note": RECOVERY_NOTE},
    )
