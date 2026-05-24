"""refresh AEAT 289 documental source evidence

Revision ID: 20260524_0098_aeat_289_documental_source_refresh
Revises: 20260524_0097_aeat_289_metadata_evidence
Create Date: 2026-05-24

This revision records the fresh Sprint 1 documental evidence for Modelo 289:
HAP/1695/2016, GI42, the CRS service-web manual, and the XSD/WSDL ZIP. It also
corrects two XSD field labels that were inconsistent with the official schema.

It deliberately does not promote CRS/DAC2 operational coverage, profile
obligations, safe_to_answer, or completeness_estado.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260524_0098_aeat_289_documental_source_refresh"
down_revision = "20260524_0097_aeat_289_metadata_evidence"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-05-24"

BOE_HAP_1695_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2016-9834"
BOE_HAP_1695_HASH = (
    "502a67740152eb23bdf66a59c1a2a69d0a34d8e4054b26191bb7dcfef7d05794"
)
BOE_RD_1021_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399"
BOE_RD_1021_HASH = (
    "423708790f64e673977e020d223ee8af89e99bea7970d793c998264e0fbc7b75"
)
AEAT_GI42_URL = "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml"
AEAT_GI42_HASH = (
    "1c00efed01d8d917591907c134abdc8dde84d87e51a6b69ca5a6acf830a26e1c"
)
AEAT_CRS_PDF_URL = "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf"
AEAT_CRS_PDF_HASH = (
    "ce76a21a629125961efe6a1ed9800262f4d253ab55c72a7f04e358936a448be3"
)
AEAT_XSD_WSDL_URL = "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/XSD_WSDL/289_XSD_2.0_WSDL_2.0.1.zip"
AEAT_XSD_WSDL_HASH = (
    "6948eec877d04ca637b099f59fa944996aa878c8d68181dfffde87fd056a048d"
)


RESOURCE_ROWS = [
    {
        "tipo_recurso": "normativa_rd_1021",
        "formato": "html",
        "url_recurso": BOE_RD_1021_URL,
        "sha256_contenido": BOE_RD_1021_HASH,
        "content_length": 175668,
        "metadata": {
            "scope": "modelo_289_documental",
            "source_kind": "normativa_base_crs",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "normativa_hap_1695",
        "formato": "html",
        "url_recurso": BOE_HAP_1695_URL,
        "sha256_contenido": BOE_HAP_1695_HASH,
        "content_length": 104850,
        "metadata": {
            "scope": "modelo_289_documental",
            "source_kind": "orden_aprobacion_modelo",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "procedimiento_gi42",
        "formato": "html",
        "url_recurso": AEAT_GI42_URL,
        "sha256_contenido": AEAT_GI42_HASH,
        "content_length": 59174,
        "metadata": {
            "scope": "modelo_289_documental",
            "source_kind": "procedimiento_aeat",
            "capture_date": CAPTURE_DATE,
            "note": "Fresh 2026-05-24 capture supersedes the auxiliary 0097 GI42 hash.",
        },
    },
    {
        "tipo_recurso": "manual_crs_servicio_web",
        "formato": "pdf",
        "url_recurso": AEAT_CRS_PDF_URL,
        "sha256_contenido": AEAT_CRS_PDF_HASH,
        "content_length": 476891,
        "metadata": {
            "scope": "modelo_289_documental",
            "source_kind": "manual_servicio_web",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "xsd_wsdl",
        "formato": "zip",
        "url_recurso": AEAT_XSD_WSDL_URL,
        "sha256_contenido": AEAT_XSD_WSDL_HASH,
        "content_length": 23669,
        "metadata": {
            "scope": "modelo_289_documental",
            "source_kind": "xsd_wsdl",
            "capture_date": CAPTURE_DATE,
            "schema_files": [
                "CrsNtnlPresentation_v2.0.xsd",
                "CrsNtnlReceipt_v2.0.xsd",
                "CrsNtnlTypes_v2.0.xsd",
                "CrsXML_v2.0.xsd",
                "oecdcrstypes_v5.0.xsd",
            ],
        },
    },
]


XSD_FIELD_FIXES = [
    {
        "old_codigo": "XSD:MessageSpec/SendingEntityIN",
        "codigo": "XSD:MessageSpec/SendingCompanyIN",
        "etiqueta": "MessageSpec > SendingCompanyIN",
        "descripcion": (
            "Identificador de la entidad emisora en MessageSpec segun "
            "CrsXML_v2.0.xsd."
        ),
        "orden": 1,
    },
    {
        "old_codigo": "XSD:AccountReport/Payment/AmntEndsmnt",
        "codigo": "XSD:AccountReport/Payment/PaymentAmnt",
        "etiqueta": "AccountReport > Payment > PaymentAmnt",
        "descripcion": (
            "Importe del pago reportado en Payment segun CrsXML_v2.0.xsd."
        ),
        "orden": 20,
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
                WHERE am.codigo = '289'
                ORDER BY mc.activo DESC, mc.campana DESC, mc.id DESC
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
                    metadata = COALESCE(mr.metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
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
                metadata,
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
                CAST(:metadata AS jsonb),
                true,
                now(),
                now()
            FROM target_campaign tc
            WHERE NOT EXISTS (SELECT 1 FROM existing);
            """
        ),
        {**row, "metadata": _metadata_json(row["metadata"])},
    )


