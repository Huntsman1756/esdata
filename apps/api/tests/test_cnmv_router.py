import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


def _client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_cnmv_buscar_alias_returns_traceable_documents():
    async with _client() as client:
        response = await client.get("/v1/cnmv/buscar?q=circular&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    first = data["documentos"][0]
    assert first["tipo_documento"].startswith("circular")
    assert first["fecha_publicacion"] is not None
    assert first["url_cnmv"] or first["boe_referencia"]
    assert data["vigencia_filter"] == "current"
    assert data["included_estados_vigencia"] == ["vigente", "vigente_modificado"]
    assert "no cargado" in data["coverage_note"]


@pytest.mark.asyncio
async def test_cnmv_coverage_exposes_loaded_subset_and_missing_families():
    async with _client() as client:
        response = await client.get("/v1/cnmv/coverage")

    assert response.status_code == 200
    data = response.json()
    assert data["total_cnmv_loaded"] >= 3
    assert data["current_loaded"] >= 2
    families = {family["family_id"]: family for family in data["source_families"]}
    assert families["circulares"]["loaded_count"] >= 3
    assert families["circulares"]["coverage_status"] == "partial_loaded"
    assert families["guias_tecnicas"]["loaded_count"] >= 1
    assert families["guias_tecnicas"]["coverage_status"] == "partial_loaded"
    assert families["documentos_consulta_cnmv"]["loaded_count"] >= 1
    assert families["documentos_consulta_cnmv"]["coverage_status"] == "partial_loaded"
    assert families["sanciones_cnmv"]["coverage_status"] == "partial_loaded"
    assert families["modelos_normalizados"]["coverage_status"] == "partial_loaded"
    assert "no cargado" in data["coverage_note"]


@pytest.mark.asyncio
async def test_cnmv_source_families_keep_distinct_truth_contracts():
    async with _client() as client:
        guide_response = await client.get(
            "/v1/cnmv/buscar",
            params={"q": "comisiones", "tipo_documento": "guia_tecnica_cnmv"},
        )
        consultation_response = await client.get(
            "/v1/cnmv/buscar",
            params={
                "q": "control interno",
                "tipo_documento": "documento_consulta_cnmv",
                "vigencia": "all",
            },
        )

    assert guide_response.status_code == 200
    guides = guide_response.json()["documentos"]
    assert guides
    assert guides[0]["tipo_documento"] == "guia_tecnica_cnmv"
    assert guides[0]["verified"] is True
    assert guides[0]["completeness"] == "complete"

    assert consultation_response.status_code == 200
    consultations = consultation_response.json()["documentos"]
    assert consultations
    assert consultations[0]["tipo_documento"] == "documento_consulta_cnmv"
    assert consultations[0]["estado_vigencia"] == "consulta_cerrada"
    assert consultations[0]["verified"] is False
    assert consultations[0]["completeness"] == "partial"


@pytest.mark.asyncio
async def test_cnmv_buscar_excludes_derogados_by_default():
    async with _client() as client:
        response = await client.get("/v1/cnmv/buscar?q=circular&limit=50")

    assert response.status_code == 200
    data = response.json()
    estados = {doc["estado_vigencia"] for doc in data["documentos"]}
    referencias = {doc["referencia"] for doc in data["documentos"]}
    assert "derogado" not in estados
    assert "vigente" in estados
    assert "vigente_modificado" in estados
    assert "CNMV-Circular-0-2020" not in referencias
    assert "CNMV-Circular-2-2024" in referencias
    modified = next(doc for doc in data["documentos"] if doc["referencia"] == "CNMV-Circular-2-2024")
    assert modified["es_consolidado"] is False
    assert modified["consolidated_verification_status"] == "not_consolidated"


@pytest.mark.asyncio
async def test_cnmv_buscar_allows_derogados_when_requested():
    async with _client() as client:
        response = await client.get("/v1/cnmv/buscar?q=circular&vigencia=all&limit=50")

    assert response.status_code == 200
    data = response.json()
    estados = {doc["estado_vigencia"] for doc in data["documentos"]}
    referencias = {doc["referencia"] for doc in data["documentos"]}
    assert data["vigencia_filter"] == "all"
    assert data["included_estados_vigencia"] is None
    assert "derogado" in estados
    assert "CNMV-Circular-0-2020" in referencias


@pytest.mark.asyncio
async def test_cnmv_detail_exposes_source_aliases():
    async with _client() as client:
        response = await client.get("/v1/cnmv/CNMV-Circular-1-2025")

    assert response.status_code == 200
    data = response.json()
    assert data["referencia"] == "CNMV-Circular-1-2025"
    assert data["fecha_publicacion"] == "2025-03-05"
    assert data["url_cnmv"] == "https://example.invalid/cnmv/circular-1-2025"
    assert data["boe_referencia"] == "BOE-A-2025-1234"

    async with _client() as client:
        modified_response = await client.get("/v1/cnmv/CNMV-Circular-2-2024")

    assert modified_response.status_code == 200
    modified = modified_response.json()
    assert modified["es_consolidado"] is False
    assert modified["consolidated_verification_status"] == "not_consolidated"
    assert modified["consolidated_source_url"] == "https://www.boe.es/buscar/act.php?id=BOE-A-2024-5678"


@pytest.mark.asyncio
async def test_cnmv_versions_expose_consolidation_audit_metadata():
    async with _client() as client:
        response = await client.get("/v1/cnmv/CNMV-Circular-2-2024/versions")

    assert response.status_code == 200
    data = response.json()
    assert data["referencia"] == "CNMV-Circular-2-2024"
    assert data["total"] == 1
    version = data["versiones"][0]
    assert version["es_consolidado"] is False
    assert version["consolidated_verification_status"] == "not_consolidated"
    assert version["consolidated_source_url"] == "https://www.boe.es/buscar/act.php?id=BOE-A-2024-5678"
    assert version["consolidated_checked_at"] == "2026-05-14T00:00:00Z"
    assert version["consolidated_evidence_note"]
