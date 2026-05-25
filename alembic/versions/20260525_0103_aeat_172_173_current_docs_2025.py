"""refresh AEAT 172/173 current documentation and campaigns

Revision ID: 20260525_0103_aeat_172_173_current_docs_2025
Revises: 20260525_0102_aeat_290_fatca_reference_sources
Create Date: 2026-05-25

The active AEAT GI53/GI54 pages are annual information returns with 2026
presentation windows for the immediately previous financial year. Keep campaign
2025 active and replace stale Modelo 172 schema URLs that no longer resolve.

This deliberately does not promote obligacion_perfil rows to verified/safe.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260525_0103_aeat_172_173_current_docs_2025"
down_revision = "20260525_0102_aeat_290_fatca_reference_sources"
branch_labels = None
depends_on = None


CAMPAIGN = "2025"
CAPTURE_DATE = "2026-05-25"

MODEL_ROWS = {
    "172": {
        "nombre": "Modelo 172. Declaracion informativa sobre saldos en monedas virtuales.",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI53.shtml",
        "version_form": "XSD/WSDL GI53 2024 vigente / presentacion 2026",
        "window": "2026-01-01/2026-02-02",
        "summary": "Declaracion informativa anual sobre saldos en monedas virtuales; plazo 2026 para informacion del ano inmediato anterior.",
    },
    "173": {
        "nombre": "Modelo 173. Declaracion informativa sobre operaciones con monedas virtuales.",
        "url_info": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI54.shtml",
        "version_form": "XSD/WSDL GI54 vigente / presentacion 2026",
        "window": "2026-01-01/2026-02-02",
        "summary": "Declaracion informativa anual sobre operaciones con monedas virtuales; plazo 2026 para informacion del ano inmediato anterior.",
    },
}

RESOURCE_ROWS = {
    "172": [
        {
            "tipo_recurso": "procedimiento_gi53",
            "formato": "html",
            "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI53.shtml",
            "sha256_contenido": "8a4f4567ee092f53a52a51429fe6bf2b2995ef2e73b92db7ff104938fafd49a0",
            "content_length": 38872,
            "fecha_publicacion_recurso": "2026-05-25",
            "metadata": {"source_kind": "procedimiento_aeat", "page_updated": "2026-05-25"},
        },
        {
            "tipo_recurso": "plazos_presentacion",
            "formato": "html",
            "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-172-declaracion-informativa-sobre-virtuales/plazos-presentacion.html",
            "sha256_contenido": "b31e58bef8a30652a7fef62365d5d36783b9b7104c04eea67d6da1716e329459",
            "content_length": 5724,
            "fecha_publicacion_recurso": "2025-12-01",
            "metadata": {"source_kind": "plazos_presentacion", "presentation_window": "2026-01-01/2026-02-02", "reported_financial_year": CAMPAIGN},
        },
        {
            "tipo_recurso": "faq_172_173",
            "formato": "html",
            "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-172-declaracion-informativa-sobre-virtuales/preguntas-frecuentes.html",
            "sha256_contenido": "0cd3647c9fe9218ede77e027e1723080a8b67f8a9bb5eac11a21c4182c18c276",
            "content_length": 26508,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "faq_172_173"},
        },
        {
            "tipo_recurso": "anexo_172",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/Anexo172.pdf",
            "sha256_contenido": "973b0ec9942e050eb0bfac263fda9fe034d0bd7555b619628fdedea3ce942d29",
            "content_length": 285927,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "contenido_declaracion"},
        },
        {
            "tipo_recurso": "faq_172_173_pdf",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/Declaraciones_informativas/2023/Notas_informativas/Preguntas_frecuentes_172_173.pdf",
            "sha256_contenido": "17081619802141e957abd5940d9fd10a58cc54a2c2da11fa089251e088273cb5",
            "content_length": 184986,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "faq_pdf"},
        },
        {
            "tipo_recurso": "descripcion_servicio_web",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/2024/DescripcionServicioWebMod172.pdf",
            "sha256_contenido": "a40f11a0f4996fb98f3b66373938b82dcadb616689f7335c62130e7a9f8e9a52",
            "content_length": 717289,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "manual_servicio_web"},
        },
        {
            "tipo_recurso": "diseno_registro_xsd",
            "formato": "zip",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/2024/Esquemas_WSDL_servicios_web.zip",
            "sha256_contenido": "2b28019b20d8d2c83174e331e1a3125f186787a0f1d346ea0095066a8373f394",
            "content_length": 7266,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "xsd_wsdl", "xsd_fields_verified": 35, "replaces_404_url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/Esquemas172.zip"},
        },
        {
            "tipo_recurso": "validaciones_errores",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/2024/Validaciones_errores_Mod172.pdf",
            "sha256_contenido": "14b108af99cd99933a228eedf4284b5b300dc858dd8bcfef41084d0280c150c0",
            "content_length": 267185,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "validaciones_errores"},
        },
    ],
    "173": [
        {
            "tipo_recurso": "procedimiento_gi54",
            "formato": "html",
            "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI54.shtml",
            "sha256_contenido": "211a6c1ce6074a57dbb5e978d513c8e3e0f63e53bf0c397b056a30693cf9e5fe",
            "content_length": 37349,
            "fecha_publicacion_recurso": "2026-05-25",
            "metadata": {"source_kind": "procedimiento_aeat", "page_updated": "2026-05-25"},
        },
        {
            "tipo_recurso": "plazos_presentacion",
            "formato": "html",
            "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-173-decla_____nformativa-sobre-operaciones-virtuales/plazos-presentacion.html",
            "sha256_contenido": "823506f8192bb7b2b9ced993a48f465e83b6fc37f2dad639be251d02283332c9",
            "content_length": 5734,
            "fecha_publicacion_recurso": "2025-12-01",
            "metadata": {"source_kind": "plazos_presentacion", "presentation_window": "2026-01-01/2026-02-02", "reported_financial_year": CAMPAIGN},
        },
        {
            "tipo_recurso": "faq_172_173",
            "formato": "html",
            "url_recurso": "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-172-declaracion-informativa-sobre-virtuales/preguntas-frecuentes.html",
            "sha256_contenido": "0cd3647c9fe9218ede77e027e1723080a8b67f8a9bb5eac11a21c4182c18c276",
            "content_length": 26508,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "faq_172_173"},
        },
        {
            "tipo_recurso": "anexo_173",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI54/Anexo173.pdf",
            "sha256_contenido": "54ea3ae68fa217966c7d667e6f9373bac1d9d8307e3f760b8539af8300a95492",
            "content_length": 536004,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "contenido_declaracion"},
        },
        {
            "tipo_recurso": "faq_172_173_pdf",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/Declaraciones_informativas/2023/Notas_informativas/Preguntas_frecuentes_172_173.pdf",
            "sha256_contenido": "17081619802141e957abd5940d9fd10a58cc54a2c2da11fa089251e088273cb5",
            "content_length": 184986,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "faq_pdf"},
        },
        {
            "tipo_recurso": "descripcion_servicio_web",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI54/Mod173_Descripcion_ServicioWeb.pdf",
            "sha256_contenido": "d2fd943b4b2adfc6e9fd45c6f59106b05bd688ad3fa680995ea70c1d90c59765",
            "content_length": 1251482,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "manual_servicio_web"},
        },
        {
            "tipo_recurso": "diseno_registro_xsd",
            "formato": "zip",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI54/Esquemas173.zip",
            "sha256_contenido": "fc00e59f2064709e6a1032f5fb7d5feef45ec5da7a5a7b54458ac6f990cdb773",
            "content_length": 7451,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "xsd_wsdl", "xsd_fields_verified": 45},
        },
        {
            "tipo_recurso": "validaciones_errores",
            "formato": "pdf",
            "url_recurso": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI54/Mod173-Validaciones-errores.pdf",
            "sha256_contenido": "0c41ec724dae18499ae389ec3dadaef8ede41f549392d15ef6a8057c4965922a",
            "content_length": 89433,
            "fecha_publicacion_recurso": "2025-07-03",
            "metadata": {"source_kind": "validaciones_errores"},
        },
    ],
}


def _metadata_json(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _ensure_model_campaign(bind, codigo: str, info: dict[str, str]) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE aeat_modelo
            SET nombre = :nombre,
                periodo = 'anual',
                impuesto = 'INFORMATIVO',
                url_info = :url_info,
                activo = true,
                derogado_at = NULL,
                updated_at = now()
            WHERE codigo = :codigo
            """
        ),
        {"codigo": codigo, **info},
    )
    bind.execute(
        sa.text(
            """
            UPDATE modelo_campana mc
            SET activo = false,
                updated_at = now()
            FROM aeat_modelo am
            WHERE am.id = mc.modelo_id
              AND am.codigo = :codigo
              AND mc.campana <> :campaign
              AND mc.activo = true
            """
        ),
        {"codigo": codigo, "campaign": CAMPAIGN},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo, updated_at)
            SELECT :codigo, :nombre, 'anual', 'INFORMATIVO', :url_info, true, now()
            WHERE NOT EXISTS (SELECT 1 FROM aeat_modelo WHERE codigo = :codigo)
            """
        ),
        {"codigo": codigo, **info},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO modelo_campana (
                modelo_id, campana, version_form, url_instrucciones, url_formato,
                activo, fecha_publicacion_portal, fecha_actualizacion_portal,
                estado_publicacion, updated_at
            )
            SELECT am.id, :campaign, :version_form, :url_info, :url_info,
                   true, DATE '2025-07-03', DATE '2026-05-25',
                   'publicado', now()
            FROM aeat_modelo am
            WHERE am.codigo = :codigo
            ON CONFLICT (modelo_id, campana) DO UPDATE SET
                version_form = EXCLUDED.version_form,
                url_instrucciones = EXCLUDED.url_instrucciones,
                url_formato = EXCLUDED.url_formato,
                activo = true,
                fecha_publicacion_portal = EXCLUDED.fecha_publicacion_portal,
                fecha_actualizacion_portal = EXCLUDED.fecha_actualizacion_portal,
                estado_publicacion = EXCLUDED.estado_publicacion,
                updated_at = now()
            """
        ),
        {"codigo": codigo, "campaign": CAMPAIGN, **info},
    )


