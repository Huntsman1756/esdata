"""seed partial doctrina pilot relations

Revision ID: 20260522_0085_doctrina_partial_pilot_relations
Revises: 20260521_0084_criterio_relacion_api_rls
Create Date: 2026-05-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0085_doctrina_partial_pilot_relations"
down_revision = "20260521_0084_criterio_relacion_api_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO criterio_relacion (
                linea_codigo, documento_referencia, norma_codigo, articulo,
                impuesto, modelo_aeat, tipo_renta, relacion, metodo_enlace,
                confianza_enlace, nota_limitacion, source_url, source_hash,
                capture_date, verified, completeness
            )
            SELECT
                'D-03',
                d.referencia,
                'LIS',
                '18',
                'IS',
                NULL,
                'operaciones_vinculadas',
                'articulo_supuesto',
                'manual_official',
                1.00,
                'Curacion D-03 parcial: V0144-26 permite anclaje LIS art. 18, sin modelo 232 ni vigencia cerrada',
                d.url_fuente,
                sr.content_hash_sha256,
                sr.fetched_at,
                true,
                'partial'
            FROM documento_interpretativo d
            JOIN source_revision sr
              ON sr.source_entity_id = d.referencia
             AND LOWER(sr.source_entity_tipo) IN (
                 'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
             )
            WHERE d.referencia = 'V0144-26'
              AND d.url_fuente IS NOT NULL
              AND sr.content_hash_sha256 IS NOT NULL
              AND sr.fetched_at IS NOT NULL
            ON CONFLICT (linea_codigo, documento_referencia, modelo_aeat, tipo_renta, relacion)
            DO UPDATE SET
                norma_codigo = EXCLUDED.norma_codigo,
                articulo = EXCLUDED.articulo,
                impuesto = EXCLUDED.impuesto,
                metodo_enlace = EXCLUDED.metodo_enlace,
                confianza_enlace = EXCLUDED.confianza_enlace,
                nota_limitacion = EXCLUDED.nota_limitacion,
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date,
                verified = EXCLUDED.verified,
                completeness = EXCLUDED.completeness,
                updated_at = now()
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO criterio_relacion (
                linea_codigo, documento_referencia, norma_codigo, articulo,
                impuesto, modelo_aeat, tipo_renta, relacion, metodo_enlace,
                confianza_enlace, nota_limitacion, source_url, source_hash,
                capture_date, verified, completeness
            )
            SELECT
                'D-04',
                d.referencia,
                NULL,
                NULL,
                'informacion_fiscal',
                '289',
                'crs_fatca',
                'modelo_supuesto',
                'manual_official',
                1.00,
                'Curacion D-04 parcial: V0138-24 menciona CRS/FATCA y modelo 289, sin articulo/supuesto normalizado ni vigencia cerrada',
                d.url_fuente,
                sr.content_hash_sha256,
                sr.fetched_at,
                true,
                'partial'
            FROM documento_interpretativo d
            JOIN source_revision sr
              ON sr.source_entity_id = d.referencia
             AND LOWER(sr.source_entity_tipo) IN (
                 'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
             )
            WHERE d.referencia = 'V0138-24'
              AND d.url_fuente IS NOT NULL
              AND sr.content_hash_sha256 IS NOT NULL
              AND sr.fetched_at IS NOT NULL
            ON CONFLICT (linea_codigo, documento_referencia, modelo_aeat, tipo_renta, relacion)
            DO UPDATE SET
                impuesto = EXCLUDED.impuesto,
                metodo_enlace = EXCLUDED.metodo_enlace,
                confianza_enlace = EXCLUDED.confianza_enlace,
                nota_limitacion = EXCLUDED.nota_limitacion,
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date,
                verified = EXCLUDED.verified,
                completeness = EXCLUDED.completeness,
                updated_at = now()
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM criterio_relacion
            WHERE (linea_codigo = 'D-03'
                   AND documento_referencia = 'V0144-26'
                   AND tipo_renta = 'operaciones_vinculadas'
                   AND relacion = 'articulo_supuesto')
               OR (linea_codigo = 'D-04'
                   AND documento_referencia = 'V0138-24'
                   AND modelo_aeat = '289'
                   AND tipo_renta = 'crs_fatca'
                   AND relacion = 'modelo_supuesto')
            """
        )
    )
