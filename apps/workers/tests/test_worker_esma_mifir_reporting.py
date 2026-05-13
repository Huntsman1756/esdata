"""Tests for ESMA MiFIR transaction reporting schema loader."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker_esma_mifir_reporting import SchemaDownload, parse_xsd_fields


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
