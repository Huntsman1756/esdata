import sys
import tempfile
from decimal import Decimal
from pathlib import Path

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import text

from .conftest import engine

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import app


pytestmark = pytest.mark.usefixtures("xbrl_test_db")


def _load_xbrl_worker_module():
    from apps.workers import xbrl as xbrl_worker

    return xbrl_worker


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _reset_xbrl_tables():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM xbrl_fact"))
        conn.execute(text("DELETE FROM xbrl_filing"))


def _fetch_xbrl_rows():
    with engine.connect() as conn:
        filing = conn.execute(
            text(
                """
                SELECT source_name, source_path, entity_identifier, period_start, period_end, filing_type
                FROM xbrl_filing
                """
            )
        ).mappings().one()
        facts = conn.execute(
            text(
                """
                SELECT concept, value_raw, value_numeric, unit, context_ref, period_start, period_end, entity_identifier, decimals
                FROM xbrl_fact
                ORDER BY concept
                """
            )
        ).mappings().all()

    return dict(filing), [dict(row) for row in facts]


def test_xbrl_worker_parse_fixture_extracts_facts(xbrl_fixture_catalog):
    xbrl = _load_xbrl_worker_module()
    parsed = xbrl.parse_xbrl_fixture(xbrl_fixture_catalog["fixture_path"])

    assert parsed["filing"]["entity_identifier"] == xbrl_fixture_catalog["entity_identifier"]
    assert parsed["filing"]["period_start"] == xbrl_fixture_catalog["filing"]["period_start"]
    assert parsed["filing"]["period_end"] == xbrl_fixture_catalog["filing"]["period_end"]
    assert len(parsed["facts"]) == len(xbrl_fixture_catalog["facts"])

    expected_facts = {fact["concept"]: fact for fact in xbrl_fixture_catalog["facts"]}
    parsed_facts = {fact["concept"]: fact for fact in parsed["facts"]}

    assert parsed_facts.keys() == expected_facts.keys()
    for concept, expected_fact in expected_facts.items():
        assert parsed_facts[concept] == expected_fact


def test_xbrl_worker_load_fixture_persists_rows(xbrl_fixture_catalog):
    _reset_xbrl_tables()
    xbrl = _load_xbrl_worker_module()

    result = xbrl.load_xbrl_fixture(engine=engine, fixture_path=xbrl_fixture_catalog["fixture_path"])
    filing, facts = _fetch_xbrl_rows()

    assert result["filings_upserted"] == 1
    assert result["facts_upserted"] == len(xbrl_fixture_catalog["facts"])
    assert filing == xbrl_fixture_catalog["filing"]
    assert facts == sorted(xbrl_fixture_catalog["facts"], key=lambda fact: fact["concept"])


def test_xbrl_worker_load_fixture_is_idempotent(xbrl_fixture_catalog):
    _reset_xbrl_tables()
    xbrl = _load_xbrl_worker_module()

    xbrl.load_xbrl_fixture(engine=engine, fixture_path=xbrl_fixture_catalog["fixture_path"])
    result = xbrl.load_xbrl_fixture(engine=engine, fixture_path=xbrl_fixture_catalog["fixture_path"])
    filing, facts = _fetch_xbrl_rows()

    assert result["filings_upserted"] == 0
    assert result["facts_upserted"] == 0
    assert filing == xbrl_fixture_catalog["filing"]
    assert facts == sorted(xbrl_fixture_catalog["facts"], key=lambda fact: fact["concept"])


def test_xbrl_worker_parse_fixture_ignores_top_level_elements_without_contextref(xbrl_fixture_catalog):
    xbrl = _load_xbrl_worker_module()
    fixture = Path(tempfile.gettempdir()) / "minimal_with_schema_ref.xbrl"
    fixture.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xbrli:xbrl
    xmlns:xbrli=\"http://www.xbrl.org/2003/instance\"
    xmlns:link=\"http://www.xbrl.org/2003/linkbase\"
    xmlns:iso4217=\"http://www.xbrl.org/2003/iso4217\"
    xmlns:ex=\"http://example.com/xbrl/test\">
  <link:schemaRef xlink:type=\"simple\" xlink:href=\"example.xsd\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" />
  <xbrli:context id=\"ctx_2025\">
    <xbrli:entity>
      <xbrli:identifier scheme=\"http://example.com/entity-id\">ES_TEST_0001</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period>
      <xbrli:startDate>2025-01-01</xbrli:startDate>
      <xbrli:endDate>2025-12-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:unit id=\"EUR\">
    <xbrli:measure>iso4217:EUR</xbrli:measure>
  </xbrli:unit>
  <ex:Revenue contextRef=\"ctx_2025\" unitRef=\"EUR\" decimals=\"0\">1000000</ex:Revenue>