def _upsert_xsd_field(bind, row: dict[str, object]) -> None:
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '289'
                ORDER BY mc.activo DESC, mc.campana DESC, mc.id DESC
                LIMIT 1
            )
            INSERT INTO modelo_casilla (
                campana_id,
                codigo,
                etiqueta,
                descripcion,
                tipo_casilla,
                orden,
                activa
            )
            SELECT
                tc.campana_id,
                :codigo,
                :etiqueta,
                :descripcion,
                'diseno_registro_xsd_campo',
                :orden,
                true
            FROM target_campaign tc
            ON CONFLICT (campana_id, codigo) DO UPDATE SET
                etiqueta = EXCLUDED.etiqueta,
                descripcion = EXCLUDED.descripcion,
                tipo_casilla = EXCLUDED.tipo_casilla,
                orden = EXCLUDED.orden,
                activa = EXCLUDED.activa;
            """
        ),
        row,
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_casilla mc
            USING modelo_campana camp
            JOIN aeat_modelo am ON am.id = camp.modelo_id
            WHERE mc.campana_id = camp.id
              AND am.codigo = '289'
              AND mc.codigo = :old_codigo;
            """
        ),
        row,
    )


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            f"""
            INSERT INTO modelo_normativa (
                modelo_id,
                boe_id,
                titulo,
                fecha,
                url_boe,
                resumen
            )
            SELECT
                am.id,
                'BOE-A-2016-9834',
                'Orden HAP/1695/2016 - aprobacion del modelo 289',
                DATE '2016-10-25',
                '{BOE_HAP_1695_URL}',
                'Orden HAP/1695/2016 que aprueba el modelo 289 de declaracion informativa anual de cuentas financieras en el ambito de la asistencia mutua.'
            FROM aeat_modelo am
            WHERE am.codigo = '289'
            ON CONFLICT (modelo_id, boe_id) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                fecha = EXCLUDED.fecha,
                url_boe = EXCLUDED.url_boe,
                resumen = EXCLUDED.resumen;
            """
        )
    )

    bind.execute(
        sa.text(
            f"""
            UPDATE modelo_instruccion mi
            SET source_hash = '{AEAT_GI42_HASH}',
                capture_date = DATE '{CAPTURE_DATE}'
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mi.campana_id = mc.id
              AND am.codigo = '289'
              AND mi.source_url = '{AEAT_GI42_URL}'
              AND (
                  mi.source_hash IS NULL
                  OR mi.source_hash <> '{AEAT_GI42_HASH}'
                  OR mi.capture_date IS NULL
              );
            """
        )
    )

    for row in RESOURCE_ROWS:
        _upsert_modelo_recurso(bind, row)

    for row in XSD_FIELD_FIXES:
        _upsert_xsd_field(bind, row)


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            f"""
            DELETE FROM modelo_normativa mn
            USING aeat_modelo am
            WHERE mn.modelo_id = am.id
              AND am.codigo = '289'
              AND mn.boe_id = 'BOE-A-2016-9834'
              AND mn.url_boe = '{BOE_HAP_1695_URL}';
            """
        )
    )

    bind.execute(
        sa.text(
            f"""
            UPDATE modelo_instruccion mi
            SET source_hash = NULL
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mi.campana_id = mc.id
              AND am.codigo = '289'
              AND mi.source_url = '{AEAT_GI42_URL}'
              AND mi.source_hash = '{AEAT_GI42_HASH}';
            """
        )
    )

    for row in RESOURCE_ROWS:
        bind.execute(
            sa.text(
                """
                DELETE FROM modelo_recurso mr
                USING modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE mr.campana_id = mc.id
                  AND am.codigo = '289'
                  AND mr.tipo_recurso = :tipo_recurso
                  AND mr.sha256_contenido = :sha256_contenido;
                """
            ),
            row,
        )

    for row in XSD_FIELD_FIXES:
        bind.execute(
            sa.text(
                """
                DELETE FROM modelo_casilla mc
                USING modelo_campana camp
                JOIN aeat_modelo am ON am.id = camp.modelo_id
                WHERE mc.campana_id = camp.id
                  AND am.codigo = '289'
                  AND mc.codigo = :codigo;
                """
            ),
            row,
        )
