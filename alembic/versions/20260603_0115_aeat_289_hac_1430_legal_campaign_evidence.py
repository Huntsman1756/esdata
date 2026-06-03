"""add HAC/1430/2025 legal campaign evidence for modelo 289

Revision ID: 20260603_0115_aeat_289_hac_1430_legal_campaign_evidence
Revises: 20260602_0114_aeat_190_field_rules_key_subclave
Create Date: 2026-06-03

Modelo 289 already has operational campaign evidence and an older BOE legal
lane. This revision adds Orden HAC/1430/2025 as the current direct legal BOE
evidence for the 2025 campaign. The order modifies the 289 annexes and states
that it is aplicable, por primera vez, a las declaraciones informativas
correspondientes al ejercicio 2025 for modelo 289. It does not change profile
obligations, campaign-bearing resource types, keys, instructions, or rules.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260603_0115_aeat_289_hac_1430_legal_campaign_evidence"
down_revision = "20260602_0114_aeat_190_field_rules_key_subclave"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-03"
BOE_289_HAC_1430_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25389"
BOE_289_HAC_1430_HASH = "45522b6eed4eca77673bffd87d7a4d744b9195e00ec4594a9fb9ae591b32421a"
BOE_289_HAC_1430_LENGTH = 110846


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = _metadata_json(
        {
            "label": (
                "Orden HAC/1430/2025. Modelo 289. Anexos I y II; "
                "ejercicio 2025."
            ),
            "anchor_text": "Orden HAC/1430/2025, de 3 de diciembre",
            "source_kind": "legal_campaign_evidence",
            "campaign_evidence_role": "direct_legal",
            "capture_date": CAPTURE_DATE,
            "evidence_scope": "modelo_289_legal_campaign",
            "ejercicio_declarado": 2025,
            "anio_presentacion": 2026,
            "boe_id": "BOE-A-2025-25389",
            "legal_effect_text": (
                "aplicable, por primera vez, a las declaraciones informativas "
                "correspondientes al ejercicio 2025"
            ),
            "modified_order": "Orden HAP/1695/2016",
        }
    )
    params = {
        "url_boe": BOE_289_HAC_1430_URL,
        "sha256_contenido": BOE_289_HAC_1430_HASH,
        "content_length": BOE_289_HAC_1430_LENGTH,
        "metadata": metadata,
    }

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
                'BOE-A-2025-25389',
                'Orden HAC/1430/2025 - actualizacion anexos I y II modelo 289',
                DATE '2025-12-12',
                :url_boe,
                'Orden HAC/1430/2025 que modifica los anexos I y II de la Orden HAP/1695/2016 del modelo 289 y resulta aplicable por primera vez al ejercicio 2025.'
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
                  AND mr.tipo_recurso = 'normativa_hac_1430_2025'
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
                'normativa_hac_1430_2025',
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
              AND mr.tipo_recurso = 'normativa_hac_1430_2025'
              AND mr.url_recurso = :url_boe
              AND mr.sha256_contenido = :sha256_contenido
            """
        ),
        {
            "url_boe": BOE_289_HAC_1430_URL,
            "sha256_contenido": BOE_289_HAC_1430_HASH,
        },
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_normativa mn
            USING aeat_modelo am
            WHERE mn.modelo_id = am.id
              AND am.codigo = '289'
              AND mn.boe_id = 'BOE-A-2025-25389'
            """
        )
    )
