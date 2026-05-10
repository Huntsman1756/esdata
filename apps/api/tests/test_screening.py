"""Tests for screening module — normalizer, schemas, worker data, and API endpoints."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from main import app


# ---------------------------------------------------------------------------
# Helpers — _normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    """Unit tests for the name normalization function used by screening."""

    def setup_method(self):
        from workers.screening import _normalize_name
        self.normalize = _normalize_name

    def test_uppercase_to_lowercase(self):
        assert self.normalize("JOSE LUIS MENDEZ") == "jose luis mendez"

    def test_removes_accents(self):
        assert self.normalize("MARIA TERESA GARCIA LOPEZ") == "maria teresa garcia lopez"

    def test_removes_special_chars(self):
        assert self.normalize("AL-RASHID TRADING COMPANY") == "al rashid trading company"

    def test_removes_punctuation(self):
        assert self.normalize("TRANSFINANCIERA IBERICA SL") == "transfinanciera iberica sl"

    def test_collapses_whitespace(self):
        assert self.normalize("  JOSE    LUIS  ") == "jose luis"

    def test_empty_string(self):
        assert self.normalize("") == ""

    def test_single_word(self):
        assert self.normalize("BBVA") == "bbva"

    def test_numbers_preserved(self):
        assert self.normalize("PETRO-ENERGY INTL 123") == "petro energy intl 123"

    def test_unicode_english(self):
        assert self.normalize("CARLOS RODRIGUEZ FERNANDEZ") == "carlos rodriguez fernandez"


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TestScreeningSchemas:

    def test_screening_check_request_minimal(self):
        from schemas import ScreeningCheckRequest
        req = ScreeningCheckRequest(nombre="TEST COMPANY")
        assert req.nombre == "TEST COMPANY"
        assert req.nif is None
        assert req.empresa_id is None

    def test_screening_check_request_full(self):
        from schemas import ScreeningCheckRequest
        req = ScreeningCheckRequest(
            empresa_id=1,
            nombre="TEST CO",
            nif="B12345678",
            tipo_entidad="entity",
            listas=["OFAC_SDN"],
        )
        assert req.empresa_id == 1
        assert req.listas == ["OFAC_SDN"]

    def test_screening_check_request_empty_nombre_raises(self):
        from schemas import ScreeningCheckRequest
        with pytest.raises(ValidationError):
            ScreeningCheckRequest(nombre="")

    def test_screening_list_schema(self):
        from schemas import ScreeningList
        s = ScreeningList(
            id=1,
            codigo="OFAC_SDN",
            nombre="OFAC Specially Designated Nationals List",
            tipo="sanctions",
            organismo="OFAC",
            activo=True,
        )
        assert s.codigo == "OFAC_SDN"
        assert s.tipo == "sanctions"

    def test_screening_entry_schema(self):
        from schemas import ScreeningEntry, ScreeningList
        lista = ScreeningList(
            id=1, codigo="UN_SANCTIONS", nombre="UN List", tipo="sanctions",
            organismo="UN", activo=True,
        )
        entry = ScreeningEntry(
            id=1,
            entidad_id="UN-40001",
            nombre="AHMED AL-MANSOUR",
            tipo_entidad="person",
            pais="YE",
            nif="YE-8821003",
            aliases=["A. AL-MANSOUR"],
            categorias=["sanctions", "yemen"],
            lista=lista,
        )
        assert entry.entidad_id == "UN-40001"
        assert entry.activo is True  # default

    def test_screening_match_schema(self):
        from schemas import ScreeningMatch, ScreeningEntry, ScreeningList
        lista = ScreeningList(
            id=1, codigo="OFAC_SDN", nombre="OFAC SDN", tipo="sanctions",
            organismo="OFAC", activo=True,
        )
        entry = ScreeningEntry(
            id=1, entidad_id="OFAC-25001", nombre="AL-RASHID TRADING COMPANY",
            tipo_entidad="entity", pais="SY", lista=lista,
        )
        match = ScreeningMatch(
            id=1, empresa_id=1, entry=entry, confianza=0.95,
            motivo="nombre_exacto", match_campo="nombre", revisado=False,
        )
        assert match.confianza == 0.95
        assert match.revisado is False

    def test_screening_check_response(self):
        from schemas import ScreeningCheckResponse
        resp = ScreeningCheckResponse(
            nombre_evaluado="TEST",
            sin_coincidencias=True,
            matches=[],
        )
        assert resp.sin_coincidencias is True

    def test_screening_entries_response(self):
        from schemas import ScreeningEntriesResponse
        resp = ScreeningEntriesResponse(total=10, limit=50, entries=[])
        assert resp.total == 10

    def test_screening_matches_response(self):
        from schemas import ScreeningMatchesResponse
        resp = ScreeningMatchesResponse(empresa_id=1, nombre="TEST SL", matches=[])
        assert resp.empresa_id == 1


# ---------------------------------------------------------------------------
# Worker static data
# ---------------------------------------------------------------------------


class TestScreeningWorkerData:

    def setup_method(self):
        from workers import screening
        self.lists = screening.SCREENING_LISTS
        self.entries = screening.SCREENING_ENTRIES

    def test_lists_count(self):
        assert len(self.lists) == 5

    def test_lists_have_required_fields(self):
        required = {"codigo", "nombre", "tipo", "organismo", "pais", "activo"}
        for lst in self.lists:
            assert required.issubset(lst.keys()), f"Missing fields in {lst['codigo']}"

    def test_lists_types(self):
        tipos = {l["tipo"] for l in self.lists}
        assert "sanctions" in tipos
        assert "pep" in tipos
        assert "watchlist" in tipos

    def test_lists_codes(self):
        codigos = {l["codigo"] for l in self.lists}
        assert codigos == {"OFAC_SDN", "EU_SANCTIONS", "UN_SANCTIONS", "SEPBLAC", "ES_PEPS"}

    def test_entries_count(self):
        assert len(self.entries) == 14

    def test_entries_have_required_fields(self):
        required = {"list_id", "entidad_id", "nombre", "tipo_entidad", "categorias", "activo"}
        for entry in self.entries:
            assert required.issubset(entry.keys()), f"Missing fields in {entry['entidad_id']}"

    def test_entries_by_list(self):
        from collections import Counter
        counts = Counter(e["list_id"] for e in self.entries)
        assert counts["OFAC_SDN"] == 4
        assert counts["EU_SANCTIONS"] == 2
        assert counts["UN_SANCTIONS"] == 2
        assert counts["SEPBLAC"] == 2
        assert counts["ES_PEPS"] == 4

    def test_entries_have_aliases(self):
        for entry in self.entries:
            assert "aliases" in entry

    def test_entries_pais_present(self):
        paises = {e["pais"] for e in self.entries}
        assert "ES" in paises
        assert "SY" in paises
        assert "RU" in paises

    def test_person_entries_have_nif(self):
        for entry in self.entries:
            if entry["tipo_entidad"] == "person":
                assert entry["nif"] is not None

    def test_entity_entries_no_nif(self):
        for entry in self.entries:
            if entry["tipo_entidad"] == "entity":
                assert entry["nif"] is None or entry["nif"].startswith("ES-")

    def test_all_entries_active(self):
        for entry in self.entries:
            assert entry["activo"] is True

    def test_list_ids_reference_valid_lists(self):
        valid_codes = {l["codigo"] for l in self.lists}
        for entry in self.entries:
            assert entry["list_id"] in valid_codes


# ---------------------------------------------------------------------------
# API endpoints (worker data seeded)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_screening_check_missing_body(client):
    """POST /v1/screening/ without required fields should return 400 (nombre defaults to empty)."""
    r = await client.post("/v1/screening/", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_screening_check_empty_nombre(client):
    """POST /v1/screening/ with empty nombre should return 422."""
    r = await client.post("/v1/screening/", json={"nombre": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_screening_entries_list(client):
    """GET /v1/screening/entries should return list of entries."""
    r = await client.get("/v1/screening/entries")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 14
    assert len(data["entries"]) >= 14
    assert "limit" in data


@pytest.mark.asyncio
async def test_screening_entries_filter_by_tipo(client):
    """GET /v1/screening/entries?tipo=pep should return only PEP entries."""
    r = await client.get("/v1/screening/entries?tipo=pep")
    assert r.status_code == 200
    data = r.json()
    for entry in data["entries"]:
        assert entry["lista"]["tipo"] == "pep"


@pytest.mark.asyncio
async def test_screening_entries_filter_by_codigo(client):
    """GET /v1/screening/entries?codigo=OFAC_SDN should return only OFAC entries."""
    r = await client.get("/v1/screening/entries?codigo=OFAC_SDN")
    assert r.status_code == 200
    data = r.json()
    for entry in data["entries"]:
        assert entry["lista"]["codigo"] == "OFAC_SDN"


@pytest.mark.asyncio
async def test_screening_entries_unpopulated_source_is_explicit(client):
    """An empty configured source must not look like a verified no-match result."""
    from db import db_session
    from sqlalchemy import text

    with db_session() as db:
        db.execute(
            text(
                """
                DELETE FROM screening_entries
                WHERE list_id IN (SELECT id FROM screening_lists WHERE codigo = 'EU_SANCTIONS')
                """
            )
        )
        db.commit()

    r = await client.get("/v1/screening/entries?codigo=EU_SANCTIONS")
    assert r.status_code == 200
    data = r.json()
    assert data["availability_status"] == "configured_but_unavailable"
    assert data["safe_to_answer"] is False
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_screening_entries_filter_by_activo(client):
    """GET /v1/screening/entries?activo=false should return 0 entries (all active)."""
    r = await client.get("/v1/screening/entries?activo=false")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_screening_entries_limit(client):
    """GET /v1/screening/entries?limit=5 should return max 5 entries."""
    r = await client.get("/v1/screening/entries?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["entries"]) <= 5


@pytest.mark.asyncio
async def test_screening_entries_limit_max(client):
    """GET /v1/screening/entries?limit=501 should return 422."""
    r = await client.get("/v1/screening/entries?limit=501")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_screening_entries_limit_min(client):
    """GET /v1/screening/entries?limit=0 should return 422."""
    r = await client.get("/v1/screening/entries?limit=0")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_screening_entries_search_q(client):
    """GET /v1/screening/entries?q=al-rashid should find matching entries."""
    r = await client.get("/v1/screening/entries?q=al-rashid")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    nombres = [e["nombre"] for e in data["entries"]]
    assert any("al-rashid" in n.lower() or "al rashid" in n.lower() for n in nombres)


@pytest.mark.asyncio
async def test_screening_entries_search_q_spanish(client):
    """GET /v1/screening/entries?q=rodriguez should find PEP entries."""
    r = await client.get("/v1/screening/entries?q=rodriguez")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_screening_matches_empresa_no_existe(client):
    """GET /v1/screening/matches/999999 should return 404."""
    r = await client.get("/v1/screening/matches/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_screening_matches_empresa_sin_matches(client):
    """GET /v1/screening/matches/1 should return 200 with empty matches for test empresa."""
    r = await client.get("/v1/screening/matches/1")
    assert r.status_code == 200
    data = r.json()
    assert data["empresa_id"] == 1
    assert data["matches"] == []


# ---------------------------------------------------------------------------
# Screening check — DB-dependent tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screening_check_requires_identifier(client):
    """POST /v1/screening/ without nombre, nif or empresa_id should return 400."""
    r = await client.post("/v1/screening/", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_screening_check_with_empresa_id(client):
    """POST /v1/screening/ with empresa_id should return 200."""
    r = await client.post("/v1/screening/", json={"empresa_id": 1})
    assert r.status_code == 200
    data = r.json()
    assert "matches" in data
    assert "sin_coincidencias" in data


@pytest.mark.asyncio
async def test_screening_check_with_nombre(client):
    """POST /v1/screening/ with nombre should return 200."""
    r = await client.post("/v1/screening/", json={"nombre": "TEST COMPANY XYZ"})
    assert r.status_code == 200
    data = r.json()
    assert "matches" in data


@pytest.mark.asyncio
async def test_screening_check_with_nif(client):
    """POST /v1/screening/ with nif should return 200."""
    r = await client.post("/v1/screening/", json={"nif": "B12345678"})
    assert r.status_code == 200
    data = r.json()
    assert "matches" in data


@pytest.mark.asyncio
async def test_screening_check_with_list_filter(client):
    """POST /v1/screening/ with listas filter should return 200."""
    r = await client.post("/v1/screening/", json={
        "nombre": "TEST",
        "listas": ["OFAC_SDN"],
    })
    assert r.status_code == 200
    data = r.json()
    assert "matches" in data


@pytest.mark.asyncio
async def test_screening_check_response_fields(client):
    """POST /v1/screening/ response should have all required fields."""
    r = await client.post("/v1/screening/", json={"nombre": "TEST COMPANY"})
    assert r.status_code == 200
    data = r.json()
    assert "empresa_id" in data
    assert "nombre_evaluado" in data
    assert "matches" in data
    assert "sin_coincidencias" in data


@pytest.mark.asyncio
async def test_screening_entries_response_fields(client):
    """GET /v1/screening/entries response should have required fields."""
    r = await client.get("/v1/screening/entries")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "limit" in data
    assert "entries" in data


@pytest.mark.asyncio
async def test_screening_entry_structure(client):
    """Each screening entry should have the expected structure."""
    r = await client.get("/v1/screening/entries?limit=1")
    assert r.status_code == 200
    data = r.json()
    assert len(data["entries"]) >= 1
    entry = data["entries"][0]
    assert "id" in entry
    assert "entidad_id" in entry
    assert "nombre" in entry
    assert "tipo_entidad" in entry
    assert "lista" in entry
    assert "aliases" in entry
    assert "categorias" in entry


@pytest.mark.asyncio
async def test_screening_list_structure(client):
    """Each screening entry's lista should have the expected structure."""
    r = await client.get("/v1/screening/entries?limit=1")
    assert r.status_code == 200
    data = r.json()
    entry = data["entries"][0]
    lista = entry["lista"]
    assert "codigo" in lista
    assert "nombre" in lista
    assert "tipo" in lista
    assert "organismo" in lista
    assert "activo" in lista
