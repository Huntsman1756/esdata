"""seed complete D-02 intracommunity acquisition relation

Revision ID: 20260523_0086_doctrina_d02_intracomunitaria
Revises: 20260522_0085_doctrina_partial_pilot_relations
Create Date: 2026-05-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260523_0086_doctrina_d02_intracomunitaria"
down_revision = "20260522_0085_doctrina_partial_pilot_relations"
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
                'Curacion D-02: V0963-25 auditada para adquisicion intracomunitaria de bienes; LIVA art. 13 citado en texto oficial'
            FROM documento_interpretativo d
            JOIN norma n ON n.codigo = 'LIVA'
            JOIN articulo a ON a.norma_id = n.id AND a.numero = '13'
            WHERE d.referencia = 'V0963-25'
              AND d.tipo_fuente = 'dgt'
              AND d.row_completeness = 'complete'
              AND d.url_fuente IS NOT NULL
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
                'D-02',
                d.referencia,
                'LIVA',
                '13',
                'IVA',
                '349',
                'adquisicion_intracomunitaria_bienes',
                'modelo_supuesto',
                'manual_official',
                1.00,
                'Curacion D-02 completa acotada a adquisicion intracomunitaria de bienes en V0963-25; no extrapolar a entregas intracomunitarias ni otros supuestos IVA',
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
            WHERE d.referencia = 'V0963-25'
              AND d.tipo_fuente = 'dgt'
              AND d.row_completeness = 'complete'
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


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM criterio_relacion
            WHERE linea_codigo = 'D-02'
              AND documento_referencia = 'V0963-25'
              AND modelo_aeat = '349'
              AND tipo_renta = 'adquisicion_intracomunitaria_bienes'
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
              AND d.referencia = 'V0963-25'
              AND n.codigo = 'LIVA'
              AND a.numero = '13'
              AND da.metodo_enlace = 'manual_official'
              AND da.nota = 'Curacion D-02: V0963-25 auditada para adquisicion intracomunitaria de bienes; LIVA art. 13 citado en texto oficial'
            """
        )
    )
