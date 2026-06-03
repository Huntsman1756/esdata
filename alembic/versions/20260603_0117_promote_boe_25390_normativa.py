"""promote BOE-A-2025-25390 legal evidence for modelos 270 and 347

Revision ID: 20260603_0117_promote_boe_25390_normativa
Revises: 20260603_0116_promote_boe_25389_normativa
Create Date: 2026-06-03

Promotes the stable recaptured BOE-A-2025-25390 source for models 270 and 347.
Modelo 190 is intentionally excluded because it is already assertable through
the operational lane.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260603_0117_promote_boe_25390_normativa"
down_revision = "20260603_0116_promote_boe_25389_normativa"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-03"
BOE_ID = "BOE-A-2025-25390"
BOE_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-25390"
BOE_ACT_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2025-25390"
BOE_HASH = "800f599e6c90760e13c2b5482328339ad0e9c39a33e5b0e098594c57f52c2f79"
BOE_CONTENT_LENGTH = 60343
TARGET_CODES = ("270", "347")


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = _metadata_json(
        {
            "label": "Orden HAC/1431/2025. Modelos 270 y 347.",
            "anchor_text": "Orden HAC/1431/2025, de 3 de diciembre",
            "source_kind": "legal_campaign_evidence",
            "campaign_evidence_role": "direct_legal",
            "capture_date": CAPTURE_DATE,
            "evidence_scope": "aeat_2025_selected_models_legal_campaign",
            "boe_id": BOE_ID,
            "hash_lineage": "stable_doc_php_recapture",
            "recapture_audit": "docs/operations/boe-recapture-audit/boe_recapture_audit_20260603_203107.json",
            "excluded_model_codes": ["190"],
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
                'BOE-A-2025-25390',
                'Orden HAC/1431/2025 - actualizacion modelos 270 y 347',
                DATE '2025-12-12',
                :url_boe,
                'Orden HAC/1431/2025 que modifica ordenes reguladoras de los modelos 270 y 347. Modelo 190 queda fuera de esta promocion porque ya dispone de carril operativo afirmable.'
            FROM aeat_modelo am
            WHERE am.codigo IN ('270', '347')
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
            SET tipo_recurso = 'normativa_hac_1431_2025',
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
              AND am.codigo IN ('270', '347')
              AND mc.campana = '2025'
              AND mc.activo IS true
              AND mr.tipo_recurso IN ('normativa', 'normativa_hac_1431_2025')
              AND mr.url_recurso LIKE '%BOE-A-2025-25390%'
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
              AND am.codigo IN ('270', '347')
              AND mc.campana = '2025'
              AND mc.activo IS true
              AND mr.tipo_recurso = 'normativa_hac_1431_2025'
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
              AND am.codigo IN ('270', '347')
              AND mn.boe_id = 'BOE-A-2025-25390'
            """
        )
    )
