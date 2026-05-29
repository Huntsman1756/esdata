"""Tests for ESMA MiFIR transaction reporting schema loader."""

import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openpyxl import Workbook
from worker_esma_mifir_reporting import (
    ESMA_MIFIR_DOCUMENTS,
    ReportingDocument,
    SchemaDownload,
    _get_esma_url,
    parse_validation_rules_xlsx,
    parse_xsd_fields,
)


class FakeResponse:
    def __init__(self, status_code, *, headers=None, content=b"ok", url="https://www.esma.europa.eu/doc"):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_parse_xsd_fields_extracts_elements_and_lengths():
    xsd = b"""<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="Max35Text">
        <xs:restriction base="xs:string">
          <xs:maxLength value="35"/>
        </xs:restriction>
      </xs:simpleType>
      <xs:element name="Document" type="Document"/>
      <xs:complexType name="Document">
        <xs:sequence>
          <xs:element name="TxId" type="Max35Text">
            <xs:annotation><xs:documentation>Transaction identifier</xs:documentation></xs:annotation>
          </xs:element>
          <xs:element name="Opt" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
      </xs:complexType>
    </xs:schema>
    """
    download = SchemaDownload(
        source_url="https://www.esma.europa.eu/schemas.zip",
        zip_hash="ziphash",
        files=[("schema/auth.016.001.01_ESMAUG_Reporting_1.1.0.xsd", xsd, "xsdhash")],
    )

    fields = parse_xsd_fields(download)

    assert [field["nombre_campo"].split(":")[-1] for field in fields] == ["Document", "TxId", "Opt"]
    tx_id = fields[1]
    assert tx_id["longitud"] == 35
    assert tx_id["obligatorio"] is True
    assert tx_id["descripcion"] == "Transaction identifier"
    opt = fields[2]
    assert opt["obligatorio"] is False
    assert "max=unbounded" in opt["formato"]


def test_parse_validation_rules_xlsx_extracts_structured_rules():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "TransactionDataValidations"
    worksheet.append(
        [
            "Rule ID",
            "Field no",
            "FIELD",
            "CONTENT TO BE REPORTED",
            "FORMAT AND STANDARDS TO BE USED FOR REPORTING",
            "Validation rule",
            "Implementation",
            "Error code",
            "Error text",
            "Set",
        ]
    )
    worksheet.append(
        [
            "005",
            "2",
            "Transaction Reference Number",
            "",
            "",
            "Reference must be unique for the executing firm.",
            "Application",
            "CON-023",
            "Duplicate transaction reference number",
            "1",
        ]
    )
    xlsx_buffer = BytesIO()
    workbook.save(xlsx_buffer)

    document = ReportingDocument(
        tipo="VALIDATION_RULES",
        titulo="Transaction Reporting Validation Rules",
        referencia="ESMA65-8-2594",
        url_esma="https://www.esma.europa.eu/rules.xlsx",
        fecha_publicacion="2022-05-31",
        source_hash="hash",
        verified=True,
        completeness="completa",
        content=xlsx_buffer.getvalue(),
    )

    rules = parse_validation_rules_xlsx(document)

    assert rules == [
        {
            "codigo": "005",
            "descripcion": "Reference must be unique for the executing firm.",
            "campo_afectado": "2 Transaction Reference Number",
            "severidad": "ERROR",
            "rts_referencia": None,
            "source_url": "https://www.esma.europa.eu/rules.xlsx",
            "source_hash": "hash",
            "capture_date": rules[0]["capture_date"],
        }
    ]


def test_mifir_reporting_documents_include_qna_and_isrb_contract():
    refs = {document[2]: document for document in ESMA_MIFIR_DOCUMENTS}

    assert refs["ESMA-MIFIR-REPORTING-HUB"][0] == "REPORTING_HUB"
    assert refs["ESMA-ISRB-MIFIR-ARTICLE-26"][0] == "ISRB"
    assert refs["ESMA-QNA-INDEX"][0] == "QNA_INDEX"
    assert refs["ESMA-QNA-INDEX"][5] is True
    assert refs["ESMA-QNA-INDEX"][6] == "parcial"


def test_get_esma_url_retries_429_with_retry_after(monkeypatch):
    responses = [
        FakeResponse(429, headers={"Retry-After": "2"}),
        FakeResponse(200, content=b"retried"),
    ]
    sleeps = []

    def fake_get(url, follow_redirects, timeout):
        assert follow_redirects is True
        assert timeout == 60.0
        return responses.pop(0)

    monkeypatch.setattr("worker_esma_mifir_reporting.httpx.get", fake_get)
    monkeypatch.setattr("worker_esma_mifir_reporting.time.sleep", sleeps.append)

    response = _get_esma_url("https://www.esma.europa.eu/doc")

    assert response.content == b"retried"
    assert sleeps == [2.0]