</xbrli:xbrl>
""",
        encoding="utf-8",
    )

    try:
        parsed = xbrl.parse_xbrl_fixture(str(fixture))
    finally:
        fixture.unlink(missing_ok=True)

    assert parsed["filing"]["entity_identifier"] == xbrl_fixture_catalog["entity_identifier"]
    assert parsed["facts"] == [
        {
            "concept": "Revenue",
            "value_raw": "1000000",
            "value_numeric": Decimal("1000000"),
            "unit": "iso4217:EUR",
            "context_ref": "ctx_2025",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "entity_identifier": "ES_TEST_0001",
            "decimals": "0",
        }
    ]


def test_xbrl_fixture_seeded_rows(xbrl_fixture_catalog):
    with engine.connect() as conn:
        filing_count = conn.execute(text("SELECT COUNT(*) FROM xbrl_filing")).scalar_one()
        fact_count = conn.execute(text("SELECT COUNT(*) FROM xbrl_fact")).scalar_one()
        filing = conn.execute(
            text(
                """
                SELECT source_name, source_path, entity_identifier, period_start, period_end, filing_type
                FROM xbrl_filing
                """
            )
        ).mappings().one()
        facts = conn.execute(
            text(
                """
                SELECT concept, value_raw, value_numeric, unit, context_ref, period_start, period_end, entity_identifier, decimals
                FROM xbrl_fact
                ORDER BY concept
                """
            )
        ).mappings().all()

    assert filing_count == 1
    assert fact_count == len(xbrl_fixture_catalog["facts"])
    assert dict(filing) == xbrl_fixture_catalog["filing"]
    assert [dict(row) for row in facts] == sorted(xbrl_fixture_catalog["facts"], key=lambda fact: fact["concept"])


def test_xbrl_tables_exist():
    with engine.connect() as conn:
        filing = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='xbrl_filing'"))
        fact = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='xbrl_fact'"))

    assert filing.scalar_one() == "xbrl_filing"
    assert fact.scalar_one() == "xbrl_fact"


@pytest.mark.asyncio
async def test_xbrl_facts_status_200():
    async with _client() as c:
        r = await c.get("/v1/xbrl/facts")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_xbrl_facts_filter_by_entity_id(xbrl_fixture_catalog):
    async with _client() as c:
        r = await c.get(f"/v1/xbrl/facts?entity_id={xbrl_fixture_catalog['entity_identifier']}")
    assert r.status_code == 200
    data = r.json()
    assert data["entity_id"] == xbrl_fixture_catalog["entity_identifier"]
    assert len(data["facts"]) == len(xbrl_fixture_catalog["facts"])
    expected_facts = {fact["concept"]: fact for fact in xbrl_fixture_catalog["facts"]}
    for fact in data["facts"]:
        assert isinstance(fact["filing_id"], int)
        assert fact["filing_id"] > 0
        expected = expected_facts[fact["concept"]]
        assert fact["value_raw"] == expected["value_raw"]
        assert fact["value_numeric"] == expected["value_numeric"]
        assert fact["unit"] == expected["unit"]
        assert fact["context_ref"] == expected["context_ref"]
        assert fact["period_start"] == expected["period_start"]
        assert fact["period_end"] == expected["period_end"]
        assert fact["entity_identifier"] == expected["entity_identifier"]
        assert fact["decimals"] == expected["decimals"]


@pytest.mark.asyncio
async def test_xbrl_facts_limit_applies_to_response_size():
    async with _client() as c:
        r = await c.get("/v1/xbrl/facts?limit=1")
    assert r.status_code == 200
    data = r.json()
    assert len(data["facts"]) == 1


@pytest.mark.asyncio
async def test_xbrl_facts_limit_rejects_values_above_max():
    async with _client() as c:
        r = await c.get("/v1/xbrl/facts?limit=1001")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_xbrl_facts_filter_by_concept(xbrl_fixture_catalog):
    expected = xbrl_fixture_catalog["facts"][0]
    concept = expected["concept"]

    async with _client() as c:
        r = await c.get(f"/v1/xbrl/facts?concept={concept}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["facts"]) >= 1
    assert all(item["concept"] == concept for item in data["facts"])
    for fact in data["facts"]:
        assert fact["value_raw"] == expected["value_raw"]
        assert fact["value_numeric"] == expected["value_numeric"]
        assert fact["unit"] == expected["unit"]
        assert fact["context_ref"] == expected["context_ref"]
        assert fact["period_start"] == expected["period_start"]
        assert fact["period_end"] == expected["period_end"]
        assert fact["entity_identifier"] == expected["entity_identifier"]
        assert fact["decimals"] == expected["decimals"]


@pytest.mark.asyncio
async def test_xbrl_filing_detail_status_200(xbrl_fixture_catalog):
    with engine.connect() as conn:
        filing_id = conn.execute(text("SELECT id FROM xbrl_filing LIMIT 1")).scalar_one()

    async with _client() as c:
        r = await c.get(f"/v1/xbrl/filings/{filing_id}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_xbrl_filing_detail_structure(xbrl_fixture_catalog):
    with engine.connect() as conn:
        filing_id = conn.execute(text("SELECT id FROM xbrl_filing LIMIT 1")).scalar_one()

    async with _client() as c:
        r = await c.get(f"/v1/xbrl/filings/{filing_id}")
    data = r.json()

    assert "filing" in data
    assert "facts" in data
    assert isinstance(data["filing"], dict)
    assert isinstance(data["facts"], list)

    filing = data["filing"]
    for key in ("id", "source_name", "source_path", "entity_identifier", "period_start", "period_end", "filing_type"):
        assert key in filing, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_xbrl_filing_detail_facts_match(xbrl_fixture_catalog):
    with engine.connect() as conn:
        filing_id = conn.execute(text("SELECT id FROM xbrl_filing LIMIT 1")).scalar_one()

    async with _client() as c:
        r = await c.get(f"/v1/xbrl/filings/{filing_id}")
    data = r.json()

    expected_facts = {fact["concept"]: fact for fact in xbrl_fixture_catalog["facts"]}
    assert len(data["facts"]) == len(xbrl_fixture_catalog["facts"])

    for fact in data["facts"]:
        assert fact["filing_id"] == filing_id
        expected = expected_facts[fact["concept"]]
        assert fact["value_raw"] == expected["value_raw"]
        assert fact["value_numeric"] == expected["value_numeric"]
        assert fact["unit"] == expected["unit"]
        assert fact["concept"] == expected["concept"]


@pytest.mark.asyncio
async def test_xbrl_filing_detail_404_not_found():
    async with _client() as c:
        r = await c.get("/v1/xbrl/filings/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_xbrl_filing_detail_filing_metadata(xbrl_fixture_catalog):
    with engine.connect() as conn:
        filing_id = conn.execute(text("SELECT id FROM xbrl_filing LIMIT 1")).scalar_one()

    async with _client() as c:
        r = await c.get(f"/v1/xbrl/filings/{filing_id}")
    data = r.json()

    expected_filing = xbrl_fixture_catalog["filing"]
    filing = data["filing"]
    assert filing["entity_identifier"] == expected_filing["entity_identifier"]
    assert filing["period_start"] == expected_filing["period_start"]
    assert filing["period_end"] == expected_filing["period_end"]
    assert filing["filing_type"] == expected_filing["filing_type"]


def test_ixbrl_worker_parse_fixture_from_html(xbrl_fixture_catalog):
    xbrl = _load_xbrl_worker_module()
    fixture_path = str(REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.ixbrl")

    parsed = xbrl.parse_filing_fixture(fixture_path)

    assert parsed["filing"]["filing_type"] == "ixbrl"
    assert parsed["filing"]["entity_identifier"] == "ES_TEST_0001"
    assert parsed["filing"]["period_start"] == "2025-01-01"
    assert parsed["filing"]["period_end"] == "2025-12-31"
    assert len(parsed["facts"]) == 3

    concepts = {f["concept"] for f in parsed["facts"]}
    assert concepts == {"Revenue", "ProfitLoss", "Assets"}


def test_ixbrl_worker_derive_filing_type_html():
    xbrl = _load_xbrl_worker_module()
    fixture_path = str(REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.ixbrl")
    assert xbrl._derive_filing_type(fixture_path) == "ixbrl"


def test_ixbrl_worker_derive_filing_type_xbrl():
    xbrl = _load_xbrl_worker_module()
    fixture_path = str(REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.xbrl")
    assert xbrl._derive_filing_type(fixture_path) == "xbrl"


def test_ixbrl_worker_load_fixture_persists_rows():
    _reset_xbrl_tables()
    xbrl = _load_xbrl_worker_module()
    fixture_path = str(REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.ixbrl")

    result = xbrl.load_filing_fixture(engine=engine, fixture_path=fixture_path)
    with engine.connect() as conn:
        filing = conn.execute(text("SELECT * FROM xbrl_filing")).mappings().one()
        facts = conn.execute(text("SELECT * FROM xbrl_fact ORDER BY concept")).mappings().all()

    assert result["filings_upserted"] == 1
    assert result["facts_upserted"] == 3
    assert filing["filing_type"] == "ixbrl"
    assert len(facts) == 3


def test_ixbrl_worker_load_fixture_separate_from_xbrl():
    _reset_xbrl_tables()
    xbrl = _load_xbrl_worker_module()
    xbrl_fixture = str(REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.xbrl")
    ixbrl_fixture = str(REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.ixbrl")

    xbrl.load_filing_fixture(engine=engine, fixture_path=xbrl_fixture)
    xbrl.load_filing_fixture(engine=engine, fixture_path=ixbrl_fixture)

    with engine.connect() as conn:
        filing_count = conn.execute(text("SELECT COUNT(*) FROM xbrl_filing")).scalar_one()
        facts_count = conn.execute(text("SELECT COUNT(*) FROM xbrl_fact")).scalar_one()

    assert filing_count == 2
    assert facts_count == 6


def test_ixbrl_worker_parse_empty_html():
    xbrl = _load_xbrl_worker_module()
    fixture = Path(tempfile.gettempdir()) / "empty_ixbrl.html"
    fixture.write_text("<html><body><p>No xbrl here</p></body></html>", encoding="utf-8")

    try:
        parsed = xbrl.parse_filing_fixture(str(fixture))
    finally:
        fixture.unlink(missing_ok=True)

    assert parsed["filing"]["filing_type"] == "ixbrl"
    assert parsed["filing"]["entity_identifier"] is None
    assert parsed["facts"] == []


@pytest.mark.asyncio
async def test_xbrl_taxonomy_status_200(xbrl_taxonomy_seed):
    async with _client() as c:
        r = await c.get("/v1/xbrl/taxonomy")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert len(data["entries"]) > 0


@pytest.mark.asyncio
async def test_xbrl_taxonomy_filter_by_standard(xbrl_taxonomy_seed):
    async with _client() as c:
        r = await c.get("/v1/xbrl/taxonomy?standard=IAS+1")
    data = r.json()
    assert r.status_code == 200
    assert data["standard"] == "IAS 1"
    for entry in data["entries"]:
        assert entry["standard"] == "IAS 1"


@pytest.mark.asyncio
async def test_xbrl_taxonomy_filter_by_language(xbrl_taxonomy_seed):
    async with _client() as c:
        r = await c.get("/v1/xbrl/taxonomy?language=es")
    data = r.json()
    assert r.status_code == 200
    assert data["language"] == "es"
    for entry in data["entries"]:
        assert entry["label_language"] == "es"


@pytest.mark.asyncio
async def test_xbrl_taxonomy_filter_by_concept(xbrl_taxonomy_seed):
    async with _client() as c:
        r = await c.get("/v1/xbrl/taxonomy?concept=ProfitLoss")
    data = r.json()
    assert r.status_code == 200
    assert data["concept"] == "ProfitLoss"
    for entry in data["entries"]:
        assert "ProfitLoss" in entry["concept_qname"]


@pytest.mark.asyncio
async def test_xbrl_taxonomy_limit_applies(xbrl_taxonomy_seed):
    async with _client() as c:
        r = await c.get("/v1/xbrl/taxonomy?limit=5")
    data = r.json()
    assert r.status_code == 200
    assert len(data["entries"]) <= 5


@pytest.mark.asyncio
async def test_xbrl_taxonomy_limit_rejects_above_max(xbrl_taxonomy_seed):
    async with _client() as c:
        r = await c.get("/v1/xbrl/taxonomy?limit=1001")
    assert r.status_code == 422


def test_xbrl_taxonomy_worker_seed_entries():
    from apps.workers import xbrl_taxonomy as xbrl_tax
    inserted = xbrl_tax.seed_taxonomy(engine=engine)
    assert inserted > 0

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM xbrl_taxonomy")).scalar_one()
    assert count > 0


def test_xbrl_taxonomy_worker_seed_is_idempotent(xbrl_taxonomy_seed):
    from apps.workers import xbrl_taxonomy as xbrl_tax
    inserted_before = xbrl_tax.seed_taxonomy(engine=engine)
    assert inserted_before == 0

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM xbrl_taxonomy")).scalar_one()
    assert count > 0


def test_xbrl_taxonomy_worker_seed_has_english_and_spanish():
    from apps.workers import xbrl_taxonomy as xbrl_tax
    xbrl_tax.seed_taxonomy(engine=engine)

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT label_language, COUNT(*) as cnt FROM xbrl_taxonomy GROUP BY label_language")
        ).mappings().all()

    langs = {row["label_language"]: row["cnt"] for row in rows}
    assert "en" in langs
    assert "es" in langs
    assert langs["en"] > 0
    assert langs["es"] > 0


def test_xbrl_taxonomy_worker_seed_has_multiple_standards():
    from apps.workers import xbrl_taxonomy as xbrl_tax
    xbrl_tax.seed_taxonomy(engine=engine)

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT standard, COUNT(*) as cnt FROM xbrl_taxonomy GROUP BY standard")
        ).mappings().all()

    standards = {row["standard"]: row["cnt"] for row in rows}

    has_ifrs = any("IFRS" in s for s in standards)
    has_ias = any("IAS" in s for s in standards)
    assert has_ifrs or has_ias
    assert "ESEF" in standards


# ---------------------------------------------------------------------------
# Phase 16.5 — pgc_xbrl_mapping worker
# ---------------------------------------------------------------------------


def test_pgc_xbrl_mapping_worker_seeds_mappings():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM pgc_xbrl_mapping")).scalar_one()

    assert count > 0


def test_pgc_xbrl_mapping_worker_is_idempotent(pgc_xbrl_mapping_seed):
    from apps.workers import pgc_xbrl_mapping as mapper

    with engine.connect() as conn:
        count_before = conn.execute(text("SELECT COUNT(*) FROM pgc_xbrl_mapping")).scalar_one()

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        count_after = conn.execute(text("SELECT COUNT(*) FROM pgc_xbrl_mapping")).scalar_one()

    assert count_after == count_before


def test_pgc_xbrl_mapping_worker_has_all_mapping_types():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT mapping_type, COUNT(*) as cnt FROM pgc_xbrl_mapping GROUP BY mapping_type")
        ).mappings().all()

    types = {row["mapping_type"]: row["cnt"] for row in rows}

    assert "direct" in types
    assert "derived" in types
    assert "expert" in types


def test_pgc_xbrl_mapping_worker_has_high_confidence():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM pgc_xbrl_mapping WHERE confidence = 'high'")
        ).scalar_one()

    assert count > 0


def test_pgc_xbrl_mapping_worker_has_all_domains():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    SUM(CASE WHEN xbrl_concept_qname LIKE 'http://xbrl.ifrs.org/taxonomy/%' THEN 1 ELSE 0 END) as ifrs,
                    SUM(CASE WHEN xbrl_concept_qname LIKE 'http://xbrl.esma.europa.eu/%' THEN 1 ELSE 0 END) as esef
                FROM pgc_xbrl_mapping
            """)
        ).mappings().one()

    assert rows["ifrs"] > 0
    assert rows["esef"] > 0


