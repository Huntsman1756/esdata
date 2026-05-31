import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mica import (
    discover_esma_casp_csv,
    discover_esma_mica_register_csvs,
    fetch_esma_casp,
    normalize_casp,
    normalize_mica_register_row,
    run_once,
)


class MockResponse:
    def __init__(self, text: str | None = None, content: bytes | None = None):
        self.text = text or ""
        self.content = content if content is not None else self.text.encode("utf-8")
        self.url = "https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv"

    def raise_for_status(self):
        return None


class MockClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        return self.responses.pop(0)


def _create_mica_tables(conn) -> None:
    """Create all MiCA tables for testing."""
    conn.execute(
        text(
            """
            CREATE TABLE casp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                registration_number TEXT UNIQUE,
                home_member_state TEXT,
                passport_active BOOLEAN NOT NULL DEFAULT FALSE,
                services_offered TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_url TEXT,
                source_hash TEXT,
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT FALSE,
                completeness TEXT NOT NULL DEFAULT 'parcial'
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE crypto_asset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                reference_uid TEXT UNIQUE,
                issuer_jurisdiction TEXT,
                is_sha BOOLEAN NOT NULL DEFAULT FALSE,
                market_value_eur NUMERIC,
                holders_count INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE tokenized_asset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                underlying_type TEXT,
                face_value NUMERIC,
                total_amount NUMERIC,
                listing_date DATE,
                regulated_market TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE wallet_custodian (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER UNIQUE,
                wallet_type TEXT,
                custody_mechanism TEXT,
                insurance_coverage NUMERIC,
                audit_frequency TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE crypto_transaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_wallet TEXT,
                receiver_wallet TEXT,
                sender_jurisdiction TEXT,
                receiver_jurisdiction TEXT,
                asset_type TEXT,
                amount NUMERIC,
                value_eur NUMERIC,
                timestamp TIMESTAMP,
                reporting_period TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sender_wallet, receiver_wallet, timestamp, reporting_period)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE mica_register_entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                register_type TEXT NOT NULL,
                register_label TEXT NOT NULL,
                source_row_id TEXT NOT NULL,
                name TEXT,
                entity_identifier TEXT,
                home_member_state TEXT,
                status TEXT,
                raw_data TEXT NOT NULL DEFAULT '{}',
                source_url TEXT NOT NULL,
                source_hash TEXT,
                capture_date DATE,
                verified BOOLEAN NOT NULL DEFAULT FALSE,
                completeness TEXT NOT NULL DEFAULT 'parcial',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(register_type, source_row_id)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                bloques_processed INTEGER,
                articulos_upserted INTEGER,
                documentos_processed INTEGER,
                documentos_upserted INTEGER,
                doctrina_links_created INTEGER,
                error_msg TEXT,
                rows_processed INTEGER,
                errors INTEGER,
                duration_ms INTEGER
            )
            """
        )
    )


def test_discover_esma_casp_csv_from_official_page(monkeypatch):
    html = '<a href="/sites/default/files/2024-12/CASPS.csv">CASP</a>'
    monkeypatch.setattr("mica.httpx.Client", lambda **kwargs: MockClient([MockResponse(text=html)]))

    assert discover_esma_casp_csv("https://www.esma.europa.eu/mica") == (
        "https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv"
    )


def test_discover_esma_mica_non_casp_register_csvs_from_official_page(monkeypatch):
    html = (
        '<a href="/sites/default/files/2024-12/OTHER.csv">Other</a>'
        '<a href="/sites/default/files/2024-12/ARTZZ.csv">ART</a>'
        '<a href="/sites/default/files/2024-12/EMTWP.csv">EMT</a>'
        '<a href="/sites/default/files/2024-12/NCASP.csv">NCASP</a>'
    )
    monkeypatch.setattr("mica.httpx.Client", lambda **kwargs: MockClient([MockResponse(text=html)]))

    discovered = discover_esma_mica_register_csvs("https://www.esma.europa.eu/mica")

    assert discovered["white_papers_other"].endswith("/OTHER.csv")
    assert discovered["art_issuers"].endswith("/ARTZZ.csv")
    assert discovered["emt_issuers"].endswith("/EMTWP.csv")
    assert discovered["non_compliant_entities"].endswith("/NCASP.csv")


