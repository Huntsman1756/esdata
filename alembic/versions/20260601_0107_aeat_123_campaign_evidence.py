"""add direct AEAT campaign evidence for modelo 123

Revision ID: 20260601_0107_aeat_123_campaign_evidence
Revises: 20260601_0106_aeat_289_campaign_duality
Create Date: 2026-06-01

Modelo 123 has an AEAT Sede help page for electronic presentation that states
the operational range as exercise 2024 and following. This revision records the
hashed source as campaign evidence for the active 2024 row without changing
obligation or profile coverage.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260601_0107_aeat_123_campaign_evidence"
down_revision = "20260601_0106_aeat_289_campaign_duality"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
AEAT_123_PRESENTATION_HELP_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/"
    "presentacion-declaraciones-ayuda-tecnica/modelo-123.html"
)
AEAT_123_PRESENTATION_HELP_HASH = (
    "4bdbd140ef841194407204e9f89a1a5ba3ca2f23af333dd1dbf82c81951b9ad6"
)
AEAT_123_PRESENTATION_HELP_LENGTH = 19722


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    metadata = _metadata_json(
        {
            "label": "Presentacion del modelo 123. Ejercicio 2024 y siguientes",
            "source_kind": "aeat_campaign_operational_evidence",
            "capture_date": CAPTURE_DATE,
            "evidence_scope": "operational_presentation_help",
        }
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                UPDATE modelo_campana mc
                SET url_instrucciones = :url_instrucciones,
                    updated_at = now()
                FROM aeat_modelo am
                WHERE am.id = mc.modelo_id
                  AND am.codigo = '123'
                  AND mc.campana = '2024'
                  AND mc.activo = true
                RETURNING mc.id AS campana_id
            ),
            existing AS (
                UPDATE modelo_recurso mr
                SET formato = 'html',
                    url_recurso = :url_instrucciones,
                    sha256_contenido = :sha256_contenido,
                    content_length = :content_length,
                    metadata = COALESCE(mr.metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                    activa = true,
                    last_seen_at = now(),
                    row_completeness = 'complete',
                    row_provenance = 'official_exact'
                FROM target_campaign tc
                WHERE mr.campana_id = tc.campana_id
                  AND mr.tipo_recurso = 'ayuda_tecnica_presentacion'
                  AND mr.url_recurso = :url_instrucciones
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
                'ayuda_tecnica_presentacion',
                'html',
                :url_instrucciones,
                :sha256_contenido,
                :content_length,
                CAST(:metadata AS jsonb),
                true,
                now(),
                now(),
                'complete',
                'official_exact'
            FROM target_campaign tc
            WHERE NOT EXISTS (SELECT 1 FROM existing);
            """
        ),
        {
            "url_instrucciones": AEAT_123_PRESENTATION_HELP_URL,
            "sha256_contenido": AEAT_123_PRESENTATION_HELP_HASH,
            "content_length": AEAT_123_PRESENTATION_HELP_LENGTH,
            "metadata": metadata,
        },
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
              AND am.codigo = '123'
              AND mc.campana = '2024'
              AND mr.tipo_recurso = 'ayuda_tecnica_presentacion'
              AND mr.url_recurso = :url_instrucciones
              AND mr.sha256_contenido = :sha256_contenido
            """
        ),
        {
            "url_instrucciones": AEAT_123_PRESENTATION_HELP_URL,
            "sha256_contenido": AEAT_123_PRESENTATION_HELP_HASH,
        },
    )