def _copy_existing_fields_to_2025(bind, codigo: str) -> None:
    bind.execute(
        sa.text(
            """
            WITH target AS (
                SELECT mc.id AS target_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = :codigo AND mc.campana = :campaign
            ),
            source_rows AS (
                SELECT DISTINCT ON (cs.codigo)
                    t.target_id, cs.codigo, cs.etiqueta, cs.descripcion,
                    cs.tipo_casilla, cs.pagina, cs.orden, cs.activa
                FROM modelo_casilla cs
                JOIN modelo_campana mc ON mc.id = cs.campana_id
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                CROSS JOIN target t
                WHERE am.codigo = :codigo
                  AND mc.campana <> :campaign
                  AND cs.activa = true
                ORDER BY cs.codigo, mc.activo DESC, mc.campana DESC, cs.id DESC
            )
            INSERT INTO modelo_casilla (
                campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden, activa
            )
            SELECT target_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden, activa
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
        {"codigo": codigo, "campaign": CAMPAIGN},
    )


def _upsert_operational_metadata(bind, codigo: str, info: dict[str, str]) -> None:
    bind.execute(
        sa.text(
            """
            WITH target AS (
                SELECT mc.id AS campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = :codigo AND mc.campana = :campaign
            )
            INSERT INTO modelo_campana_operativa (
                campana_id, categoria_obligado, frecuencia_presentacion,
                ventana_presentacion, canal_presentacion, obligados_resumen,
                plazo_resumen, presentacion_resumen, norma_base, nota,
                origen_metadato, estado_metadato, completeness_estado,
                actualizado_at
            )
            SELECT target.campana_id, 'declarante_modelo_' || :codigo, 'anual',
                   :window, 'servicio_web', :summary,
                   'Del 1 de enero al 2 de febrero de 2026, respecto de informacion del ano inmediato anterior.',
                   'Presentacion mediante servicio web y esquemas oficiales AEAT vigentes.',
                   'Orden HFP/887/2023 y Orden HAC/1504/2024 cuando aplique.',
                   'Documentacion AEAT vigente capturada el 2026-05-25. La completitud se limita al contrato documental del modelo; no verifica aplicabilidad por perfil en obligacion_perfil.',
                   'aeat_current_docs_172_173', 'curado', 'completa', now()
            FROM target
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
        {"codigo": codigo, "campaign": CAMPAIGN, **info},
    )


def _upsert_modelo_recurso(bind, codigo: str, row: dict[str, object]) -> None:
    metadata = {
        **row["metadata"],
        "scope": "modelo_172_173_current_docs",
        "capture_date": CAPTURE_DATE,
    }
    bind.execute(
        sa.text(
            """
            WITH target AS (
                SELECT mc.id AS campana_id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = :codigo AND mc.campana = :campaign
            ),
            deactivated AS (
                UPDATE modelo_recurso mr
                SET activa = false,
                    last_seen_at = now()
                FROM target
                WHERE mr.campana_id = target.campana_id
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
                FROM target
                WHERE mr.campana_id = target.campana_id
                  AND mr.tipo_recurso = :tipo_recurso
                  AND mr.sha256_contenido = :sha256_contenido
                RETURNING mr.id
            )
            INSERT INTO modelo_recurso (
                campana_id, tipo_recurso, formato, url_recurso,
                sha256_contenido, content_length, fecha_publicacion_recurso,
                metadata, row_completeness, row_provenance,
                activa, first_seen_at, last_seen_at
            )
            SELECT target.campana_id, :tipo_recurso, :formato, :url_recurso,
                   :sha256_contenido, :content_length, :fecha_publicacion_recurso,
                   CAST(:metadata AS jsonb), 'complete', 'official_exact',
                   true, now(), now()
            FROM target
            WHERE NOT EXISTS (SELECT 1 FROM existing)
            """
        ),
        {
            **row,
            "codigo": codigo,
            "campaign": CAMPAIGN,
            "metadata": _metadata_json(metadata),
        },
    )


def _deactivate_other_campaigns(bind, codigo: str) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE modelo_campana mc
            SET activo = false,
                updated_at = now()
            FROM aeat_modelo am
            WHERE am.id = mc.modelo_id
              AND am.codigo = :codigo
              AND mc.campana <> :campaign
              AND mc.activo = true
            """
        ),
        {"codigo": codigo, "campaign": CAMPAIGN},
    )


def upgrade() -> None:
    bind = op.get_bind()
    for codigo, info in MODEL_ROWS.items():
        _ensure_model_campaign(bind, codigo, info)
        _copy_existing_fields_to_2025(bind, codigo)
        _upsert_operational_metadata(bind, codigo, info)
        for row in RESOURCE_ROWS[codigo]:
            _upsert_modelo_recurso(bind, codigo, row)
        _deactivate_other_campaigns(bind, codigo)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_recurso mr
            USING modelo_campana mc, aeat_modelo am
            WHERE mr.campana_id = mc.id
              AND mc.modelo_id = am.id
              AND am.codigo IN ('172', '173')
              AND mc.campana = :campaign
              AND mr.metadata ->> 'scope' = 'modelo_172_173_current_docs'
            """
        ),
        {"campaign": CAMPAIGN},
    )
