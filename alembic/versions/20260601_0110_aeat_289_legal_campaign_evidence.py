"""add BOE legal campaign evidence for modelo 289

Revision ID: 20260601_0110_aeat_289_legal_campaign_evidence
Revises: 20260601_0109_aeat_190_internal_evidence
Create Date: 2026-06-01

Modelo 289 is already assertable through the AEAT operational lane. This
revision adds a separate BOE legal lane using Orden HAC/1504/2024, which
updates the 289 annexes for "2025 y siguientes". It does not change profile
obligations, campaign-bearing resource types, keys, instructions, or rules.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260601_0110_aeat_289_legal_campaign_evidence"
down_revision = "20260601_0109_aeat_190_internal_evidence"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
BOE_289_LEGAL_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2024-27528"
BOE_289_LEGAL_HASH = "91c443efff4b5cca5403d5573be18061effa495cdd9769c6dfc305b3c9110c3c"
BOE_289_LEGAL_LENGTH = 152551


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = _metadata_json(
        {
            "label": "Orden HAC/1504/2024. Modelo 289. 2025 y siguientes.",
            "anchor_text": "Modelo 289 2025 y siguientes",
            "source_kind": "legal_campaign_evidence",
            "campaign_evidence_role": "direct_legal",
            "capture_date": CAPTURE_DATE,
            "evidence_scope": "modelo_289_legal_campaign",
            "ejercicio_declarado": 2025,
            "anio_presentacion": 2026,
        }
    )
    params = {
        "url_boe": BOE_289_LEGAL_URL,
        "sha256_contenido": BOE_289_LEGAL_HASH,
        "content_length": BOE_289_LEGAL_LENGTH,
        "metadata": metadata,
    }

    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_normativa mn
            USING aeat_modelo am
            WHERE mn.modelo_id = am.id
              AND am.codigo = '289'
              AND mn.boe_id = 'BOE-A-2024-24098'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO modelo_normativa (
                modelo_id,
                boe_id,
                titulo,
                fecha,
                url_boe,
                resumen
            )
            SELECT
                am.id,
                'BOE-A-2024-27528',
                'Orden HAC/1504/2024 - actualizacion anexos I y II modelo 289',
                DATE '2024-12-31',
                :url_boe,
                'Orden HAC/1504/2024 que modifica la Orden HAP/1695/2016 y actualiza los anexos I y II del modelo 289 para 2025 y siguientes.'
            FROM aeat_modelo am
            WHERE am.codigo = '289'
            ON CONFLICT (modelo_id, boe_id) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                fecha = EXCLUDED.fecha,
                url_boe = EXCLUDED.url_boe,
                resumen = EXCLUDED.resumen
            """
        ),
        params,
    )
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '289'
                  AND mc.campana = '2025'
                  AND mc.activo = true
            ),
            existing AS (
                UPDATE modelo_recurso mr
                SET formato = 'html',
                    url_recurso = :url_boe,
                    sha256_contenido = :sha256_contenido,
                    content_length = :content_length,
                    metadata = COALESCE(mr.metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                    activa = true,
                    last_seen_at = now(),
                    row_completeness = 'complete',
                    row_provenance = 'official_exact'
                FROM target_campaign tc
                WHERE mr.campana_id = tc.campana_id
                  AND mr.tipo_recurso = 'normativa_hac_1504_2024'
                RETURNING mr.id
            )
            INSERT INTO modelo_recurso (
                campana_id,
                tipo_recurso,
                formato,
                url_recurso,
                sha256_contenido,
                content_length,
                metadata,
                activa,
                first_seen_at,
                last_seen_at,
                row_completeness,
                row_provenance
            )
            SELECT
                tc.campana_id,
                'normativa_hac_1504_2024',
                'html',
                :url_boe,
                :sha256_contenido,
                :content_length,
                CAST(:metadata AS jsonb),
                true,
                now(),
                now(),
                'complete',
                'official_exact'
            FROM target_campaign tc
            WHERE NOT EXISTS (SELECT 1 FROM existing)
            """
        ),
        params,
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_recurso mr
            USING modelo_campana mc, aeat_modelo am
            WHERE mr.campana_id = mc.id
              AND am.id = mc.modelo_id
              AND am.codigo = '289'
              AND mc.campana = '2025'
              AND mr.tipo_recurso = 'normativa_hac_1504_2024'
              AND mr.url_recurso = :url_boe
              AND mr.sha256_contenido = :sha256_contenido
            """
        ),
        {
            "url_boe": BOE_289_LEGAL_URL,
            "sha256_contenido": BOE_289_LEGAL_HASH,
        },
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_normativa mn
            USING aeat_modelo am
            WHERE mn.modelo_id = am.id
              AND am.codigo = '289'
              AND mn.boe_id = 'BOE-A-2024-27528'
            """
        )
    )
