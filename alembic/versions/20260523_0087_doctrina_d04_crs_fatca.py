"""curate complete D-04 CRS FATCA relation

Revision ID: 20260523_0087_doctrina_d04_crs_fatca
Revises: 20260523_0086_doctrina_d02_intracomunitaria
Create Date: 2026-05-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260523_0087_doctrina_d04_crs_fatca"
down_revision = "20260523_0086_doctrina_d02_intracomunitaria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO documento_articulo (
                documento_id, articulo_id, metodo_enlace, confianza_enlace, nota
            )
            SELECT
                d.id,
                a.id,
                'manual_official',
                1.00,
                'Curacion D-04: V0138-24 auditada para CRS/FATCA; LGT disposicion adicional vigesimo segunda citada en texto oficial'
            FROM documento_interpretativo d
            JOIN norma n ON n.codigo = 'LGT'
            JOIN articulo a ON a.norma_id = n.id AND a.numero = 'vigésimo segunda'
            WHERE d.referencia = 'V0138-24'
              AND d.tipo_fuente = 'dgt'
              AND d.row_completeness = 'complete'
              AND d.url_fuente IS NOT NULL
              AND d.texto ILIKE '%modelo 289%'
              AND d.texto ILIKE '%Real Decreto 1021/2015%'
              AND (
                  d.texto ILIKE '%Disposición adicional vigésima segunda%'
                  OR d.texto ILIKE '%disposicion adicional vigesima segunda%'
              )
            ON CONFLICT (documento_id, articulo_id)
            DO UPDATE SET
                metodo_enlace = EXCLUDED.metodo_enlace,
                confianza_enlace = EXCLUDED.confianza_enlace,
                nota = EXCLUDED.nota
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
                'LGT',
                'vigésimo segunda',
                'informacion_fiscal',
                '289',
                'crs_fatca',
                'modelo_supuesto',
                'manual_official',
                1.00,
                'Curacion D-04 completa acotada a CRS/FATCA y modelo 289 en V0138-24; no usar como procedimiento completo de reporte',
                d.url_fuente,
                sr.content_hash_sha256,
                sr.fetched_at,
                true,
                'complete'
            FROM documento_interpretativo d
            JOIN source_revision sr
              ON sr.source_entity_id = d.referencia
             AND LOWER(sr.source_entity_tipo) IN (
                 'consulta', 'consulta_vinculante', 'documento', 'resolucion_teac'
             )
            WHERE d.referencia = 'V0138-24'
              AND d.tipo_fuente = 'dgt'
              AND d.row_completeness = 'complete'
              AND d.url_fuente IS NOT NULL
              AND sr.content_hash_sha256 IS NOT NULL
              AND sr.fetched_at IS NOT NULL
              AND d.texto ILIKE '%modelo 289%'
              AND d.texto ILIKE '%Real Decreto 1021/2015%'
              AND (
                  d.texto ILIKE '%Disposición adicional vigésima segunda%'
                  OR d.texto ILIKE '%disposicion adicional vigesima segunda%'
              )
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


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE criterio_relacion
            SET norma_codigo = NULL,
                articulo = NULL,
                impuesto = 'informacion_fiscal',
                metodo_enlace = 'manual_official',
                confianza_enlace = 1.00,
                nota_limitacion = 'Curacion D-04 parcial: V0138-24 menciona CRS/FATCA y modelo 289, sin articulo/supuesto normalizado ni vigencia cerrada',
                verified = true,
                completeness = 'partial',
                updated_at = now()
            WHERE linea_codigo = 'D-04'
              AND documento_referencia = 'V0138-24'
              AND modelo_aeat = '289'
              AND tipo_renta = 'crs_fatca'
              AND relacion = 'modelo_supuesto'
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM documento_articulo da
            USING documento_interpretativo d, articulo a, norma n
            WHERE da.documento_id = d.id
              AND da.articulo_id = a.id
              AND a.norma_id = n.id
              AND d.referencia = 'V0138-24'
              AND n.codigo = 'LGT'
              AND a.numero = 'vigésimo segunda'
              AND da.metodo_enlace = 'manual_official'
              AND da.nota = 'Curacion D-04: V0138-24 auditada para CRS/FATCA; LGT disposicion adicional vigesimo segunda citada en texto oficial'
            """
        )
    )