def test_fetch_esma_casp_parses_current_csv(monkeypatch):
    csv_content = (
        "ae_competentAuthority,ae_homeMemberState,ae_lei_name,ae_lei,ae_lei_cou_code,"
        "ae_commercial_name,ae_address,ae_website,ae_website_platform,"
        "ac_authorisationNotificationDate,ac_authorisationEndDate,ac_serviceCode,"
        "ac_serviceCode_cou,ac_comments,ac_lastupdate\n"
        "Austrian FMA,AT,Bybit EU GmbH,5299005V5GBSN2A4C303,AT,Bybit,"
        "\"Donau-City-Strasse 7, Vienna\",https://www.bybit.eu,,28/05/2025,,"
        "\"a. custody | c. exchange\",BE|ES,,28/05/2025\n"
    )
    monkeypatch.setattr(
        "mica.httpx.Client",
        lambda **kwargs: MockClient([MockResponse(content=csv_content.encode("utf-8-sig"))]),
    )

    rows, source, source_hash = fetch_esma_casp("https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv")
    normalized = normalize_casp(rows[0])

    assert source.endswith("CASPS.csv")
    assert len(source_hash) == 32
    assert normalized["name"] == "Bybit"
    assert normalized["registration_number"] == "5299005V5GBSN2A4C303"
    assert normalized["home_member_state"] == "AT"
    assert normalized["passport_active"] is True
    assert normalized["services_offered"] == ["a. custody", "c. exchange"]


def test_normalize_mica_register_row_preserves_raw_non_casp_fields():
    normalized = normalize_mica_register_row(
        "emt_issuers",
        {
            "ae_homeMemberState": "CZ",
            "ae_lei_name": "Payment Corporation SE",
            "ae_lei": "315700IJDQF91J9C8B68",
            "ae_commercial_name": "Stable Labs",
            "wp_url": "https://stablelabs.co/whitepaper0.pdf",
            "wp_lastupdate": "30/10/2025",
            "": "",
        },
        0,
    )

    assert normalized["register_type"] == "emt_issuers"
    assert normalized["name"] == "Stable Labs"
    assert normalized["entity_identifier"] == "315700IJDQF91J9C8B68"
    assert normalized["home_member_state"] == "CZ"
    assert normalized["status"] == "active"
    assert normalized["raw_data"]["wp_url"].endswith("whitepaper0.pdf")
    assert "" not in normalized["raw_data"]


def test_run_once_persists_casp_entities(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "mica.fetch_esma_casp",
        lambda: (
            [
                {
                    "ae_commercial_name": "Bitso",
                    "ae_lei": "ESMA-BITSO-001",
                    "ae_homeMemberState": "ES",
                    "ac_serviceCode_cou": "ES|FR",
                    "ac_serviceCode": "custody | exchange",
                }
            ],
            "https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv",
            "sourcehash",
        ),
    )
    monkeypatch.setattr("mica.discover_esma_mica_register_csvs", lambda: {})

    run_once()

    with engine.begin() as conn:
        casp_count = conn.execute(text("SELECT COUNT(*) FROM casp")).scalar()
        assert casp_count == 1
        asset_count = conn.execute(text("SELECT COUNT(*) FROM crypto_asset")).scalar()
        assert asset_count == 0
        tokenized_count = conn.execute(text("SELECT COUNT(*) FROM tokenized_asset")).scalar()
        assert tokenized_count == 0
        custodian_count = conn.execute(text("SELECT COUNT(*) FROM wallet_custodian")).scalar()
        assert custodian_count == 0
        tx_count = conn.execute(text("SELECT COUNT(*) FROM crypto_transaction")).scalar()
        assert tx_count == 0
        register_count = conn.execute(text("SELECT COUNT(*) FROM mica_register_entry")).scalar()
        assert register_count == 0
        source_row = conn.execute(
            text("SELECT source_url, source_hash, verified, completeness FROM casp WHERE name = 'Bitso'")
        ).mappings().one()
        assert source_row["source_url"].endswith("CASPS.csv")
        assert source_row["source_hash"] == "sourcehash"
        assert bool(source_row["verified"]) is True
        assert source_row["completeness"] == "completa"


