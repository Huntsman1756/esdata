"""add AEAT capital mobiliario 123/124 evidence rules

Revision ID: 20260524_0092_aeat_capital_mobiliario_123_124_rules
Revises: 20260524_0091_aeat_193_domestic_applicability_fail_closed
Create Date: 2026-05-24

This migration persists only the routing-level official scope for Modelos 123
and 124. It does not promote either model to a complete obligation contract.
Rules are inserted only when the active campaign has a cached official AEAT
procedure page with hash and capture timestamp.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0092_aeat_capital_mobiliario_123_124_rules"
down_revision = "20260524_0091_aeat_193_domestic_applicability_fail_closed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE aeat_modelo
            SET impuesto = 'IRPF/IS/IRNR'
            WHERE codigo = '124'
              AND COALESCE(activo, true) = true;
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH active_campaign AS (
                SELECT m.codigo, mc.id AS campana_id
                FROM aeat_modelo m
                JOIN modelo_campana mc ON mc.modelo_id = m.id
                WHERE m.codigo IN ('123', '124')
                  AND COALESCE(m.activo, true) = true
                  AND COALESCE(mc.activo, true) = true
            ),
            official_source AS (
                SELECT DISTINCT ON (ac.codigo)
                    ac.codigo,
                    ac.campana_id,
                    mr.url_recurso AS source_url,
                    mr.sha256_contenido AS source_hash,
                    CAST(mr.last_seen_at AS DATE) AS capture_date
                FROM active_campaign ac
                JOIN modelo_recurso mr ON mr.campana_id = ac.campana_id
                WHERE mr.sha256_contenido IS NOT NULL
                  AND mr.last_seen_at IS NOT NULL
                  AND (
                    (ac.codigo = '123' AND mr.url_recurso LIKE '%GH04.shtml')
                    OR (ac.codigo = '124' AND mr.url_recurso LIKE '%GH05.shtml')
                  )
                ORDER BY ac.codigo, mr.last_seen_at DESC, mr.id DESC
            ),
            rules AS (
                SELECT
                    campana_id,
                    'capital_mobiliario_general_123' AS supuesto,
                    'CONDICIONAL' AS decision,
                    'Modelo 123: retenciones e ingresos a cuenta de IRPF, IS e IRNR con establecimiento permanente sobre determinados rendimientos del capital mobiliario o determinadas rentas. No acredita obligacion concreta sin pagador, perceptor, renta, articulo y exencion/no sujecion si aplica.' AS condicion,
                    NULL::text AS umbral,
                    'Ficha AEAT GH04 Modelo 123.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '123'
                UNION ALL
                SELECT
                    campana_id,
                    'aplicabilidad_no_confirmada_123' AS supuesto,
                    'EVIDENCE_LIMITED' AS decision,
                    'La existencia del Modelo 123 en catalogo, casillas o diseno de registro no permite marcar safe_to_answer=true ni obligacion de perfil sin reglas de inclusion y evidencia de supuesto concreto.' AS condicion,
                    NULL::text AS umbral,
                    'Ficha AEAT GH04 Modelo 123 y contrato interno fail-closed.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '123'
                UNION ALL
                SELECT
                    campana_id,
                    'activos_financieros_124' AS supuesto,
                    'CONDICIONAL' AS decision,
                    'Modelo 124: retenciones e ingresos a cuenta sobre rentas y rendimientos del capital mobiliario derivados de transmision, amortizacion, reembolso, canje o conversion de activos representativos de la captacion y utilizacion de capitales ajenos.' AS condicion,
                    NULL::text AS umbral,
                    'Ficha AEAT GH05 Modelo 124.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '124'
                UNION ALL
                SELECT
                    campana_id,
                    'activos_financieros_no_generico_124' AS supuesto,
                    'EXCLUIR' AS decision,
                    'No ofrecer Modelo 124 como candidato para capital mobiliario residente generico si el supuesto no identifica transmision, amortizacion, reembolso, canje o conversion de activos financieros.' AS condicion,
                    NULL::text AS umbral,
                    'Ficha AEAT GH05 Modelo 124 y contrato interno de routing semantico.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '124'
            )
            INSERT INTO modelo_regla_inclusion (
                campana_id,
                supuesto,
                decision,
                condicion,
                umbral,
                fuente_normativa,
                source_url,
                source_hash,
                capture_date
            )
            SELECT
                campana_id,
                supuesto,
                decision,
                condicion,
                umbral,
                fuente_normativa,
                source_url,
                source_hash,
                capture_date
            FROM rules
            ON CONFLICT (campana_id, supuesto) DO UPDATE SET
                decision = EXCLUDED.decision,
                condicion = EXCLUDED.condicion,
                umbral = EXCLUDED.umbral,
                fuente_normativa = EXCLUDED.fuente_normativa,
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM modelo_regla_inclusion
            WHERE supuesto IN (
                'capital_mobiliario_general_123',
                'aplicabilidad_no_confirmada_123',
                'activos_financieros_124',
                'activos_financieros_no_generico_124'
            );
            """
        )
    )
