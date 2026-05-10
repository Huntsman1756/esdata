import sys
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ofac_sdn import fetch_ofac_sdn_xml, parse_ofac_sdn_xml, run_sync


class MockResponse:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.content


OFAC_XML = b"""<?xml version="1.0" standalone="yes"?>
<sdnList xmlns="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML">
  <publshInformation>
    <Publish_Date>05/08/2026</Publish_Date>
    <Record_Count>2</Record_Count>
  </publshInformation>
  <sdnEntry>
    <uid>36</uid>
    <lastName>AEROCARIBBEAN AIRLINES</lastName>
    <sdnType>Entity</sdnType>
    <programList><program>CUBA</program></programList>
    <akaList>
      <aka><uid>12</uid><type>a.k.a.</type><category>strong</category><lastName>AERO-CARIBBEAN</lastName></aka>
    </akaList>
    <addressList><address><uid>25</uid><city>Havana</city><country>Cuba</country></address></addressList>
  </sdnEntry>
  <sdnEntry>
    <uid>2674</uid>
    <firstName>Abu</firstName>
    <lastName>ABBAS</lastName>
    <sdnType>Individual</sdnType>
    <programList><program>SDGT</program></programList>
    <idList><id><uid>185810</uid><idType>Passport</idType><idNumber>A123</idNumber></id></idList>
  </sdnEntry>
</sdnList>
"""


def test_parse_ofac_sdn_xml_maps_official_fields():
    entries, meta = parse_ofac_sdn_xml(OFAC_XML)

    assert meta == {"publish_date": "05/08/2026", "record_count": "2"}
    assert len(entries) == 2
    assert entries[0]["entidad_id"] == "OFAC-36"
    assert entries[0]["nombre"] == "AEROCARIBBEAN AIRLINES"
    assert entries[0]["nombre_normalizado"] == "aerocaribbean airlines"
    assert entries[0]["tipo_entidad"] == "entity"
    assert entries[0]["aliases"] == ["AERO-CARIBBEAN"]
    assert entries[0]["categorias"] == ["sanctions", "ofac", "CUBA"]
    assert entries[0]["metadata_json"]["countries"] == ["Cuba"]
    assert entries[1]["nombre"] == "Abu ABBAS"
    assert entries[1]["tipo_entidad"] == "person"
    assert entries[1]["metadata_json"]["id_documents"] == [{"type": "Passport", "number": "A123"}]


def test_fetch_ofac_sdn_xml_uses_official_source_parser():
    with patch("ofac_sdn.urlopen", return_value=MockResponse(OFAC_XML)):
        entries, meta = fetch_ofac_sdn_xml("https://www.treasury.gov/ofac/downloads/sdn.xml")

    assert len(entries) == 2
    assert meta["publish_date"] == "05/08/2026"


def test_run_sync_returns_error_without_seed_fallback():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with patch("ofac_sdn.create_engine", return_value=engine), patch(
        "ofac_sdn.fetch_ofac_sdn_xml", side_effect=RuntimeError("official source down")
    ), patch("ofac_sdn.ensure_database_connection", return_value=None), patch(
        "ofac_sdn.handle_worker_failure", return_value=True
    ):
        result = run_sync(worker_name="test-ofac")

    assert result["processed"] == 0
    assert result["source"] == "ofac_sdn_xml"
    assert "official source down" in result["error"]
