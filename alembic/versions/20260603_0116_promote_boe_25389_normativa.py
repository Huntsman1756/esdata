"""promote BOE-A-2025-25389 legal evidence for selected AEAT models

Revision ID: 20260603_0116_promote_boe_25389_normativa
Revises: 20260603_0115_aeat_289_hac_1430_legal_campaign_evidence
Create Date: 2026-06-03

Promotes the stable recaptured BOE-A-2025-25389 source for models
182, 184, 195, 199, 282 and 345. Modelo 193 is intentionally excluded because
its active campaign is currently in conflict and needs separate review.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260603_0116_promote_boe_25389_normativa"
down_revision = "20260603_0115_aeat_289_hac_1430_legal_campaign_evidence"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-03"
BOE_ID = "BOE-A-2025-25389"
BOE_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25389"
BOE_ACT_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2025-25389"
BOE_HASH = "45522b6eed4eca77673bffd87d7a4d744b9195e00ec4594a9fb9ae591b32421a"
BOE_CONTENT_LENGTH = 110846
TARGET_CODES = ("182", "184", "195", "199", "282", "345")


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = _metadata_json(
        {
            "label": "Orden HAC/1430/2025. Modelos 182, 184, 195, 199, 282 y 345.",
            "anchor_text": "Orden HAC/1430/2025, de 3 de diciembre",
            "source_kind": "legal_campaign_evidence",
            "campaign_evidence_role": "direct_legal",
            "capture_date": CAPTURE_DATE,
            "evidence_scope": "aeat_2025_selected_informative_models_legal_campaign",
            "boe_id": BOE_ID,
            "hash_lineage": "stable_doc_php_recapture",
            "recapture_audit": "docs/operations/boe-recapture-audit/boe_recapture_audit_20260603_203107.json",
            "excluded_model_codes": ["193"],
        }
    )
    params = {
        "url_boe": BOE_URL,
        "sha256_contenido": BOE_HASH,
        "content_length": BOE_CONTENT_LENGTH,
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
                'Orden HAC/1430/2025 - actualizacion modelos informativos 2025',
                DATE '2025-12-12',
                :url_boe,
                'Orden HAC/1430/2025 que modifica ordenes reguladoras de los modelos 182, 184, 195, 199, 282 y 345. Promocion limitada a modelos sin conflicto de campana.'
            FROM aeat_modelo am
            WHERE am.codigo IN ('182', '184', '195', '199', '282', '345')
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
            UPDATE modelo_recurso mr
            SET tipo_recurso = 'normativa_hac_1430_2025',
                formato = 'html',
                url_recurso = :url_boe,
                sha256_contenido = :sha256_contenido,
                content_length = :content_length,
                metadata = COALESCE(mr.metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                activa = true,
                last_seen_at = now(),
                row_completeness = 'complete',
                row_provenance = 'official_exact'
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mr.campana_id = mc.id
              AND am.codigo IN ('182', '184', '195', '199', '282', '345')
              AND mc.campana = '2025'
              AND mc.activo IS true
              AND mr.tipo_recurso IN ('normativa', 'normativa_hac_1430_2025')
              AND mr.url_recurso LIKE '%BOE-A-2025-25389%'
              AND mr.sha256_contenido = :sha256_contenido
            """
        ),
        params,
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE modelo_recurso mr
            SET tipo_recurso = 'normativa',
                formato = 'html',
                url_recurso = :act_url,
                content_length = NULL,
                metadata = COALESCE(mr.metadata, '{}'::jsonb)
                    - 'label'
                    - 'anchor_text'
                    - 'source_kind'
                    - 'campaign_evidence_role'
                    - 'capture_date'
                    - 'evidence_scope'
                    - 'boe_id'
                    - 'hash_lineage'
                    - 'recapture_audit'
                    - 'excluded_model_codes',
                row_completeness = NULL,
                row_provenance = NULL
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mr.campana_id = mc.id
              AND am.codigo IN ('182', '184', '195', '199', '282', '345')
              AND mc.campana = '2025'
              AND mc.activo IS true
              AND mr.tipo_recurso = 'normativa_hac_1430_2025'
              AND mr.url_recurso = :url_boe
              AND mr.sha256_contenido = :sha256_contenido
            """
        ),
        {
            "act_url": BOE_ACT_URL,
            "url_boe": BOE_URL,
            "sha256_contenido": BOE_HASH,
        },
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_normativa mn
            USING aeat_modelo am
            WHERE mn.modelo_id = am.id
              AND am.codigo IN ('182', '184', '195', '199', '282', '345')
              AND mn.boe_id = 'BOE-A-2025-25389'
            """
        )
    )
