"""curate AEAT IRNR 216/296 inclusion rules

Revision ID: 20260524_0088_aeat_irnr_216_296_rules
Revises: 20260523_0087_doctrina_d04_crs_fatca
Create Date: 2026-05-24

This data migration keeps the already loaded model forms intact and adds the
missing operational layer for IRNR retentions: structured inclusion/exclusion
rules for models 216 and 296, plus fail-closed obligation-profile evidence.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0088_aeat_irnr_216_296_rules"
down_revision = "20260523_0087_doctrina_d04_crs_fatca"
branch_labels = None
depends_on = None


ORDER_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497"
ORDER_MD5 = "068961df0b9a3d1625cf48b130c2f5b4"
CAPTURE_DATE = "2026-05-14"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            WITH active_campaign AS (
                SELECT m.codigo, mc.id AS campana_id
                FROM aeat_modelo m
                JOIN modelo_campana mc ON mc.modelo_id = m.id
                WHERE m.codigo IN ('216', '296')
                  AND mc.activo = true
            ),
            rules AS (
                SELECT *
                FROM (
                    VALUES
                    (
                        '216',
                        'irnr_sin_establecimiento_permanente_retenciones',
                        'CONDICIONAL',
                        'Usar si el sujeto esta obligado a retener o ingresar a cuenta por rentas obtenidas sin mediacion de establecimiento permanente por contribuyentes IRNR.',
                        NULL,
                        'Orden EHA/3290/2008, articulos 1 y 2; TRLIRNR art. 31 y Reglamento IRNR art. 11.'
                    ),
                    (
                        '216',
                        'declaracion_negativa_art31_4',
                        'CONDICIONAL',
                        'Tambien se usa por los obligados cuando no proceda practicar retencion o ingreso a cuenta conforme al TRLIRNR art. 31.4 y exista obligacion de declarar negativa.',
                        NULL,
                        'Orden EHA/3290/2008, articulo 2; TRLIRNR art. 31.4.'
                    ),
                    (
                        '216',
                        'exclusion_iic_y_loterias_apuestas',
                        'EXCLUIR',
                        'No cerrar como Modelo 216 cuando el supuesto corresponda a transmisiones o reembolsos de acciones o participaciones de IIC, o a premios de determinadas loterias y apuestas, porque la propia Orden remite a declaraciones especificas.',
                        NULL,
                        'Orden EHA/3290/2008, articulo 1.'
                    ),
                    (
                        '296',
                        'resumen_anual_retenciones_irnr',
                        'CONDICIONAL',
                        'Declaracion anual para sujetos obligados a retener o efectuar ingreso a cuenta por rentas IRNR sin establecimiento permanente.',
                        NULL,
                        'Orden EHA/3290/2008, articulos 7, 8 y 11; Reglamento IRNR art. 15.'
                    ),
                    (
                        '296',
                        'pagadores_depositarias_gestoras_valores',
                        'CONDICIONAL',
                        'Tambien puede alcanzar a entidades domiciliadas, residentes o representadas en Espana que paguen por cuenta ajena rentas sujetas a retencion o ingreso a cuenta, o que sean depositarias o gestionen el cobro de rentas de valores.',
                        NULL,
                        'Orden EHA/3290/2008, articulo 7.2; Reglamento IRNR art. 15.2.'
                    ),
                    (
                        '296',
                        'exclusion_perceptores_sin_declaracion_negativa',
                        'EXCLUIR',
                        'No incluir en el resumen anual perceptores de rentas excluidas de la obligacion de presentar declaracion negativa de retenciones.',
                        NULL,
                        'Orden EHA/3290/2008, articulo 8.3.'
                    ),
                    (
                        '296',
                        'exclusion_iic_declaracion_anual_especifica',
                        'EXCLUIR',
                        'No cerrar como Modelo 296 el resumen anual de los sujetos obligados por transmisiones o reembolsos de acciones o participaciones de IIC cuando deban efectuar declaracion anual especifica.',
                        NULL,
                        'Orden EHA/3290/2008, articulo 7.1.'
                    )
                ) AS raw(
                    modelo_codigo,
                    supuesto,
                    decision,
                    condicion,
                    umbral,
                    fuente_normativa
                )
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
                active_campaign.campana_id,
                rules.supuesto,
                rules.decision,
                rules.condicion,
                rules.umbral,
                rules.fuente_normativa,
                '{ORDER_URL}',
                '{ORDER_MD5}',
                DATE '{CAPTURE_DATE}'
            FROM rules
            JOIN active_campaign ON active_campaign.codigo = rules.modelo_codigo
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

    op.execute(
        sa.text(
            f"""
            UPDATE obligacion_perfil
            SET
                source_url = '{ORDER_URL}',
                source_hash = '{ORDER_MD5}',
                capture_date = COALESCE(capture_date, DATE '{CAPTURE_DATE}'),
                safe_to_answer = CASE
                    WHEN completeness = 'completa'
                     AND verified = true
                     AND norma_codigo = 'TRLIRNR'
                     AND articulo_referencia = 'art. 31'
                    THEN true
                    ELSE false
                END,
                notas = CASE
                    WHEN modelo_aeat = '296' AND completeness <> 'completa'
                    THEN CONCAT_WS(' ', NULLIF(notas, ''), 'Fail-closed: resumen anual IRNR condicionado a supuesto, tipo de renta y evidencia completa.')
                    ELSE notas
                END
            WHERE modelo_aeat IN ('216', '296');
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM modelo_regla_inclusion
            WHERE supuesto IN (
                'irnr_sin_establecimiento_permanente_retenciones',
                'declaracion_negativa_art31_4',
                'exclusion_iic_y_loterias_apuestas',
                'resumen_anual_retenciones_irnr',
                'pagadores_depositarias_gestoras_valores',
                'exclusion_perceptores_sin_declaracion_negativa',
                'exclusion_iic_declaracion_anual_especifica'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE obligacion_perfil
            SET source_hash = NULL
            WHERE modelo_aeat IN ('216', '296')
              AND source_url = 'https://www.boe.es/buscar/act.php?id=BOE-A-2008-18497'
            """
        )
    )
