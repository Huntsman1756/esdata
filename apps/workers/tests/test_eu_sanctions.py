import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eu_sanctions import fetch_eu_sanctions_xml, parse_eu_sanctions_xml


class MockResponse:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.content


EU_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<export xmlns="http://eu.europa.ec/fpi/fsd/export">
  <exportGenerationDate>2026-05-17T08:00:00</exportGenerationDate>
  <sanctionEntity euReferenceNumber="EU.1234" logicalId="456">
    <subjectType classificationCode="person"/>
    <regulation programme="UKR" numberTitle="Council Regulation (EU) No 269/2014" publicationUrl="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014R0269"/>
    <nameAlias wholeName="Jane Doe" function="Primary name"/>
    <nameAlias wholeName="J. Doe"/>
    <address countryDescription="Spain"/>
    <identification identificationTypeCode="passport" number="X123456"/>
  </sanctionEntity>
</export>
"""


def test_parse_eu_sanctions_xml_maps_official_fields():
    entries, meta = parse_eu_sanctions_xml(EU_XML)

    assert meta == {"generation_date": "2026-05-17T08:00:00", "record_count": "1"}
    assert entries[0]["entidad_id"] == "EU-EU.1234"
    assert entries[0]["nombre"] == "Jane Doe"
    assert entries[0]["nombre_normalizado"] == "jane doe"
    assert entries[0]["tipo_entidad"] == "person"
    assert entries[0]["aliases"] == ["J. Doe"]
    assert entries[0]["categorias"] == ["sanctions", "eu", "UKR", "Council Regulation (EU) No 269/2014"]
    assert entries[0]["metadata_json"]["countries"] == ["Spain"]
    assert entries[0]["metadata_json"]["id_documents"] == [{"type": "passport", "number": "X123456"}]


def test_fetch_eu_sanctions_xml_uses_official_source_parser():
    with patch("eu_sanctions.urlopen", return_value=MockResponse(EU_XML)):
        entries, meta = fetch_eu_sanctions_xml("https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content")

    assert len(entries) == 1
    assert meta["record_count"] == "1"