def test_pgc_xbrl_mapping_worker_has_pgc_accounts():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        codes = conn.execute(
            text("SELECT DISTINCT pgc_account_codigo FROM pgc_xbrl_mapping ORDER BY pgc_account_codigo")
        ).mappings().all()

    pgc_codes = {row["pgc_account_codigo"] for row in codes}

    assert "700" in pgc_codes
    assert "572" in pgc_codes
    assert "600" in pgc_codes
    assert "11" in pgc_codes
    assert "300" in pgc_codes


def test_pgc_xbrl_mapping_worker_all_mappings_have_notes():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        null_count = conn.execute(
            text("SELECT COUNT(*) FROM pgc_xbrl_mapping WHERE note IS NULL")
        ).scalar_one()

    assert null_count == 0


def test_pgc_xbrl_mapping_worker_all_mappings_active():
    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)

    with engine.connect() as conn:
        inactive = conn.execute(
            text("SELECT COUNT(*) FROM pgc_xbrl_mapping WHERE is_active = false")
        ).scalar_one()

    assert inactive == 0


# ---------------------------------------------------------------------------
# Phase 16.6 — XBRL fact -> PGC account mapping (enriched-facts endpoint)
# ---------------------------------------------------------------------------


def _seed_enriched_fact(engine, concept_qname, value_raw="999999"):
    """Seed a single xbrl_fact with a given concept QName that will match PGC mappings."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM xbrl_fact")
        )
        conn.execute(
            text("DELETE FROM xbrl_filing")
        )
        conn.execute(
            text(
                """
                INSERT INTO xbrl_filing (source_name, source_path, entity_identifier, period_start, period_end, filing_type)
                VALUES ('enriched_test', '/tmp/enriched_test.xbrl', 'ES_TEST_0001', '2025-01-01', '2025-12-31', 'xbrl')
                """
            )
        )
        filing_id = conn.execute(
            text("SELECT id FROM xbrl_filing WHERE source_path = '/tmp/enriched_test.xbrl'")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO xbrl_fact (filing_id, concept, value_raw, value_numeric, unit, context_ref, period_start, period_end, entity_identifier, decimals)
                VALUES (:filing_id, :concept, :value_raw, :value_numeric, :unit, :ctx, :ps, :pe, :ei, :dec)
                """
            ),
            {
                "filing_id": filing_id,
                "concept": concept_qname,
                "value_raw": value_raw,
                "value_numeric": 999999,
                "unit": "iso4217:EUR",
                "ctx": "ctx_2025",
                "ps": "2025-01-01",
                "pe": "2025-12-31",
                "ei": "ES_TEST_0001",
                "dec": "0",
            },
        )


