import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import db_session
from main import app


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _seed_cnmv_perfil_docs():
    with db_session() as db:
        for idx in range(12):
            tipo_documento = "circular_cnmv" if idx < 8 else "guia_tecnica_cnmv"
            db.execute(
                text(
                    """
                    INSERT INTO documento_interpretativo (
                        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                        ambito, referencia, fecha, titulo, texto, url_fuente,
                        estado_vigencia, sujeto_obligado, row_completeness,
                        row_provenance
                    )
                    VALUES (
                        :tipo_documento, 'CNMV', 'es', 'cnmv',
                        'mifid_ii', :referencia, :fecha, :titulo, :texto,
                        :url_fuente, 'vigente', 'sociedad_valores,agencia_valores',
                        'complete', 'official_exact'
                    )
                    ON CONFLICT (referencia) DO UPDATE SET
                        tipo_documento = excluded.tipo_documento,
                        sujeto_obligado = excluded.sujeto_obligado,
                        estado_vigencia = excluded.estado_vigencia,
                        row_completeness = excluded.row_completeness,
                        row_provenance = excluded.row_provenance
                    """
                ),
                {
                    "tipo_documento": tipo_documento,
                    "referencia": f"CNMV-PERFIL-SV-{idx:02d}",
                    "fecha": f"2025-04-{idx + 1:02d}",
                    "titulo": f"Documento CNMV perfil sociedad valores {idx}",
                    "texto": "Documento supervisor CNMV aplicable a sociedad de valores.",
                    "url_fuente": f"https://example.invalid/cnmv/perfil-sv-{idx}",
                },
            )

        for idx in range(2):
            db.execute(
                text(
                    """
                    INSERT INTO documento_interpretativo (
                        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                        ambito, referencia, fecha, titulo, texto, url_fuente,
                        estado_vigencia, sujeto_obligado, row_completeness,
                        row_provenance
                    )
                    VALUES (
                        'guia_tecnica_cnmv', 'CNMV', 'es', 'cnmv',
                        'asesoramiento', :referencia, :fecha, :titulo, :texto,
                        :url_fuente, 'vigente', 'eaf',
                        'complete', 'official_exact'
                    )
                    ON CONFLICT (referencia) DO UPDATE SET
                        sujeto_obligado = excluded.sujeto_obligado,
                        estado_vigencia = excluded.estado_vigencia
                    """
                ),
                {
                    "referencia": f"CNMV-PERFIL-EAF-{idx:02d}",
                    "fecha": f"2025-03-{idx + 1:02d}",
                    "titulo": f"Documento CNMV perfil EAF {idx}",
                    "texto": "Documento supervisor CNMV aplicable a EAF.",
                    "url_fuente": f"https://example.invalid/cnmv/perfil-eaf-{idx}",
                },
            )
        db.commit()


@pytest.mark.asyncio
async def test_cnmv_perfil_sociedad_valores_returns_documents():
    _seed_cnmv_perfil_docs()

    async with _client() as client:
        response = await client.get("/v1/cnmv/perfil/sociedad_valores")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 10
    assert {"referencia", "titulo", "tipo_documento"} <= set(data[0])


@pytest.mark.asyncio
async def test_cnmv_perfil_filters_by_tipo_documento():
    _seed_cnmv_perfil_docs()

    async with _client() as client:
        response = await client.get(
            "/v1/cnmv/perfil/sociedad_valores",
            params={"tipo_documento": "circular_cnmv"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert {item["tipo_documento"] for item in data} == {"circular_cnmv"}


@pytest.mark.asyncio
async def test_cnmv_perfil_eaf_has_narrower_scope_than_sociedad_valores():
    _seed_cnmv_perfil_docs()

    async with _client() as client:
        sv_response = await client.get("/v1/cnmv/perfil/sociedad_valores")
        eaf_response = await client.get("/v1/cnmv/perfil/eaf")

    assert sv_response.status_code == 200
    assert eaf_response.status_code == 200
    assert len(eaf_response.json()) < len(sv_response.json())
