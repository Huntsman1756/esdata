"""add explicit FATCA reference sources for AEAT 290

Revision ID: 20260525_0102_aeat_290_fatca_reference_sources
Revises: 20260525_0101_aeat_290_remove_legacy_fields
Create Date: 2026-05-25

The active GI38 page links additional FATCA reference material that is important
for MCP answers: TIN validation guidance, the competent-authorities agreement,
the GI38 procedure sheet, and the BOE normative documents. Store those sources
as explicit Modelo 290 resources instead of relying on indirect references in
the GI38 HTML page.

This revision does not promote profile obligations or safe-to-answer flags.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260525_0102_aeat_290_fatca_reference_sources"
down_revision = "20260525_0101_aeat_290_remove_legacy_fields"
branch_labels = None
depends_on = None


CAMPAIGN = "2025"
CAPTURE_DATE = "2026-05-25"

RESOURCE_ROWS = [
    {
        "tipo_recurso": "validaciones_tin_eeuu",
        "formato": "html",
        "url_recurso": (
            "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/"
            "impuestos-tasas/declaraciones-informativas/"
            "modelo-290-decla_____s-determinadas-personas-fatca_/"
            "validaciones-tin-eeuu.html"
        ),
        "sha256_contenido": "d8402a65dabe2f41b0188b247d737e9b976f456ccefed8aa27f379b32aeff0bf",
        "content_length": 5958,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "tin_validation_guidance",
            "page_updated": "2025-07-03",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "acuerdo_autoridades_competentes_fatca",
        "formato": "html",
        "url_recurso": (
            "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/"
            "impuestos-tasas/declaraciones-informativas/"
            "modelo-290-decla_____s-determinadas-personas-fatca_/"
            "acuerdo-autoridades-competentes-reino-unido-eu____.html"
        ),
        "sha256_contenido": "7c0d1d08cb305678b227bc7e037178952f1835c771135944279287563b99890d",
        "content_length": 7173,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "competent_authorities_agreement",
            "page_updated": "2025-07-03",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "ficha_procedimiento_gi38",
        "formato": "html",
        "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/procedimientos/GI38.shtml",
        "sha256_contenido": "31847d653dbe9d02352fa5c2be1ae3bddcd454a44574728c15d84ffdc8d29e71",
        "content_length": 15544,
        "fecha_publicacion_recurso": "2026-05-25",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "procedimiento_aeat_ficha",
            "page_updated": "2026-05-25",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "normativa_acuerdo_espana_eeuu_fatca",
        "formato": "html",
        "url_recurso": "https://www.boe.es/buscar/act.php?id=BOE-A-2014-6854",
        "sha256_contenido": "ec76e834083d046fa96dab718a6b270580abebfb6a813711bec665567d6f2aef",
        "content_length": 162175,
        "fecha_publicacion_recurso": "2014-07-01",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "normativa_boe",
            "boe_id": "BOE-A-2014-6854",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "normativa_orden_hap_1136_2014",
        "formato": "html",
        "url_recurso": "https://www.boe.es/buscar/doc.php?id=BOE-A-2014-6922",
        "sha256_contenido": "76b5497544853f0fb66b0893caa420b349de5d6fb1f262d3975c6282a8f43d6e",
        "content_length": 89374,
        "fecha_publicacion_recurso": "2014-07-02",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "normativa_boe",
            "boe_id": "BOE-A-2014-6922",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "normativa_orden_hap_410_2015",
        "formato": "html",
        "url_recurso": "https://www.boe.es/buscar/doc.php?id=BOE-A-2015-2629",
        "sha256_contenido": "258e4c5a2f92653146ff45969800d5fbfd7591b0e30ebfb15fd3d7c35c822942",
        "content_length": 39508,
        "fecha_publicacion_recurso": "2015-03-12",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "normativa_boe",
            "boe_id": "BOE-A-2015-2629",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "normativa_orden_hap_2783_2015",
        "formato": "html",
        "url_recurso": "https://www.boe.es/buscar/doc.php?id=BOE-A-2015-14021",
        "sha256_contenido": "529c16eff89047ba7df68ad91586cdcef693d16d3a9c1dca646d404af8fbcac8",
        "content_length": 80073,
        "fecha_publicacion_recurso": "2015-12-23",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "normativa_boe",
            "boe_id": "BOE-A-2015-14021",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "normativa_orden_hap_1695_2016",
        "formato": "html",
        "url_recurso": "https://www.boe.es/buscar/doc.php?id=BOE-A-2016-9834",
        "sha256_contenido": "502a67740152eb23bdf66a59c1a2a69d0a34d8e4054b26191bb7dcfef7d05794",
        "content_length": 104850,
        "fecha_publicacion_recurso": "2016-10-27",
        "metadata": {
            "scope": "modelo_290_fatca_reference_sources",
            "source_kind": "normativa_boe",
            "boe_id": "BOE-A-2016-9834",
            "capture_date": CAPTURE_DATE,
        },
    },
]


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _upsert_modelo_recurso(bind, row: dict[str, object]) -> None:
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '290'
                  AND mc.campana = :campaign
                LIMIT 1
            ),
            deactivated AS (
                UPDATE modelo_recurso mr
                SET activa = false,
                    last_seen_at = now()
                FROM target_campaign tc
                WHERE mr.campana_id = tc.campana_id
                  AND mr.tipo_recurso = :tipo_recurso
                  AND mr.activa = true
                  AND mr.sha256_contenido <> :sha256_contenido
                RETURNING mr.id
            ),
            existing AS (
                UPDATE modelo_recurso mr
                SET formato = :formato,
                    url_recurso = :url_recurso,
                    content_length = :content_length,
                    fecha_publicacion_recurso = :fecha_publicacion_recurso,
                    metadata = COALESCE(mr.metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                    row_completeness = 'complete',
                    row_provenance = 'official_exact',
                    activa = true,
                    last_seen_at = now()
                FROM target_campaign tc
                WHERE mr.campana_id = tc.campana_id
                  AND mr.tipo_recurso = :tipo_recurso
                  AND mr.sha256_contenido = :sha256_contenido
                RETURNING mr.id
            )
            INSERT INTO modelo_recurso (
                campana_id,
                tipo_recurso,
                formato,
                url_recurso,
                sha256_contenido,
                content_length,
                fecha_publicacion_recurso,
                metadata,
                row_completeness,
                row_provenance,
                activa,
                first_seen_at,
                last_seen_at
            )
            SELECT
                tc.campana_id,
                :tipo_recurso,
                :formato,
                :url_recurso,
                :sha256_contenido,
                :content_length,
                :fecha_publicacion_recurso,
                CAST(:metadata AS jsonb),
                'complete',
                'official_exact',
                true,
                now(),
                now()
            FROM target_campaign tc
            WHERE NOT EXISTS (SELECT 1 FROM existing)
            """
        ),
        {**row, "campaign": CAMPAIGN, "metadata": _metadata_json(row["metadata"])},
    )


def upgrade() -> None:
    bind = op.get_bind()
    for row in RESOURCE_ROWS:
        _upsert_modelo_recurso(bind, row)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_recurso mr
            USING modelo_campana mc, aeat_modelo am
            WHERE mr.campana_id = mc.id
              AND mc.modelo_id = am.id
              AND am.codigo = '290'
              AND mc.campana = :campaign
              AND mr.metadata ->> 'scope' = 'modelo_290_fatca_reference_sources'
            """
        ),
        {"campaign": CAMPAIGN},
    )
