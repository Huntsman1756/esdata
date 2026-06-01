"""separate AEAT 289 declared exercise and presentation year

Revision ID: 20260601_0106_aeat_289_campaign_duality
Revises: 20260531_0105_mica_register_api_rls
Create Date: 2026-06-01

Modelo 289 is an annual informative declaration where the declared exercise
and the presentation year differ. This revision records that duality for the
2025 campaign and replaces the stale AEAT 2024 campaign URL with the current
AEAT 2025 campaign evidence. It does not promote profile obligations.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260601_0106_aeat_289_campaign_duality"
down_revision = "20260531_0105_mica_register_api_rls"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
AEAT_289_CAMPAIGN_2025_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/"
    "declaraciones-informativas-otros-impuestos-tasas/"
    "campana-declaraciones-informativas-2025/normativa/modelo-289.html"
)
AEAT_289_CAMPAIGN_2025_HASH = (
    "2502f41331ddd2eb1b39171bd3d54be661baf5cc69a6c4c54812d38c4f29867b"
)
AEAT_289_CAMPAIGN_2025_LENGTH = 44398


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE modelo_campana
                ADD COLUMN IF NOT EXISTS ejercicio_declarado INTEGER,
                ADD COLUMN IF NOT EXISTS anio_presentacion INTEGER
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP FUNCTION IF EXISTS modelo_campana_activa(INTEGER);

            CREATE FUNCTION modelo_campana_activa(p_modelo_id INTEGER)
            RETURNS TABLE (
                id INTEGER,
                campana TEXT,
                url_instrucciones TEXT,
                url_normativa TEXT,
                url_formato TEXT,
                ejercicio_declarado INTEGER,
                anio_presentacion INTEGER
            ) AS $$
                SELECT
                    id,
                    campana,
                    url_instrucciones,
                    url_normativa,
                    url_formato,
                    ejercicio_declarado,
                    anio_presentacion
                FROM modelo_campana
                WHERE modelo_id = p_modelo_id AND activo = true
                ORDER BY campana DESC
                LIMIT 1;
            $$ LANGUAGE sql STABLE;
            """
        )
    )

    bind = op.get_bind()
    metadata = _metadata_json(
        {
            "label": "Modelo 289 - normativa campana declaraciones informativas 2025",
            "anchor_text": "Modelo 289 campana declaraciones informativas 2025",
            "scope": "modelo_289_campaign_duality",
            "source_kind": "aeat_campaign_operational_evidence",
            "capture_date": CAPTURE_DATE,
            "ejercicio_declarado": 2025,
            "anio_presentacion": 2026,
        }
    )
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                UPDATE modelo_campana mc
                SET url_instrucciones = :url_instrucciones,
                    ejercicio_declarado = 2025,
                    anio_presentacion = 2026,
                    updated_at = now()
                FROM aeat_modelo am
                WHERE am.id = mc.modelo_id
                  AND am.codigo = '289'
                  AND mc.campana = '2025'
                RETURNING mc.id AS campana_id
            ),
            existing AS (
                UPDATE modelo_recurso mr
                SET formato = 'html',
                    url_recurso = :url_instrucciones,
                    content_length = :content_length,
                    metadata = COALESCE(mr.metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                    activa = true,
                    last_seen_at = now(),
                    row_completeness = 'complete',
                    row_provenance = 'official_exact'
                FROM target_campaign tc
                WHERE mr.campana_id = tc.campana_id
                  AND mr.tipo_recurso = 'instrucciones'
                  AND mr.sha256_contenido = :sha256_contenido
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
            "url_instrucciones": AEAT_289_CAMPAIGN_2025_URL,
            "sha256_contenido": AEAT_289_CAMPAIGN_2025_HASH,
            "content_length": AEAT_289_CAMPAIGN_2025_LENGTH,
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
              AND am.codigo = '289'
              AND mc.campana = '2025'
              AND mr.tipo_recurso = 'instrucciones'
              AND mr.url_recurso = :url_instrucciones;

            UPDATE modelo_campana mc
            SET ejercicio_declarado = NULL,
                anio_presentacion = NULL,
                updated_at = now()
            FROM aeat_modelo am
            WHERE am.id = mc.modelo_id
              AND am.codigo = '289'
              AND mc.campana = '2025';

            DROP FUNCTION IF EXISTS modelo_campana_activa(INTEGER);

            CREATE FUNCTION modelo_campana_activa(p_modelo_id INTEGER)
            RETURNS TABLE (
                id INTEGER,
                campana TEXT,
                url_instrucciones TEXT,
                url_normativa TEXT,
                url_formato TEXT
            ) AS $$
                SELECT id, campana, url_instrucciones, url_normativa, url_formato
                FROM modelo_campana
                WHERE modelo_id = p_modelo_id AND activo = true
                ORDER BY campana DESC
                LIMIT 1;
            $$ LANGUAGE sql STABLE;
            """
        ),
        {"url_instrucciones": AEAT_289_CAMPAIGN_2025_URL},
    )
