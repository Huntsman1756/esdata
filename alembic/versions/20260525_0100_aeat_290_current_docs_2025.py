"""refresh AEAT 290 current documentation and active campaign

Revision ID: 20260525_0100_aeat_290_current_docs_2025
Revises: 20260525_0099_obligacion_perfil_recover_200
Create Date: 2026-05-25

GI38 contains historical FATCA years such as 2013, but the current AEAT
presentation period on 2026-05-25 is for financial information from the
immediately previous year. This revision makes campaign 2025 the active
Modelo 290 campaign and records the current official AEAT documentation.

This deliberately does not promote obligacion_perfil rows to verified/safe.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260525_0100_aeat_290_current_docs_2025"
down_revision = "20260525_0099_obligacion_perfil_recover_200"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-05-25"
CAMPAIGN = "2025"

GI38_URL = "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI38.shtml"
PLAZOS_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/"
    "impuestos-tasas/declaraciones-informativas/"
    "modelo-290-decla_____s-determinadas-personas-fatca_/plazos-presentacion.html"
)
FAQ_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/"
    "impuestos-tasas/declaraciones-informativas/"
    "modelo-290-decla_____s-determinadas-personas-fatca_/preguntas-frecuentes.html"
)
PRESENTACION_WS_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/"
    "impuestos-tasas/declaraciones-informativas/"
    "modelo-290-decla_____s-determinadas-personas-fatca_/"
    "informacion-sobre-presentacion-mediante-web-service.html"
)
CONSULTA_ERRORES_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/"
    "impuestos-tasas/declaraciones-informativas/"
    "modelo-290-decla_____s-determinadas-personas-fatca_/"
    "informacion-sobre-consulta-errores-mediante-service.html"
)
XSD_WSDL_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/"
    "Procedimiento_ayuda/GI38/Ayuda/XSD_WSDL/290_XSD_2.0_WSDL_2.1.1.zip"
)
MANUAL_PRESENTACION_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/"
    "Procedimiento_ayuda/GI38/Ayuda/FATCA-Presentac_290_SWeb_2.16.pdf"
)
ERRORES_WSDL_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/"
    "Procedimiento_ayuda/GI38/Ayuda/WS_consulta_errores_290.zip"
)
ERRORES_MANUAL_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/"
    "Procedimiento_ayuda/GI38/Ayuda/DescargaErroresPresentacion290.pdf"
)
ERRORES_XML_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/"
    "Procedimiento_ayuda/GI38/Ayuda/ARESErroresFATCAV1Sal_Ejemplo.xml"
)
ORDEN_MODELO_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2014-6922"


RESOURCE_ROWS = [
    {
        "tipo_recurso": "procedimiento_gi38",
        "formato": "html",
        "url_recurso": GI38_URL,
        "sha256_contenido": "f90d2f6328c3bdcb305b18e4de5f0f0bce0b6b81c0eae321dea47ad6185e9b21",
        "content_length": 41032,
        "fecha_publicacion_recurso": "2026-05-25",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "procedimiento_aeat",
            "page_updated": "2026-05-25",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "plazos_presentacion",
        "formato": "html",
        "url_recurso": PLAZOS_URL,
        "sha256_contenido": "b99ffc04e8c37edf61f2beae12876bf3ea2e6599f818311376a0f32a329c3311",
        "content_length": 5575,
        "fecha_publicacion_recurso": "2025-12-01",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "plazos_presentacion",
            "presentation_window": "2026-01-01/2026-06-01",
            "reported_financial_year": CAMPAIGN,
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "faq_fatca",
        "formato": "html",
        "url_recurso": FAQ_URL,
        "sha256_contenido": "e206655ab2963f8d2d706764a6c6e33fbc9d29afc7e0f2b261cf095e0b4537ae",
        "content_length": 40706,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "faq_fatca",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "ayuda_tecnica_presentacion",
        "formato": "html",
        "url_recurso": PRESENTACION_WS_URL,
        "sha256_contenido": "6a38830731c80a34c41416a4845532c2b8068a60722b3ed00f298837c86036cb",
        "content_length": 11243,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "ayuda_tecnica_presentacion",
            "xsd_version": "2.0",
            "wsdl_version": "2.1.1",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "diseno_registro_xsd",
        "formato": "zip",
        "url_recurso": XSD_WSDL_URL,
        "sha256_contenido": "b816f86d4778b858b87ac63a6926297b9170d91473af3285d513b8389bf20a59",
        "content_length": 23153,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "xsd_wsdl",
            "xsd_version": "2.0",
            "wsdl_version": "2.1.1",
            "xsd_fields_verified": 152,
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "manual_servicio_web",
        "formato": "pdf",
        "url_recurso": MANUAL_PRESENTACION_URL,
        "sha256_contenido": "91033373633a7e6e3e9aa65e6081fe8cd53abdfb0d2b95303a8a27e57d049431",
        "content_length": 1660146,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "manual_servicio_web",
            "manual_version": "2.16",
            "manual_date": "2023-03-15",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "ayuda_tecnica_consulta_errores",
        "formato": "html",
        "url_recurso": CONSULTA_ERRORES_URL,
        "sha256_contenido": "5cedde010fca6e601b60394d6f354152a65483283d168cff2001bb6a4a8f6f55",
        "content_length": 6715,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "ayuda_tecnica_consulta_errores",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "consulta_errores_wsdl",
        "formato": "zip",
        "url_recurso": ERRORES_WSDL_URL,
        "sha256_contenido": "6b2cfad94e35c412ddf00ae5e5b34e8de738fff301a462a7fb6f87d506752c42",
        "content_length": 13787,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "consulta_errores_wsdl",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "consulta_errores_manual",
        "formato": "pdf",
        "url_recurso": ERRORES_MANUAL_URL,
        "sha256_contenido": "0f54272cf0bc49ed86301e615521f0490eaa2e8a990476e368e9f99c26002d79",
        "content_length": 202124,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "consulta_errores_manual",
            "capture_date": CAPTURE_DATE,
        },
    },
    {
        "tipo_recurso": "consulta_errores_ejemplo_xml",
        "formato": "xml",
        "url_recurso": ERRORES_XML_URL,
        "sha256_contenido": "76e57d25092922096d99d2f741677870f9d3e548077d905f65b7b9cb19dfcc67",
        "content_length": 6366,
        "fecha_publicacion_recurso": "2025-07-03",
        "metadata": {
            "scope": "modelo_290_current_docs",
            "source_kind": "consulta_errores_ejemplo_xml",
            "capture_date": CAPTURE_DATE,
        },
    },
]


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _ensure_model_and_campaign(bind) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo, updated_at)
            VALUES (
                '290',
                'Modelo 290. Declaracion informativa anual de cuentas financieras de determinadas personas estadounidenses (FATCA).',
                'anual',
                'INFORMATIVO',
                :gi38_url,
                true,
                now()
            )
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                periodo = EXCLUDED.periodo,
                impuesto = EXCLUDED.impuesto,
                url_info = EXCLUDED.url_info,
                activo = true,
                derogado_at = NULL,
                updated_at = now()
            """
        ),
        {"gi38_url": GI38_URL},
    )
    bind.execute(
        sa.text(
            """
            UPDATE modelo_campana mc
            SET activo = false,
                updated_at = now()
            FROM aeat_modelo am
            WHERE am.id = mc.modelo_id
              AND am.codigo = '290'
              AND mc.campana <> :campaign
              AND mc.activo = true
            """
        ),
        {"campaign": CAMPAIGN},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO modelo_campana (
                modelo_id,
                campana,
                version_form,
                url_instrucciones,
                url_normativa,
                url_formato,
                activo,
                fecha_publicacion_portal,
                fecha_actualizacion_portal,
                estado_publicacion,
                updated_at
            )
            SELECT
                am.id,
                :campaign,
                'XSD 2.0 / WSDL 2.1.1 / manual 2.16',
                :manual_url,
                :orden_url,
                :xsd_url,
                true,
                DATE '2025-07-03',
                DATE '2026-05-25',
                'publicado',
                now()
            FROM aeat_modelo am
            WHERE am.codigo = '290'
            ON CONFLICT (modelo_id, campana) DO UPDATE SET
                version_form = EXCLUDED.version_form,
                url_instrucciones = EXCLUDED.url_instrucciones,
                url_normativa = EXCLUDED.url_normativa,
                url_formato = EXCLUDED.url_formato,
                activo = true,
                fecha_publicacion_portal = EXCLUDED.fecha_publicacion_portal,
                fecha_actualizacion_portal = EXCLUDED.fecha_actualizacion_portal,
                estado_publicacion = EXCLUDED.estado_publicacion,
                updated_at = now()
            """
        ),
        {
            "campaign": CAMPAIGN,
            "manual_url": MANUAL_PRESENTACION_URL,
            "orden_url": ORDEN_MODELO_URL,
            "xsd_url": XSD_WSDL_URL,
        },
    )


def _upsert_operational_metadata(bind) -> None:
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
            )
            INSERT INTO modelo_campana_operativa (
                campana_id,
                categoria_obligado,
                frecuencia_presentacion,
                ventana_presentacion,
                canal_presentacion,
                obligados_resumen,
                plazo_resumen,
                presentacion_resumen,
                norma_base,
                nota,
                origen_metadato,
                estado_metadato,
                completeness_estado,
                actualizado_at
            )
            SELECT
                tc.campana_id,
                'institucion_financiera_fatca',
                'anual',
                '2026-01-01/2026-06-01',
                'servicio_web',
                'Instituciones financieras espanolas obligadas a comunicar informacion FATCA cuando existan cuentas estadounidenses sujetas a comunicacion.',
                'Del 1 de enero al 1 de junio de 2026, respecto de informacion financiera del ano inmediato anterior.',
                'Presentacion mediante servicio web; XSD 2.0 y WSDL 2.1.1 vigentes en la ayuda tecnica AEAT.',
                'Orden HAP/1136/2014 y Acuerdo FATCA Espana-Estados Unidos.',
                'Documentacion AEAT GI38 vigente capturada el 2026-05-25. La completitud se limita al contrato documental del modelo; no verifica aplicabilidad por perfil en obligacion_perfil.',
                'aeat_gi38_current_docs',
                'curado',
                'completa',
                now()
            FROM target_campaign tc
            ON CONFLICT (campana_id) DO UPDATE SET
                categoria_obligado = EXCLUDED.categoria_obligado,
                frecuencia_presentacion = EXCLUDED.frecuencia_presentacion,
                ventana_presentacion = EXCLUDED.ventana_presentacion,
                canal_presentacion = EXCLUDED.canal_presentacion,
                obligados_resumen = EXCLUDED.obligados_resumen,
                plazo_resumen = EXCLUDED.plazo_resumen,
                presentacion_resumen = EXCLUDED.presentacion_resumen,
                norma_base = EXCLUDED.norma_base,
                nota = EXCLUDED.nota,
                origen_metadato = EXCLUDED.origen_metadato,
                estado_metadato = EXCLUDED.estado_metadato,
                completeness_estado = EXCLUDED.completeness_estado,
                actualizado_at = now()
            """
        ),
        {"campaign": CAMPAIGN},
    )


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


