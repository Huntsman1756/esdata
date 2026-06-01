"""add direct AEAT campaign evidence for modelo 190

Revision ID: 20260601_0108_aeat_190_campaign_evidence
Revises: 20260601_0107_aeat_123_campaign_evidence
Create Date: 2026-06-01

Modelo 190 has an AEAT Sede operational page that states the active exercise
2025 in the current procedures section. This revision records the hashed page
as direct operational campaign evidence without changing keys, instructions,
rules, obligations, or profile applicability.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260601_0108_aeat_190_campaign_evidence"
down_revision = "20260601_0107_aeat_123_campaign_evidence"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
AEAT_190_OPERATIONAL_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/irpf/"
    "retenciones-ingresos-cuenta-pagos-fraccionados/retenciones-ingresos-cuenta/"
    "modelo-190.html"
)
AEAT_190_OPERATIONAL_HASH = (
    "b154ea65d4a7679774842767de2e643f76c194e037237052647f43962073f205"
)
AEAT_190_OPERATIONAL_LENGTH = 30641


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    metadata = _metadata_json(
        {
            "label": "Modelo 190. Ejercicio 2025. Gestiones activas en AEAT Sede.",
            "source_kind": "aeat_campaign_operational_evidence",
            "capture_date": CAPTURE_DATE,
            "evidence_scope": "operational_model_page",
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
                  AND am.codigo = '190'
                  AND mc.campana = '2025'
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
                  AND mr.tipo_recurso = 'instrucciones'
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
                'instrucciones',
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
            "url_instrucciones": AEAT_190_OPERATIONAL_URL,
            "sha256_contenido": AEAT_190_OPERATIONAL_HASH,
            "content_length": AEAT_190_OPERATIONAL_LENGTH,
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
              AND am.codigo = '190'
              AND mc.campana = '2025'
              AND mr.tipo_recurso = 'instrucciones'
              AND mr.url_recurso = :url_instrucciones
              AND mr.sha256_contenido = :sha256_contenido
            """
        ),
        {
            "url_instrucciones": AEAT_190_OPERATIONAL_URL,
            "sha256_contenido": AEAT_190_OPERATIONAL_HASH,
        },
    )
