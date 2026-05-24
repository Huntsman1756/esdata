"""harden AEAT valores 187/198 obligation contract

Revision ID: 20260524_0093_aeat_valores_187_198_contract
Revises: 20260524_0092_aeat_capital_mobiliario_123_124_rules
Create Date: 2026-05-24

Modelos 187 and 198 already have official fields, keys and instructions loaded.
This migration does not change their form-level completeness. It only prevents
legacy profile obligations from remaining safe without hash/capture evidence and
persists routing-level scope rules from cached official AEAT/BOE resources.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0093_aeat_valores_187_198_contract"
down_revision = "20260524_0092_aeat_capital_mobiliario_123_124_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET
                safe_to_answer = false,
                verified = false,
                completeness = 'parcial'
            WHERE modelo_aeat IN ('187', '198')
              AND (source_hash IS NULL OR capture_date IS NULL);
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
                WHERE m.codigo IN ('187', '198')
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
                    (
                      ac.codigo = '187'
                      AND (
                        mr.url_recurso LIKE '%GI07.shtml'
                        OR mr.url_recurso LIKE '%BOE-A-2014-9225%'
                        OR mr.url_recurso LIKE '%DR_Modelo_187%'
                      )
                    )
                    OR (
                      ac.codigo = '198'
                      AND (
                        mr.url_recurso LIKE '%GI17.shtml'
                        OR mr.url_recurso LIKE '%BOE-A-2004-20157%'
                        OR mr.url_recurso LIKE '%DR_Modelo_198%'
                      )
                    )
                  )
                ORDER BY
                    ac.codigo,
                    CASE
                        WHEN mr.tipo_recurso = 'pagina_modelo' THEN 1
                        WHEN mr.tipo_recurso = 'normativa' THEN 2
                        WHEN mr.tipo_recurso = 'diseno_registro' THEN 3
                        ELSE 9
                    END,
                    mr.last_seen_at DESC,
                    mr.id DESC
            ),
            rules AS (
                SELECT
                    campana_id,
                    'iic_transmisiones_reembolsos_187' AS supuesto,
                    'CONDICIONAL' AS decision,
                    'Modelo 187: declaracion informativa de acciones o participaciones representativas del capital o patrimonio de instituciones de inversion colectiva y resumen anual de retenciones e ingresos a cuenta por rentas o ganancias patrimoniales derivadas de transmisiones o reembolsos. No acredita por si solo obligacion de perfil sin operacion, sujeto obligado y retencion/exencion.' AS condicion,
                    NULL::text AS umbral,
                    'Ficha AEAT GI07 y Orden HAP/1608/2014 Modelo 187.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '187'
                UNION ALL
                SELECT
                    campana_id,
                    'iic_obligacion_perfil_no_confirmada_187' AS supuesto,
                    'EVIDENCE_LIMITED' AS decision,
                    'La existencia del Modelo 187, sus casillas, claves o instrucciones no permite marcar obligacion_perfil safe_to_answer=true sin hash/captura y relacion completa con supuesto, sujeto obligado y fuente normativa.' AS condicion,
                    NULL::text AS umbral,
                    'Contrato interno fail-closed para obligaciones de perfil 187.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '187'
                UNION ALL
                SELECT
                    campana_id,
                    'activos_financieros_valores_mobiliarios_198' AS supuesto,
                    'CONDICIONAL' AS decision,
                    'Modelo 198: declaracion anual de operaciones con activos financieros y otros valores mobiliarios. No acredita por si solo obligacion de perfil sin operacion, intermediario/declarado y regla aplicable.' AS condicion,
                    NULL::text AS umbral,
                    'Ficha AEAT GI17 y Orden EHA/3895/2004 Modelo 198.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '198'
                UNION ALL
                SELECT
                    campana_id,
                    'activos_financieros_obligacion_perfil_no_confirmada_198' AS supuesto,
                    'EVIDENCE_LIMITED' AS decision,
                    'La existencia del Modelo 198, sus casillas, claves o instrucciones no permite marcar obligacion_perfil safe_to_answer=true sin hash/captura y relacion completa con supuesto, sujeto obligado y fuente normativa.' AS condicion,
                    NULL::text AS umbral,
                    'Contrato interno fail-closed para obligaciones de perfil 198.' AS fuente_normativa,
                    source_url,
                    source_hash,
                    capture_date
                FROM official_source
                WHERE codigo = '198'
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
                'iic_transmisiones_reembolsos_187',
                'iic_obligacion_perfil_no_confirmada_187',
                'activos_financieros_valores_mobiliarios_198',
                'activos_financieros_obligacion_perfil_no_confirmada_198'
            );
            """
        )
    )