def test_services_offered_serialized_as_json(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "mica.fetch_esma_casp",
        lambda: (
            [
                {
                    "ae_commercial_name": "Bitso",
                    "ae_lei": "ESMA-BITSO-001",
                    "ae_homeMemberState": "ES",
                    "ac_serviceCode_cou": "ES|FR",
                    "ac_serviceCode": "custody | exchange",
                }
            ],
            "https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv",
            "sourcehash",
        ),
    )
    monkeypatch.setattr("mica.discover_esma_mica_register_csvs", lambda: {})

    run_once()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT services_offered FROM casp WHERE name = 'Bitso'")
        ).scalar()
        assert row is not None
        if isinstance(row, str):
            parsed = json.loads(row)
        else:
            parsed = row
        assert isinstance(parsed, list)
        assert "exchange" in parsed
        assert "custody" in parsed


def test_upsert_idempotent(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _create_mica_tables(conn)

    monkeypatch.setattr("mica.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "mica.fetch_esma_casp",
        lambda: (
            [
                {
                    "ae_commercial_name": "Bitso",
                    "ae_lei": "ESMA-BITSO-001",
                    "ae_homeMemberState": "ES",
                    "ac_serviceCode_cou": "ES|FR",
                    "ac_serviceCode": "custody | exchange",
                }
            ],
            "https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv",
            "sourcehash",
        ),
    )
    monkeypatch.setattr(
        "mica.discover_esma_mica_register_csvs",
        lambda: {
            "emt_issuers": "https://www.esma.europa.eu/sites/default/files/2024-12/EMTWP.csv",
        },
    )
    monkeypatch.setattr(
        "mica.fetch_esma_mica_register",
        lambda register_type, url=None: (
            [
                {
                    "ae_commercial_name": "Stable Labs",
                    "ae_lei": "315700IJDQF91J9C8B68",
                    "ae_homeMemberState": "CZ",
                    "wp_url": "https://stablelabs.co/whitepaper0.pdf",
                }
            ],
            url,
            "registerhash",
        ),
    )

    run_once()
    run_once()

    with engine.begin() as conn:
        casp_count = conn.execute(text("SELECT COUNT(*) FROM casp")).scalar()
        assert casp_count == 1
        asset_count = conn.execute(text("SELECT COUNT(*) FROM crypto_asset")).scalar()
        assert asset_count == 0
        tx_count = conn.execute(text("SELECT COUNT(*) FROM crypto_transaction")).scalar()
        assert tx_count == 0
        register_count = conn.execute(text("SELECT COUNT(*) FROM mica_register_entry")).scalar()
        assert register_count == 1
        register_row = conn.execute(
            text(
                """
                SELECT register_type, name, entity_identifier, source_url, source_hash,
                       verified, completeness
                FROM mica_register_entry
                """
            )
        ).mappings().one()
        assert register_row["register_type"] == "emt_issuers"
        assert register_row["name"] == "Stable Labs"
        assert register_row["entity_identifier"] == "315700IJDQF91J9C8B68"
        assert register_row["source_url"].endswith("EMTWP.csv")
        assert register_row["source_hash"] == "registerhash"
        assert bool(register_row["verified"]) is True
        assert register_row["completeness"] == "completa"
