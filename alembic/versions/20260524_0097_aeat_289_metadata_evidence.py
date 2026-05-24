"""normalize AEAT 289 auxiliary metadata evidence

Revision ID: 20260524_0097_aeat_289_metadata_evidence
Revises: 20260524_0096_obligacion_perfil_recover_111_115
Create Date: 2026-05-24

Modelo 289 already had useful CRS/DAC2 auxiliary rows, but several
modelo_regla_inclusion and modelo_instruccion rows carried official URLs and
capture dates without a normalized hash. This revision only normalizes those
auxiliary evidence fields. It does not promote profile obligations or model
coverage.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0097_aeat_289_metadata_evidence"
down_revision = "20260524_0096_obligacion_perfil_recover_111_115"
branch_labels = None
depends_on = None


BOE_RD_1021_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399"
BOE_RD_1021_HASH = (
    "423708790f64e673977e020d223ee8af89e99bea7970d793c998264e0fbc7b75"
)
AEAT_GI42_URL = "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml"
AEAT_GI42_HASH = (
    "c73351f50935086f4fbeda39d5123563587a6964e2aaa8d254a4ba7b38b4b9a1"
)
AEAT_CRS_PDF_URL = "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf"
AEAT_CRS_PDF_HASH = (
    "ce76a21a629125961efe6a1ed9800262f4d253ab55c72a7f04e358936a448be3"
)
CAPTURE_DATE = "2026-05-24"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE modelo_regla_inclusion mri
            SET
                source_hash = '{BOE_RD_1021_HASH}',
                capture_date = COALESCE(mri.capture_date, DATE '{CAPTURE_DATE}')
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mri.campana_id = mc.id
              AND am.codigo = '289'
              AND mri.source_url = '{BOE_RD_1021_URL}'
              AND (mri.source_hash IS NULL OR mri.capture_date IS NULL);
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            UPDATE modelo_instruccion mi
            SET
                source_hash = CASE
                    WHEN mi.source_url = '{BOE_RD_1021_URL}' THEN '{BOE_RD_1021_HASH}'
                    WHEN mi.source_url = '{AEAT_GI42_URL}' THEN '{AEAT_GI42_HASH}'
                    WHEN mi.source_url = '{AEAT_CRS_PDF_URL}' THEN '{AEAT_CRS_PDF_HASH}'
                    ELSE mi.source_hash
                END,
                capture_date = COALESCE(mi.capture_date, DATE '{CAPTURE_DATE}')
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mi.campana_id = mc.id
              AND am.codigo = '289'
              AND mi.source_url IN (
                  '{BOE_RD_1021_URL}',
                  '{AEAT_GI42_URL}',
                  '{AEAT_CRS_PDF_URL}'
              )
              AND (mi.source_hash IS NULL OR mi.capture_date IS NULL);
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE modelo_regla_inclusion mri
            SET source_hash = NULL
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mri.campana_id = mc.id
              AND am.codigo = '289'
              AND mri.source_url = '{BOE_RD_1021_URL}'
              AND mri.source_hash = '{BOE_RD_1021_HASH}';
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            UPDATE modelo_instruccion mi
            SET source_hash = NULL
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mi.campana_id = mc.id
              AND am.codigo = '289'
              AND (
                  (mi.source_url = '{BOE_RD_1021_URL}' AND mi.source_hash = '{BOE_RD_1021_HASH}')
                  OR (mi.source_url = '{AEAT_GI42_URL}' AND mi.source_hash = '{AEAT_GI42_HASH}')
                  OR (mi.source_url = '{AEAT_CRS_PDF_URL}' AND mi.source_hash = '{AEAT_CRS_PDF_HASH}')
              );
            """
        )
    )
