"""add IRNR 296 income-type rules for dividends and interests

Revision ID: 20260524_0089_aeat_irnr_income_type_rules
Revises: 20260524_0088_aeat_irnr_216_296_rules
Create Date: 2026-05-24

This data migration uses already loaded official Modelo 296 income keys. It
does not make the obligation safe to answer; it only persists traceable
conditional rules for the annual summary by income type.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0089_aeat_irnr_income_type_rules"
down_revision = "20260524_0088_aeat_irnr_216_296_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH active_296 AS (
                SELECT mc.id AS campana_id
                FROM aeat_modelo m
                JOIN modelo_campana mc ON mc.modelo_id = m.id
                WHERE m.codigo = '296'
                  AND COALESCE(m.activo, true) = true
                  AND COALESCE(mc.activo, true) = true
            ),
            source_keys AS (
                SELECT
                    cl.campana_id,
                    cl.codigo,
                    cl.etiqueta,
                    cl.source_url,
                    cl.source_hash,
                    cl.capture_date
                FROM modelo_clave cl
                JOIN active_296 a ON a.campana_id = cl.campana_id
                WHERE COALESCE(cl.activa, true) = true
                  AND COALESCE(cl.tipo, cl.tipo_clave) = 'CLAVE_RENTA'
                  AND cl.codigo IN ('1', '2')
                  AND cl.source_url IS NOT NULL
                  AND cl.source_hash IS NOT NULL
                  AND cl.capture_date IS NOT NULL
            ),
            rules AS (
                SELECT
                    campana_id,
                    CASE codigo
                        WHEN '1' THEN 'tipo_renta_dividendos_irnr_296'
                        WHEN '2' THEN 'tipo_renta_intereses_irnr_296'
                    END AS supuesto,
                    'CONDICIONAL' AS decision,
                    CASE codigo
                        WHEN '1' THEN
                            'Modelo 296 identifica la clave de renta 1 para dividendos y otras rentas derivadas de la participacion en fondos propios de entidades. No determina por si sola retencion efectiva, convenio ni protocolo.'
                        WHEN '2' THEN
                            'Modelo 296 identifica la clave de renta 2 para intereses y otras rentas derivadas de la cesion a terceros de capitales propios. No determina por si sola retencion efectiva, convenio ni protocolo.'
                    END AS condicion,
                    NULL::text AS umbral,
                    CASE codigo
                        WHEN '1' THEN 'Modelo 296, clave de renta 1; Orden EHA/3290/2008.'
                        WHEN '2' THEN 'Modelo 296, clave de renta 2; Orden EHA/3290/2008.'
                    END AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM source_keys
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
            WHERE supuesto IS NOT NULL
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
                'tipo_renta_dividendos_irnr_296',
                'tipo_renta_intereses_irnr_296'
            )
            """
        )
    )