def test_enriched_facts_endpoint_returns_all_facts(pgc_xbrl_enriched_db):
    """All facts returned when no filters applied, even those without PGC mapping."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts")
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) >= 1
    fact = data["facts"][0]
    assert fact["concept"] == "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue"
    assert fact["value_raw"] == "999999"
    assert fact["pgc_account_codigo"] is not None
    assert fact["mapping_confidence"] is not None


def test_enriched_facts_returns_none_when_no_mapping(pgc_xbrl_enriched_db):
    """Fact with a concept that has no PGC mapping returns null mapping fields."""
    _seed_enriched_fact(
        engine,
        "http://example.com/nonexistent/Concept",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts")
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) == 1
    fact = data["facts"][0]
    assert fact["pgc_account_codigo"] is None
    assert fact["mapping_confidence"] is None
    assert fact["mapping_type"] is None
    assert fact["mapping_note"] is None


def test_enriched_facts_filter_by_entity_id(pgc_xbrl_enriched_db):
    """Filter by entity_id returns only matching facts."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts", params={"entity_id": "ES_TEST_0001"})
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) >= 1
    assert data["facts"][0]["entity_identifier"] == "ES_TEST_0001"


def test_enriched_facts_filter_by_concept(pgc_xbrl_enriched_db):
    """Filter by concept returns only matching facts."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts", params={"concept": "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue"})
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) >= 1


def test_enriched_facts_filter_by_pgc_account(pgc_xbrl_enriched_db):
    """Filter by pgc_account returns only facts that have a matching PGC mapping."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts", params={"pgc_account": "700"})
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) == 1
    assert data["facts"][0]["pgc_account_codigo"] == "700"


def test_enriched_facts_filter_by_confidence(pgc_xbrl_enriched_db):
    """Filter by confidence returns only facts with matching mapping confidence."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts", params={"confidence": "high"})
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) >= 1
    assert data["facts"][0]["mapping_confidence"] == "high"


def test_enriched_facts_pgc_account_description_present(pgc_xbrl_enriched_db):
    """PGC account description is populated via LEFT JOIN with pgc_cuenta."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts")
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) >= 1
    assert data["facts"][0]["pgc_account_descripcion"] is not None
    assert "Ventas" in data["facts"][0]["pgc_account_descripcion"]


def test_enriched_facts_limit(pgc_xbrl_enriched_db):
    """Limit parameter caps the number of results returned."""
    _seed_enriched_fact(
        engine,
        "http://xbrl.ifrs.org/taxonomy/2025-03-27/ias/IAS18/Revenue",
    )

    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/v1/xbrl/enriched-facts", params={"limit": 1})
            return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["facts"]) == 1
