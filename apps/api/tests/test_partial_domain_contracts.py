import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "workers"))

from db import db_session
from main import app
from sqlalchemy import text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/bde", "/v1/sepblac"])
async def test_partial_document_domains_expose_fail_closed_coverage_contract(path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert "documentos" in payload
    assert "items" in payload
    assert isinstance(payload["total"], int)
    assert payload["coverage_status"] in {"partial_loaded", "workflow_empty"}
    assert payload["safe_to_answer"] is False

    if payload["documentos"]:
        first = payload["documentos"][0]
        assert first["url_fuente"]
        assert first["row_completeness"] == "partial"
        assert first["row_provenance"] == "official_best_effort"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/bdns", "/v1/cendoj"])
async def test_very_limited_document_domains_expose_fail_closed_coverage_contract(path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["total"], int)
    assert payload["coverage_status"] in {"partial_loaded", "very_limited", "workflow_empty"}
    assert payload["safe_to_answer"] is False

    if payload["items"]:
        first = payload["items"][0]
        assert first["url_fuente"]
        assert first["row_completeness"] == "partial"
        assert first["row_provenance"] == "official_best_effort"


@pytest.mark.asyncio
async def test_bdns_structured_rows_expose_partial_loaded_but_still_fail_closed():
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
                    referencia, fecha, titulo, texto, url_fuente,
                    metadata, row_completeness, row_provenance
                )
                VALUES (
                    'convocatoria_bdns', 'BDNS', 'es', 'bdns', 'subvenciones',
                    'BDNS-CONVOCATORIA-909363', '2026-05-31',
                    'Bono Social Termico 2024',
                    'Referencia: BDNS-CONVOCATORIA-909363',
                    'https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/909363',
                    '{"bdns_endpoint":"convocatoria"}',
                    'partial',
                    'official_exact'
                )
                ON CONFLICT (referencia) DO UPDATE SET
                    row_provenance = excluded.row_provenance
                """
            )
        )
        db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/bdns?q=Bono")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_status"] == "partial_loaded"
    assert payload["safe_to_answer"] is False
    assert payload["items"][0]["row_provenance"] == "official_exact"


@pytest.mark.asyncio
async def test_bdns_list_supports_structured_filters_and_pagination():
    with db_session() as db:
        db.execute(
            text(
                """
                INSERT INTO documento_interpretativo (
                    tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
                    referencia, fecha, titulo, texto, url_fuente,
                    metadata, row_completeness, row_provenance
                )
                VALUES (
                    'concesion_bdns', 'BDNS', 'es', 'bdns', 'subvenciones',
                    'BDNS-CONCESION-SB152503817', '2026-05-29',
                    'Ayudas para empresas con actividad en Islas Baleares',
                    'Beneficiario: B57250185 IDEAL SERVICES PROPERTY MANAGEMENT SL',
                    'https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/877699',
                    :metadata,
                    'partial',
                    'official_exact'
                )
                ON CONFLICT (referencia) DO UPDATE SET
                    metadata = excluded.metadata,
                    row_provenance = excluded.row_provenance
                """
            ),
            {
                "metadata": '{"bdns_endpoint":"concesion","beneficiario":"B57250185 IDEAL SERVICES PROPERTY MANAGEMENT SL","numero_convocatoria":"877699","importe":3317.18}'
            },
        )
        db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get(
            "/v1/bdns",
            params={
                "tipo_documento": "concesion_bdns",
                "beneficiario": "IDEAL SERVICES",
                "numero_convocatoria": "877699",
                "importe_min": "3000",
                "limit": "1",
                "offset": "0",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert payload["items"][0]["referencia"] == "BDNS-CONCESION-SB152503817"
