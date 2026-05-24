"""add Modelo 193 resident income-type rules

Revision ID: 20260524_0090_aeat_193_income_type_rules
Revises: 20260524_0089_aeat_irnr_income_type_rules
Create Date: 2026-05-24

This data migration persists conditional resident income-type rules for
Modelo 193 only when both the perception key and the nature key are already
loaded with official URL, hash and capture date.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0090_aeat_193_income_type_rules"
down_revision = "20260524_0089_aeat_irnr_income_type_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH active_193 AS (
                SELECT mc.id AS campana_id
                FROM aeat_modelo m
                JOIN modelo_campana mc ON mc.modelo_id = m.id
                WHERE m.codigo = '193'
                  AND COALESCE(m.activo, true) = true
                  AND COALESCE(mc.activo, true) = true
            ),
            source_keys AS (
                SELECT
                    cl.campana_id,
                    cl.codigo,
                    COALESCE(cl.tipo, cl.tipo_clave) AS tipo,
                    cl.etiqueta,
                    cl.source_url,
                    cl.source_hash,
                    cl.capture_date
                FROM modelo_clave cl
                JOIN active_193 a ON a.campana_id = cl.campana_id
                WHERE COALESCE(cl.activa, true) = true
                  AND cl.codigo IN (
                      'PERCEPCION_A',
                      'NAT_A_02',
                      'PERCEPCION_B',
                      'NAT_BD_01'
                  )
                  AND cl.source_url IS NOT NULL
                  AND cl.source_hash IS NOT NULL
                  AND cl.capture_date IS NOT NULL
            ),
            dividendos AS (
                SELECT
                    p.campana_id,
                    n.source_url,
                    n.source_hash,
                    n.capture_date
                FROM source_keys p
                JOIN source_keys n ON n.campana_id = p.campana_id
                WHERE p.codigo = 'PERCEPCION_A'
                  AND p.tipo = 'CLAVE_PERCEPCION'
                  AND n.codigo = 'NAT_A_02'
                  AND n.tipo = 'NATURALEZA'
            ),
            intereses AS (
                SELECT
                    p.campana_id,
                    n.source_url,
                    n.source_hash,
                    n.capture_date
                FROM source_keys p
                JOIN source_keys n ON n.campana_id = p.campana_id
                WHERE p.codigo = 'PERCEPCION_B'
                  AND p.tipo = 'CLAVE_PERCEPCION'
                  AND n.codigo = 'NAT_BD_01'
                  AND n.tipo = 'NATURALEZA'
            ),
            rules AS (
                SELECT
                    campana_id,
                    'tipo_renta_dividendos_residentes_193' AS supuesto,
                    'CONDICIONAL' AS decision,
                    'Modelo 193 identifica rendimientos o rentas por participacion en fondos propios mediante PERCEPCION_A y dividendos/participaciones en beneficios mediante NAT_A_02. No determina por si solo obligacion efectiva, exencion, perceptor ni retencion concreta.' AS condicion,
                    NULL::text AS umbral,
                    'Modelo 193, PERCEPCION_A y NAT_A_02.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM dividendos
                UNION ALL
                SELECT
                    campana_id,
                    'tipo_renta_intereses_residentes_193' AS supuesto,
                    'CONDICIONAL' AS decision,
                    'Modelo 193 identifica rendimientos o rentas por cesion a terceros de capitales propios mediante PERCEPCION_B e intereses mediante NAT_BD_01. No determina por si solo obligacion efectiva, exencion, perceptor ni retencion concreta.' AS condicion,
                    NULL::text AS umbral,
                    'Modelo 193, PERCEPCION_B y NAT_BD_01.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM intereses
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
                'tipo_renta_dividendos_residentes_193',
                'tipo_renta_intereses_residentes_193'
            )
            """
        )
    )