def _copy_existing_290_content_to_2025(bind) -> None:
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS target_campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '290'
                  AND mc.campana = :campaign
                LIMIT 1
            ),
            source_rows AS (
                SELECT DISTINCT ON (cs.codigo)
                    tc.target_campana_id,
                    cs.codigo,
                    cs.etiqueta,
                    cs.descripcion,
                    cs.tipo_casilla,
                    cs.pagina,
                    cs.orden,
                    cs.activa
                FROM modelo_casilla cs
                JOIN modelo_campana mc ON mc.id = cs.campana_id
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                CROSS JOIN target_campaign tc
                WHERE am.codigo = '290'
                  AND mc.campana <> :campaign
                  AND cs.activa = true
                ORDER BY cs.codigo, mc.activo DESC, mc.campana DESC, cs.id DESC
            )
            INSERT INTO modelo_casilla (
                campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden, activa
            )
            SELECT
                target_campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden, activa
            FROM source_rows
            ON CONFLICT (campana_id, codigo) DO UPDATE SET
                etiqueta = EXCLUDED.etiqueta,
                descripcion = EXCLUDED.descripcion,
                tipo_casilla = EXCLUDED.tipo_casilla,
                pagina = EXCLUDED.pagina,
                orden = EXCLUDED.orden,
                activa = EXCLUDED.activa
            """
        ),
        {"campaign": CAMPAIGN},
    )
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS target_campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '290'
                  AND mc.campana = :campaign
                LIMIT 1
            ),
            source_rows AS (
                SELECT DISTINCT ON (COALESCE(cl.tipo, cl.tipo_clave, 'CLAVE'), cl.codigo)
                    tc.target_campana_id,
                    cl.codigo,
                    cl.etiqueta,
                    cl.descripcion,
                    cl.tipo_clave,
                    cl.activa,
                    COALESCE(cl.tipo, cl.tipo_clave, 'CLAVE') AS tipo,
                    cl.criterio_aplicacion,
                    cl.exclusiones,
                    cl.source_url,
                    cl.source_hash,
                    cl.capture_date
                FROM modelo_clave cl
                JOIN modelo_campana mc ON mc.id = cl.campana_id
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                CROSS JOIN target_campaign tc
                WHERE am.codigo = '290'
                  AND mc.campana <> :campaign
                  AND cl.activa = true
                ORDER BY COALESCE(cl.tipo, cl.tipo_clave, 'CLAVE'), cl.codigo, mc.activo DESC, mc.campana DESC, cl.id DESC
            )
            INSERT INTO modelo_clave (
                campana_id, codigo, etiqueta, descripcion, tipo_clave, activa,
                tipo, criterio_aplicacion, exclusiones, source_url, source_hash, capture_date
            )
            SELECT
                target_campana_id, codigo, etiqueta, descripcion, tipo_clave, activa,
                tipo, criterio_aplicacion, exclusiones, source_url, source_hash, capture_date
            FROM source_rows
            ON CONFLICT (campana_id, codigo) DO UPDATE SET
                etiqueta = EXCLUDED.etiqueta,
                descripcion = EXCLUDED.descripcion,
                tipo_clave = EXCLUDED.tipo_clave,
                tipo = EXCLUDED.tipo,
                activa = EXCLUDED.activa,
                criterio_aplicacion = EXCLUDED.criterio_aplicacion,
                exclusiones = EXCLUDED.exclusiones,
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date
            """
        ),
        {"campaign": CAMPAIGN},
    )
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS target_campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '290'
                  AND mc.campana = :campaign
                LIMIT 1
            ),
            source_rows AS (
                SELECT DISTINCT ON (mi.seccion, mi.titulo)
                    tc.target_campana_id,
                    mi.seccion,
                    mi.titulo,
                    mi.contenido,
                    mi.orden,
                    mi.texto,
                    mi.casilla_referencia,
                    mi.source_url,
                    mi.source_hash,
                    mi.capture_date
                FROM modelo_instruccion mi
                JOIN modelo_campana mc ON mc.id = mi.campana_id
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                CROSS JOIN target_campaign tc
                WHERE am.codigo = '290'
                  AND mc.campana <> :campaign
                ORDER BY mi.seccion, mi.titulo, mc.activo DESC, mc.campana DESC, mi.id DESC
            )
            INSERT INTO modelo_instruccion (
                campana_id, seccion, titulo, contenido, orden, texto,
                casilla_referencia, source_url, source_hash, capture_date
            )
            SELECT
                target_campana_id, seccion, titulo, contenido, orden, texto,
                casilla_referencia, source_url, source_hash, capture_date
            FROM source_rows
            ON CONFLICT (campana_id, seccion, titulo) DO UPDATE SET
                contenido = EXCLUDED.contenido,
                orden = EXCLUDED.orden,
                texto = EXCLUDED.texto,
                casilla_referencia = EXCLUDED.casilla_referencia,
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date
            """
        ),
        {"campaign": CAMPAIGN},
    )
    bind.execute(
        sa.text(
            """
            WITH target_campaign AS (
                SELECT mc.id AS target_campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '290'
                  AND mc.campana = :campaign
                LIMIT 1
            ),
            source_rows AS (
                SELECT DISTINCT ON (mri.supuesto)
                    tc.target_campana_id,
                    mri.supuesto,
                    mri.decision,
                    mri.condicion,
                    mri.umbral,
                    mri.fuente_normativa,
                    mri.source_url,
                    mri.source_hash,
                    mri.capture_date
                FROM modelo_regla_inclusion mri
                JOIN modelo_campana mc ON mc.id = mri.campana_id
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                CROSS JOIN target_campaign tc
                WHERE am.codigo = '290'
                  AND mc.campana <> :campaign
                ORDER BY mri.supuesto, mc.activo DESC, mc.campana DESC, mri.id DESC
            )
            INSERT INTO modelo_regla_inclusion (
                campana_id, supuesto, decision, condicion, umbral,
                fuente_normativa, source_url, source_hash, capture_date
            )
            SELECT
                target_campana_id, supuesto, decision, condicion, umbral,
                fuente_normativa, source_url, source_hash, capture_date
            FROM source_rows
            ON CONFLICT (campana_id, supuesto) DO UPDATE SET
                decision = EXCLUDED.decision,
                condicion = EXCLUDED.condicion,
                umbral = EXCLUDED.umbral,
                fuente_normativa = EXCLUDED.fuente_normativa,
                source_url = EXCLUDED.source_url,
                source_hash = EXCLUDED.source_hash,
                capture_date = EXCLUDED.capture_date
            """
        ),
        {"campaign": CAMPAIGN},
    )


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_model_and_campaign(bind)
    _upsert_operational_metadata(bind)
    for row in RESOURCE_ROWS:
        _upsert_modelo_recurso(bind, row)
    _copy_existing_290_content_to_2025(bind)


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
              AND mr.metadata ->> 'scope' = 'modelo_290_current_docs'
            """
        ),
        {"campaign": CAMPAIGN},
    )
    bind.execute(
        sa.text(
            """
            UPDATE modelo_campana_operativa mco
            SET completeness_estado = 'parcial',
                nota = COALESCE(NULLIF(nota, ''), 'Reverted 0100 Modelo 290 current-docs marker.'),
                actualizado_at = now()
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE mco.campana_id = mc.id
              AND am.codigo = '290'
              AND mc.campana = :campaign
              AND mco.origen_metadato = 'aeat_gi38_current_docs'
            """
        ),
        {"campaign": CAMPAIGN},
    )
