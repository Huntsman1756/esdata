"""keep Modelo 193 domestic profile obligations fail-closed

Revision ID: 20260524_0091_aeat_193_domestic_applicability_fail_closed
Revises: 20260524_0090_aeat_193_income_type_rules
Create Date: 2026-05-24

Modelo 193 has income-type evidence for resident dividends and interest, but
the legacy profile obligations lack normalized source_hash evidence. Keep those
profile obligations partial until a full payer/recipient/article/exemption
contract is curated.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0091_aeat_193_domestic_applicability_fail_closed"
down_revision = "20260524_0090_aeat_193_income_type_rules"
branch_labels = None
depends_on = None

NOTE_MARKER = "[0091] Modelo 193 aplicabilidad domestica pendiente de hash/captura normalizada."


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE aeat_modelo
            SET periodo = 'anual'
            WHERE codigo = '193'
              AND COALESCE(periodo, '') <> 'anual';
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET
                verified = false,
                safe_to_answer = false,
                completeness = 'parcial',
                notas = trim(
                    both ' ' FROM concat_ws(
                        ' ',
                        NULLIF(notas, ''),
                        '[0091] Modelo 193 aplicabilidad domestica pendiente de hash/captura normalizada.'
                    )
                )
            WHERE modelo_aeat = '193'
              AND (
                  source_hash IS NULL
                  OR source_hash = ''
                  OR capture_date IS NULL
              )
              AND COALESCE(notas, '') NOT LIKE '%[0091] Modelo 193 aplicabilidad domestica pendiente%';
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET
                verified = true,
                safe_to_answer = true,
                completeness = 'completa',
                notas = NULLIF(
                    trim(
                        both ' ' FROM replace(
                            COALESCE(notas, ''),
                            '[0091] Modelo 193 aplicabilidad domestica pendiente de hash/captura normalizada.',
                            ''
                        )
                    ),
                    ''
                )
            WHERE modelo_aeat = '193'
              AND COALESCE(notas, '') LIKE '%[0091] Modelo 193 aplicabilidad domestica pendiente%';
            """
        )
    )
