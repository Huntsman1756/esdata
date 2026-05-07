"""Tests for IBAN validation (Fase 17.1)."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.banking.iban import validate_iban
from apps.api.banking.iso20022 import parse_iso20022
from apps.api.banking.n43 import parse_n43

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app


# ---------------------------------------------------------------------------
# Unit tests — validate_iban
# ---------------------------------------------------------------------------

class TestValidateIban:
    """Pure Python validation tests."""

    def test_valid_es_iban(self):
        result = validate_iban("ES79 2100 0813 6101 2345 6789")
        assert result["valid"] is True
        assert result["iban"] == "ES7921000813610123456789"
        assert result["country_code"] == "ES"
        assert result["country_length_ok"] is True
        assert result["format_ok"] is True
        assert result["check_digit_valid"] is True
        assert result["errors"] == []

    def test_valid_es_iban_no_spaces(self):
        result = validate_iban("ES7921000813610123456789")
        assert result["valid"] is True
        assert result["iban"] == "ES7921000813610123456789"

    def test_valid_de_iban(self):
        result = validate_iban("DE89370400440532013000")
        assert result["valid"] is True
        assert result["country_code"] == "DE"
        assert result["country_length_ok"] is True

    def test_valid_gb_iban(self):
        result = validate_iban("GB29NWBK60161331926819")
        assert result["valid"] is True
        assert result["country_code"] == "GB"
        assert result["country_length_ok"] is True

    def test_valid_fr_iban(self):
        result = validate_iban("FR7630006000011234567890189")
        assert result["valid"] is True
        assert result["country_code"] == "FR"
        assert result["country_length_ok"] is True

    def test_invalid_check_digit(self):
        # Same as ES IBAN but check digit changed
        result = validate_iban("ES7821000813610123456789")
        assert result["valid"] is False
        assert result["check_digit_valid"] is False
        assert len(result["errors"]) > 0

    def test_invalid_length_es(self):
        # Too short for Spain
        result = validate_iban("ES12345678901234567890")
        assert result["valid"] is False
        assert result["country_length_ok"] is False

    def test_unknown_country(self):
        # Unknown country code — format ok, length skipped
        result = validate_iban("XX123456789012345678")
        assert result["format_ok"] is True
        assert result["country_length_ok"] is None

    def test_empty_iban(self):
        result = validate_iban("")
        assert result["valid"] is False
        assert result["iban"] == ""
        assert result["country_code"] is None
        assert result["format_ok"] is False
        assert len(result["errors"]) > 0

    def test_invalid_format_letters_in_check(self):
        result = validate_iban("ESAB21000813610123456789")
        assert result["valid"] is False
        assert result["format_ok"] is False

    def test_invalid_format_short(self):
        result = validate_iban("ES12")
        assert result["valid"] is False
        assert result["format_ok"] is False

    def test_lowercase_normalized(self):
        result = validate_iban("es7921000813610123456789")
        assert result["valid"] is True
        assert result["iban"] == "ES7921000813610123456789"

    def test_spaces_removed(self):
        result = validate_iban("ES 79 2100 0813 6101 2345 6789")
        assert result["valid"] is True
        assert " " not in result["iban"]

    def test_mixed_case_with_spaces(self):
        result = validate_iban("Es79 2100 0813 6101 2345 6789")
        assert result["valid"] is True
        assert result["iban"] == "ES7921000813610123456789"

    def test_pt_iban(self):
        result = validate_iban("PT50000201231234567890154")
        assert result["valid"] is True
        assert result["country_code"] == "PT"
        assert result["country_length_ok"] is True

    def test_it_iban(self):
        result = validate_iban("IT60X0542811101000000123456")
        assert result["valid"] is True
        assert result["country_code"] == "IT"
        assert result["country_length_ok"] is True

    def test_nl_iban(self):
        result = validate_iban("NL91ABNA0417164300")
        assert result["valid"] is True
        assert result["country_code"] == "NL"
        assert result["country_length_ok"] is True

    def test_be_iban(self):
        result = validate_iban("BE68539007547034")
        assert result["valid"] is True
        assert result["country_code"] == "BE"
        assert result["country_length_ok"] is True

    def test_all_errors_listed(self):
        # Format invalid — check digit can't be validated
        result = validate_iban("XYZ")
        assert result["valid"] is False
        assert result["format_ok"] is False
        assert result["check_digit_valid"] is False
        assert len(result["errors"]) >= 1

    def test_country_codes_registry(self):
        from apps.api.banking.iban import IBAN_COUNTRY_LENGTHS
        assert "ES" in IBAN_COUNTRY_LENGTHS
        assert IBAN_COUNTRY_LENGTHS["ES"] == 24
        assert "DE" in IBAN_COUNTRY_LENGTHS
        assert IBAN_COUNTRY_LENGTHS["DE"] == 22
        assert "GB" in IBAN_COUNTRY_LENGTHS
        assert IBAN_COUNTRY_LENGTHS["GB"] == 22


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(app)


class TestIbanValidateEndpoint:
    """POST /v1/banking/iban/validate endpoint tests."""

    def test_validate_valid_es(self, client):
        resp = client.post("/v1/banking/iban/validate", json={"iban": "ES79 2100 0813 6101 2345 6789"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is True
        assert data["result"]["country_code"] == "ES"
        assert data["result"]["iban"] == "ES7921000813610123456789"

    def test_validate_invalid_check_digit(self, client):
        resp = client.post("/v1/banking/iban/validate", json={"iban": "ES7821000813610123456789"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is False
        assert data["result"]["check_digit_valid"] is False
        assert len(data["result"]["errors"]) > 0

    def test_validate_empty_iban(self, client):
        resp = client.post("/v1/banking/iban/validate", json={"iban": ""})
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data["detail"]

    def test_validate_missing_body(self, client):
        resp = client.post("/v1/banking/iban/validate")
        assert resp.status_code == 422

    def test_validate_invalid_format(self, client):
        resp = client.post("/v1/banking/iban/validate", json={"iban": "INVALID"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is False
        assert data["result"]["format_ok"] is False

    def test_validate_de_iban(self, client):
        resp = client.post("/v1/banking/iban/validate", json={"iban": "DE89370400440532013000"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is True
        assert data["result"]["country_code"] == "DE"

    def test_validate_gb_iban(self, client):
        resp = client.post("/v1/banking/iban/validate", json={"iban": "GB29NWBK60161331926819"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is True
        assert data["result"]["country_code"] == "GB"


class TestIbanCountryCodesEndpoint:
    """GET /v1/banking/iban/countries endpoint tests."""

    def test_returns_country_list(self, client):
        resp = client.get("/v1/banking/iban/countries")
        assert resp.status_code == 200
        data = resp.json()
        assert "supported_countries" in data
        assert "ES" in data["supported_countries"]
        assert isinstance(data["supported_countries"], list)
        assert len(data["supported_countries"]) > 20

    def test_countries_sorted(self, client):
        resp = client.get("/v1/banking/iban/countries")
        data = resp.json()
        assert data["supported_countries"] == sorted(data["supported_countries"])


# ---------------------------------------------------------------------------
# ISO 20022 parsing tests (Fase 17.2)
# ---------------------------------------------------------------------------

SAMPLE_PAIN008 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.08">
  <CstmrPmtInitn>
    <GrpHdr>
      <MsgId>MSG-20250101-001</MsgId>
      <CreDtTm>2025-01-01T10:00:00</CreDtTm>
      <NbOfTxs>2</NbOfTxs>
      <CtrlSum>1500.00</CtrlSum>
      <InitgPrty>NORM</InitgPrty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMT-001</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <BtchBookg>true</BtchBookg>
      <NbOfTxs>2</NbOfTxs>
      <CtrlSum>1500.00</CtrlSum>
      <PmtTpInf>
        <SvcLn>
          <Prtry>SEPA</Prtry>
        </SvcLn>
      </PmtTpInf>
      <ReqdExctnDt>2025-01-02</ReqdExctnDt>
      <Dbtr>
        <Nm>Empresa Ejemplo SL</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <IBAN>ES7921000813610123456789</IBAN>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <BICFI>CAIXESBB</BICFI>
        </FinInstnId>
      </DbtrAgt>
      <ChqInstr>
        <Tp>
          <CdOrPrtry>
            <Cd>CHEQ</Cd>
          </CdOrPrtry>
        </Tp>
        <ChqNb>123456</ChqNb>
      </ChqInstr>
      <CstmrPmtInf>
        <PmtId>
          <EndToEndId>E2E-001</EndToEndId>
          <InstrId>INS-001</InstrId>
        </PmtId>
        <InstdAmt Ccy="EUR">500.00</InstdAmt>
        <CdtrAgt>
          <FinInstnId>
            <BICFI>BKTRUS33</BICFI>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>Proveedor Alpha SA</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <IBAN>DE89370400440532013000</IBAN>
          </Id>
        </CdtrAcct>
        <RmtInf>
          <Ustrd>Factura 2025-001</Ustrd>
        </RmtInf>
        <ChrgBr>DEBT</ChrgBr>
      </CstmrPmtInf>
      <CstmrPmtInf>
        <PmtId>
          <EndToEndId>E2E-002</EndToEndId>
          <InstrId>INS-002</InstrId>
        </PmtId>
        <InstdAmt Ccy="EUR">1000.00</InstdAmt>
        <CdtrAgt>
          <FinInstnId>
            <BICFI>BBVAESMM</BICFI>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>Servicios Beta SL</Nm>
          <PstlAdr>
            <Ctry>ES</Ctry>
            <AdrLine>Calle Principal 1</AdrLine>
          </PstlAdr>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <IBAN>FR7630006000011234567890189</IBAN>
          </Id>
        </CdtrAcct>
        <RmtInf>
          <Strd>
            <CdtrRefInf>
              <Ref>REF-2025-002</Ref>
              <Tp>
                <Cd>SCOR</Cd>
              </Tp>
            </CdtrRefInf>
          </Strd>
        </RmtInf>
      </CstmrPmtInf>
    </PmtInf>
  </CstmrPmtInitn>
</Document>"""


class TestParseIso20022:
    """Pure Python ISO 20022 parser tests."""

    def test_parse_valid_pain008(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        assert result["valid"] is True
        assert result["document_type"] == "pain.008.001.08"
        assert "pain.008.001.08" in result["namespace"]
        assert result["group_header"] is not None
        assert result["group_header"]["msg_id"] == "MSG-20250101-001"
        assert result["group_header"]["creation_datetime"] == "2025-01-01T10:00:00"
        assert result["group_header"]["number_of_transactions"] == "2"
        assert result["group_header"]["control_sum"] == "1500.00"
        assert result["group_header"]["instruction_priority"] == "NORM"

    def test_parse_pmt_inf(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        pmts = result["payment_informations"]
        assert len(pmts) == 1
        pmt = pmts[0]
        assert pmt["payment_information_id"] == "PMT-001"
        assert pmt["payment_method"] == "TRF"
        assert pmt["batch_booking"] is True
        assert pmt["control_sum"] == "1500.00"
        assert pmt["requested_execution_date"] == "2025-01-02"

    def test_parse_payment_type_info(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        pmt = result["payment_informations"][0]
        pti = pmt["payment_type_info"]
        assert pti is not None
        assert pti["service_level"] == "SEPA"

    def test_parse_debtor(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        pmt = result["payment_informations"][0]
        assert pmt["debtor"]["name"] == "Empresa Ejemplo SL"
        assert pmt["debtor_account"]["iban"] == "ES7921000813610123456789"
        assert pmt["debtor_agent"]["bicfi"] == "CAIXESBB"

    def test_parse_cheque_instruction(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        pmt = result["payment_informations"][0]
        assert pmt["cheque_instruction"] is not None
        assert pmt["cheque_instruction"]["type"] == "CHEQ"
        assert pmt["cheque_instruction"]["cheque_number"] == "123456"

    def test_parse_transactions(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        pmt = result["payment_informations"][0]
        txns = pmt["transactions"]
        assert len(txns) == 2

    def test_parse_transaction_1(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        txn = result["payment_informations"][0]["transactions"][0]
        assert txn["end_to_end_id"] == "E2E-001"
        assert txn["instruction_id"] == "INS-001"
        assert txn["amount"] == "500.00"
        assert txn["currency"] == "EUR"
        assert txn["creditor"]["name"] == "Proveedor Alpha SA"
        assert txn["creditor_account"]["iban"] == "DE89370400440532013000"
        assert txn["creditor_agent"]["bicfi"] == "BKTRUS33"
        assert txn["remittance"]["unstructured"] == "Factura 2025-001"
        assert txn["charge_bearer"] == "DEBT"

    def test_parse_transaction_2(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        txn = result["payment_informations"][0]["transactions"][1]
        assert txn["end_to_end_id"] == "E2E-002"
        assert txn["amount"] == "1000.00"
        assert txn["creditor"]["name"] == "Servicios Beta SL"
        assert txn["creditor"]["address"]["country"] == "ES"
        assert txn["creditor_account"]["iban"] == "FR7630006000011234567890189"
        assert txn["remittance"]["structured_reference"] == "REF-2025-002"
        assert txn["remittance"]["reference_type"] == "SCOR"

    def test_parse_total_counts(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        assert result["total_transactions"] == 2
        assert result["total_control_sum"] == "1500.00"

    def test_parse_empty_input(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(b"")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_parse_invalid_xml(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(b"<not valid xml")
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "parse error" in result["errors"][0].lower()

    def test_parse_no_pmt_inf(self):
        from apps.api.banking.iso20022 import parse_iso20022
        xml = b"""<?xml version="1.0"?>
        <Document><OtherBlock/></Document>"""
        result = parse_iso20022(xml)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "PmtInf" in result["errors"][0]

    def test_parse_creditor_address(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008)
        txn = result["payment_informations"][0]["transactions"][1]
        addr = txn["creditor"]["address"]
        assert addr["country"] == "ES"
        assert "Calle Principal 1" in addr["lines"]


SAMPLE_PAIN008_NO_TRANSACTIONS = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.08">
  <CstmrPmtInitn>
    <GrpHdr>
      <MsgId>EMPTY-MSG</MsgId>
      <NbOfTxs>0</NbOfTxs>
      <CtrlSum>0.00</CtrlSum>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMT-EMPTY</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <NbOfTxs>0</NbOfTxs>
      <CtrlSum>0.00</CtrlSum>
      <Dbtr>
        <Nm>Empty Corp</Nm>
      </Dbtr>
    </PmtInf>
  </CstmrPmtInitn>
</Document>"""


class TestParseIso20022EdgeCases:
    """Edge cases for ISO 20022 parser."""

    def test_empty_payment_info(self):
        from apps.api.banking.iso20022 import parse_iso20022
        result = parse_iso20022(SAMPLE_PAIN008_NO_TRANSACTIONS)
        assert result["valid"] is True
        assert len(result["payment_informations"]) == 1
        pmt = result["payment_informations"][0]
        assert pmt["payment_information_id"] == "PMT-EMPTY"
        assert pmt["transactions"] == []
        assert result["total_transactions"] == 0

    def test_parse_multiple_pmt_inf(self):
        from apps.api.banking.iso20022 import parse_iso20022
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.08">
          <CstmrPmtInitn>
            <GrpHdr>
              <MsgId>MULTI</MsgId>
              <NbOfTxs>3</NbOfTxs>
              <CtrlSum>3000.00</CtrlSum>
            </GrpHdr>
            <PmtInf>
              <PmtInfId>PMT-1</PmtInfId>
              <NbOfTxs>1</NbOfTxs>
              <CtrlSum>1000.00</CtrlSum>
              <Dbtr><Nm>Corp 1</Nm></Dbtr>
              <CstmrPmtInf>
                <PmtId><EndToEndId>E1</EndToEndId></PmtId>
                <InstdAmt Ccy="EUR">1000.00</InstdAmt>
                <Cdtr><Nm>Vendor 1</Nm></Cdtr>
                <CdtrAcct><Id><IBAN>ES7921000813610123456789</IBAN></Id></CdtrAcct>
              </CstmrPmtInf>
            </PmtInf>
            <PmtInf>
              <PmtInfId>PMT-2</PmtInfId>
              <NbOfTxs>2</NbOfTxs>
              <CtrlSum>2000.00</CtrlSum>
              <Dbtr><Nm>Corp 2</Nm></Dbtr>
              <CstmrPmtInf>
                <PmtId><EndToEndId>E2</EndToEndId></PmtId>
                <InstdAmt Ccy="EUR">1000.00</InstdAmt>
                <Cdtr><Nm>Vendor 2</Nm></Cdtr>
                <CdtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct>
              </CstmrPmtInf>
              <CstmrPmtInf>
                <PmtId><EndToEndId>E3</EndToEndId></PmtId>
                <InstdAmt Ccy="EUR">1000.00</InstdAmt>
                <Cdtr><Nm>Vendor 3</Nm></Cdtr>
                <CdtrAcct><Id><IBAN>FR7630006000011234567890189</IBAN></Id></CdtrAcct>
              </CstmrPmtInf>
            </PmtInf>
          </CstmrPmtInitn>
        </Document>"""
        result = parse_iso20022(xml)
        assert result["valid"] is True
        assert len(result["payment_informations"]) == 2
        assert result["payment_informations"][0]["payment_information_id"] == "PMT-1"
        assert len(result["payment_informations"][0]["transactions"]) == 1
        assert len(result["payment_informations"][1]["transactions"]) == 2
        assert result["total_transactions"] == 3
        assert result["total_control_sum"] == "3000.00"


# ---------------------------------------------------------------------------
# Integration tests — ISO 20022 API endpoint (Fase 17.2)
# ---------------------------------------------------------------------------

class TestIso20022ParseEndpoint:
    """POST /v1/banking/iso20022/parse endpoint tests."""

    def test_parse_valid_xml(self, client):
        resp = client.post(
            "/v1/banking/iso20022/parse",
            files={"xml_file": ("pain008.xml", SAMPLE_PAIN008, "application/xml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["document_type"] == "pain.008.001.08"
        assert data["group_header"]["msg_id"] == "MSG-20250101-001"
        assert data["total_transactions"] == 2
        assert data["total_control_sum"] == "1500.00"
        assert len(data["payment_informations"]) == 1
        assert len(data["payment_informations"][0]["transactions"]) == 2

    def test_parse_empty_xml(self, client):
        resp = client.post(
            "/v1/banking/iso20022/parse",
            files={"xml_file": ("empty.xml", b"", "application/xml")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data["detail"]

    def test_parse_invalid_xml(self, client):
        resp = client.post(
            "/v1/banking/iso20022/parse",
            files={"xml_file": ("bad.xml", b"<not valid", "application/xml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_parse_no_file(self, client):
        resp = client.post("/v1/banking/iso20022/parse")
        assert resp.status_code == 422

    def test_parse_empty_payment_info(self, client):
        resp = client.post(
            "/v1/banking/iso20022/parse",
            files={"xml_file": ("empty.xml", SAMPLE_PAIN008_NO_TRANSACTIONS, "application/xml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["total_transactions"] == 0
        assert len(data["payment_informations"]) == 1
        assert len(data["payment_informations"][0]["transactions"]) == 0

    def test_parse_multiple_pmt_inf(self, client):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.08">
          <CstmrPmtInitn>
            <GrpHdr>
              <MsgId>MULTI</MsgId>
              <NbOfTxs>2</NbOfTxs>
              <CtrlSum>2000.00</CtrlSum>
            </GrpHdr>
            <PmtInf>
              <PmtInfId>PMT-1</PmtInfId>
              <NbOfTxs>1</NbOfTxs>
              <CtrlSum>1000.00</CtrlSum>
              <Dbtr><Nm>Corp 1</Nm></Dbtr>
              <CstmrPmtInf>
                <PmtId><EndToEndId>E1</EndToEndId></PmtId>
                <InstdAmt Ccy="EUR">1000.00</InstdAmt>
                <Cdtr><Nm>Vendor 1</Nm></Cdtr>
                <CdtrAcct><Id><IBAN>ES7921000813610123456789</IBAN></Id></CdtrAcct>
              </CstmrPmtInf>
            </PmtInf>
            <PmtInf>
              <PmtInfId>PMT-2</PmtInfId>
              <NbOfTxs>1</NbOfTxs>
              <CtrlSum>1000.00</CtrlSum>
              <Dbtr><Nm>Corp 2</Nm></Dbtr>
              <CstmrPmtInf>
                <PmtId><EndToEndId>E2</EndToEndId></PmtId>
                <InstdAmt Ccy="EUR">1000.00</InstdAmt>
                <Cdtr><Nm>Vendor 2</Nm></Cdtr>
                <CdtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct>
              </CstmrPmtInf>
            </PmtInf>
          </CstmrPmtInitn>
        </Document>"""
        resp = client.post(
            "/v1/banking/iso20022/parse",
            files={"xml_file": ("multi.xml", xml, "application/xml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert len(data["payment_informations"]) == 2
        assert data["total_transactions"] == 2
        assert data["total_control_sum"] == "2000.00"


# ---------------------------------------------------------------------------
# Fase 17.3 — N43 / AEB Cuaderno Bancario
# ---------------------------------------------------------------------------

def _n43_line(record_type: str, fields: list[tuple[int, int, str]]) -> str:
    line = [" "] * 80
    line[0:2] = list(record_type)
    for start, end, value in fields:
        width = end - start + 1
        rendered = value[:width].ljust(width)
        line[start - 1:end] = list(rendered)
    return "".join(line)


def _n43_header(fecha_inicial: str, fecha_final: str) -> str:
    return _n43_line(
        "11",
        [
            (3, 6, "0019"),
            (7, 10, "0123"),
            (11, 20, "4567890123"),
            (21, 26, fecha_inicial),
            (27, 32, fecha_final),
            (33, 33, "1"),
            (34, 47, "00000000000000"),
            (48, 50, "978"),
            (51, 51, "3"),
            (52, 77, "CLIENTE PRUEBA"),
        ],
    )


def _n43_movement(
    booking_date: str,
    value_date: str,
    concept_common: str,
    concept_own: str,
    debe_haber: str,
    amount_cents: str,
    document_number: str,
    reference1: str,
    reference2: str,
) -> str:
    return _n43_line(
        "22",
        [
            (3, 6, "0001"),
            (7, 10, "0123"),
            (11, 16, booking_date),
            (17, 22, value_date),
            (23, 24, concept_common),
            (25, 27, concept_own),
            (28, 28, debe_haber),
            (29, 42, amount_cents),
            (43, 52, document_number),
            (53, 64, reference1),
            (65, 80, reference2),
        ],
    )


def _n43_concept(code: str, concept1: str, concept2: str = "") -> str:
    return _n43_line(
        "23",
        [
            (3, 4, code),
            (5, 42, concept1),
            (43, 80, concept2),
        ],
    )


def _n43_amount(code: str, currency: str, amount_cents: str) -> str:
    return _n43_line(
        "24",
        [
            (3, 4, code),
            (5, 7, currency),
            (8, 21, amount_cents),
        ],
    )


def _n43_final(debe_count: str, debe_total_cents: str, haber_count: str, haber_total_cents: str, saldo_code: str, saldo_cents: str) -> str:
    return _n43_line(
        "33",
        [
            (3, 6, "0019"),
            (7, 10, "0123"),
            (11, 20, "4567890123"),
            (21, 25, debe_count),
            (26, 39, debe_total_cents),
            (40, 44, haber_count),
            (45, 58, haber_total_cents),
            (59, 59, saldo_code),
            (60, 73, saldo_cents),
            (74, 76, "978"),
        ],
    )


def _n43_file_end(record_count: str) -> str:
    return _n43_line(
        "88",
        [
            (3, 20, "9" * 18),
            (21, 26, record_count),
        ],
    )


SAMPLE_N43_SINGLE_ACCOUNT = "\n".join(
    [
        _n43_header("190123", "200131"),
        _n43_movement("190123", "190123", "04", "001", "2", "00000000100000", "1234567890", "1234567890", "REF12345678901"),
        _n43_concept("01", "Transferencia a cuenta ES1234567890123", "456789012"),
        _n43_concept("02", "Referencia adicional del pago"),
        _n43_movement("250101", "250101", "04", "001", "1", "00000005000000", "9876543210", "9876543210", "REF09876543210"),
        _n43_final("00001", "00000005000000", "00001", "00000000100000", "1", "00000004900000"),
        _n43_file_end("000007"),
    ]
) + "\n"

SAMPLE_N43_WITH_FOREIGN_CURRENCY = "\n".join(
    [
        _n43_header("190123", "200131"),
        _n43_movement("190123", "190123", "04", "001", "2", "00000000100000", "1234567890", "1234567890", "REF12345678901"),
        _n43_concept("01", "Transferencia a cuenta ES1234567890123", "456789012"),
        _n43_amount("01", "036", "00000000001500"),
        _n43_final("00000", "00000000000000", "00001", "00000000100000", "2", "00000000000000"),
        _n43_file_end("000005"),
    ]
) + "\n"

SAMPLE_N43_EMPTY_ACCOUNT = "\n".join(
    [
        _n43_header("190123", "200131"),
        _n43_final("00000", "00000000000000", "00000", "00000000000000", "2", "00000002000000"),
        _n43_file_end("000003"),
    ]
) + "\n"

SAMPLE_N43_DESCENDING = "\n".join(
    [
        _n43_header("200101", "200131"),
        _n43_movement("250101", "250101", "04", "001", "1", "00000005000000", "9876543210", "9876543210", "REF09876543210"),
        _n43_movement("190123", "190123", "04", "001", "2", "00000000100000", "1234567890", "1234567890", "REF12345678901"),
        _n43_final("00001", "00000005000000", "00001", "00000000100000", "1", "00000004900000"),
        _n43_file_end("000005"),
    ]
) + "\n"

SAMPLE_N43_NO_HEADERS = "\n".join(
    [
        _n43_movement("190123", "190123", "04", "001", "2", "00000000100000", "1234567890", "1234567890", "REF12345678901"),
        _n43_movement("250101", "250101", "04", "001", "1", "00000005000000", "9876543210", "9876543210", "REF09876543210"),
    ]
) + "\n"

SAMPLE_N43_EMPTY = ""


class TestN43Parse:
    """Pure Python N43 parser unit tests."""

    def test_single_account_transactions(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        assert result.valid is True
        assert len(result.accounts) == 1
        acc = result.accounts[0]
        assert len(acc["transactions"]) == 2
        assert acc["currency"] == "EUR"

    def test_single_account_header_fields(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        acc = result.accounts[0]
        assert len(acc["iban"]) == 24
        assert acc["iban"].startswith("ES")
        assert acc["bank_id"] == "0019"
        assert acc["branch_id"] == "0123"
        assert acc["currency"] == "EUR"
        assert acc["balance_variation"] == -49000.0

    def test_transaction_amounts(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        txns = result.accounts[0]["transactions"]
        assert len(txns) == 2
        assert txns[0]["amount"] == 1000.0
        assert txns[1]["amount"] == -50000.0

    def test_transaction_concepts(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        txns = result.accounts[0]["transactions"]
        assert txns[0]["concept_own"] == "001"
        assert txns[0]["concept_common"] == "04"
        assert txns[0]["remittance"] == "001 GIROS - TRANSFERENCIAS - TRASPASOS - CHEQUES Transferencia a cuenta ES1234567890123456789012 Referencia adicional del pago"

    def test_transaction_dates(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        txns = result.accounts[0]["transactions"]
        assert txns[0]["booking_date"] == "2019-01-23"
        assert txns[0]["value_date"] == "2019-01-23"
        assert txns[1]["booking_date"] == "2025-01-01"
        assert txns[1]["value_date"] == "2025-01-01"

    def test_transaction_balance(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        txns = result.accounts[0]["transactions"]
        assert txns[0]["balance"] == 1000.0
        assert txns[1]["balance"] == -49000.0

    def test_transaction_references(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        txns = result.accounts[0]["transactions"]
        assert txns[0]["reference1"] == "1234567890"
        assert txns[0]["reference2"] == "REF12345678901"
        assert txns[1]["reference1"] == "9876543210"
        assert txns[1]["reference2"] == "REF09876543210"

    def test_transaction_count_and_amount(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        acc = result.accounts[0]
        assert acc["transaction_count"] == 2
        assert acc["transactions_amount"] == -49000.0

    def test_debe_haber_counts(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        acc = result.accounts[0]
        assert acc["debe_count"] == 1
        assert acc["debe_total"] == 50000.0
        assert acc["haber_count"] == 1
        assert acc["haber_total"] == 1000.0

    def test_foreign_currency_supplement(self):
        result = parse_n43(SAMPLE_N43_WITH_FOREIGN_CURRENCY)
        acc = result.accounts[0]
        assert len(acc["transactions"]) == 1
        assert acc["debe_count"] == 0
        assert acc["haber_count"] == 1

    def test_empty_account(self):
        result = parse_n43(SAMPLE_N43_EMPTY_ACCOUNT)
        acc = result.accounts[0]
        assert len(acc["transactions"]) == 0
        assert acc["transaction_count"] == 0
        assert acc["transactions_amount"] == 0.0

    def test_no_headers_error(self):
        result = parse_n43(SAMPLE_N43_NO_HEADERS)
        assert result.valid is False
        assert len(result.accounts) == 0
        assert len(result.errors) > 0

    def test_empty_file(self):
        result = parse_n43(SAMPLE_N43_EMPTY)
        assert result.valid is False
        assert len(result.accounts) == 0
        assert len(result.errors) > 0

    def test_record_counting(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        assert result.total_record_count == 7

    def test_raw_line_counting(self):
        result = parse_n43(SAMPLE_N43_SINGLE_ACCOUNT)
        assert result.raw_line_count == 7


class TestN43ParseEndpoint:
    """Integration tests for the N43 parse endpoint."""

    def test_parse_valid_n43(self, client):
        resp = client.post(
            "/v1/banking/n43/parse",
            files={"n43_file": ("statement.n43", SAMPLE_N43_SINGLE_ACCOUNT.encode(), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["account_count"] == 1
        assert len(data["accounts"]) == 1
        acc = data["accounts"][0]
        assert len(acc["transactions"]) == 2
        assert acc["transactions"][0]["amount"] == 1000.0
        assert acc["transactions"][1]["amount"] == -50000.0

    def test_parse_empty_n43(self, client):
        resp = client.post(
            "/v1/banking/n43/parse",
            files={"n43_file": ("empty.n43", b"", "text/plain")},
        )
        assert resp.status_code == 400

    def test_parse_no_file(self, client):
        resp = client.post("/v1/banking/n43/parse")
        assert resp.status_code == 422

    def test_parse_invalid_n43(self, client):
        resp = client.post(
            "/v1/banking/n43/parse",
            files={"n43_file": ("bad.n43", b"not a valid n43 file at all", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_parse_empty_account_n43(self, client):
        resp = client.post(
            "/v1/banking/n43/parse",
            files={"n43_file": ("empty_acc.n43", SAMPLE_N43_EMPTY_ACCOUNT.encode(), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["account_count"] == 1
        assert len(data["accounts"][0]["transactions"]) == 0

    def test_parse_with_foreign_currency(self, client):
        resp = client.post(
            "/v1/banking/n43/parse",
            files={"n43_file": ("fx.n43", SAMPLE_N43_WITH_FOREIGN_CURRENCY.encode(), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["account_count"] == 1
        assert len(data["accounts"][0]["transactions"]) == 1


# ---------------------------------------------------------------------------
# Fase 17.4 — SEPA / pain.001
# ---------------------------------------------------------------------------

class TestValidateBic:
    """Pure Python BIC validation tests."""

    def test_valid_8_char_bic(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("BSCHESMM")
        assert result["valid"] is True
        assert result["bic"] == "BSCHESMM"
        assert result["country_code"] == "ES"
        assert result["location_code"] == "MM"
        assert result["branch_code"] is None

    def test_valid_11_char_bic(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("DEUTDEFF500")
        assert result["valid"] is True
        assert result["bic"] == "DEUTDEFF500"
        assert result["branch_code"] == "500"

    def test_invalid_bic_short(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("ABC")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_invalid_bic_long(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("BSCHESMMMMMMM")
        assert result["valid"] is False

    def test_empty_bic(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("")
        assert result["valid"] is False
        assert result["bic"] == ""

    def test_bic_lowercase(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("bschesmm")
        assert result["valid"] is True
        assert result["bic"] == "BSCHESMM"

    def test_bic_with_spaces(self):
        from apps.api.banking.sepa import validate_bic
        result = validate_bic("BSCH ES MM")
        assert result["valid"] is False  # spaces not allowed in cleaned


class TestGeneratePain001:
    """pain.001 XML generation tests."""

    def test_generate_single_transaction(self):
        from apps.api.banking.sepa import generate_pain001
        xml_bytes = generate_pain001(
            debtor_name="Test S.L.",
            debtor_iban="ES9121000418450200051332",
            debtor_bic="BSCHESMM",
            execution_date="2025-01-15",
            transactions=[{
                "creditor_name": "Juan Perez",
                "creditor_iban": "ES9121000418450200051332",
                "amount": 1500.50,
                "currency": "EUR",
                "remittance_info": "Factura 001",
            }],
        )
        assert xml_bytes
        assert b"pain.001" in xml_bytes or b"Document" in xml_bytes
        assert b"Test S.L." in xml_bytes
        assert b"Juan Perez" in xml_bytes
        assert b"1500.50" in xml_bytes
        assert b"ES9121000418450200051332" in xml_bytes

    def test_generate_multiple_transactions(self):
        from apps.api.banking.sepa import generate_pain001
        xml_bytes = generate_pain001(
            debtor_name="Test S.L.",
            debtor_iban="ES9121000418450200051332",
            transactions=[
                {
                    "creditor_name": "Creditor A",
                    "creditor_iban": "ES9121000418450200051332",
                    "amount": 100.00,
                },
                {
                    "creditor_name": "Creditor B",
                    "creditor_iban": "DE89370400440532013000",
                    "amount": 200.00,
                },
            ],
        )
        assert xml_bytes
        assert b"Creditor A" in xml_bytes
        assert b"Creditor B" in xml_bytes

    def test_generate_no_bic(self):
        from apps.api.banking.sepa import generate_pain001
        xml_bytes = generate_pain001(
            debtor_name="Test S.L.",
            debtor_iban="ES9121000418450200051332",
            transactions=[{
                "creditor_name": "Juan",
                "creditor_iban": "ES9121000418450200051332",
                "amount": 50.00,
            }],
        )
        assert xml_bytes
        assert b"Document" in xml_bytes

    def test_generate_default_date(self):
        from apps.api.banking.sepa import generate_pain001
        xml_bytes = generate_pain001(
            debtor_name="Test S.L.",
            debtor_iban="ES9121000418450200051332",
            transactions=[{
                "creditor_name": "Juan",
                "creditor_iban": "ES9121000418450200051332",
                "amount": 50.00,
            }],
        )
        assert xml_bytes
        # Should have today's date in the XML


class TestGroupTransactions:
    """Transaction grouping tests."""

    def test_group_by_creditor_iban(self):
        from apps.api.banking.sepa import group_transactions
        txs = [
            {"creditor_iban": "ES111", "amount": 100.0},
            {"creditor_iban": "ES222", "amount": 200.0},
            {"creditor_iban": "ES111", "amount": 50.0},
        ]
        batches = group_transactions(txs, group_by="creditor_iban")
        assert len(batches) == 2
        assert batches[0][0]["creditor_iban"] == "ES111"
        assert batches[0][1]["creditor_iban"] == "ES111"
        assert batches[1][0]["creditor_iban"] == "ES222"

    def test_group_max_batch_size(self):
        from apps.api.banking.sepa import group_transactions
        txs = [
            {"creditor_iban": "ES111", "amount": float(i)}
            for i in range(10)
        ]
        batches = group_transactions(txs, max_batch_size=3, group_by="creditor_iban")
        assert len(batches) == 4  # 3+3+3+1
        assert batches[0][0]["creditor_iban"] == "ES111"
        assert batches[3][0]["creditor_iban"] == "ES111"

    def test_group_empty(self):
        from apps.api.banking.sepa import group_transactions
        batches = group_transactions([], group_by="creditor_iban")
        assert batches == []


class TestSepaEndpoints:
    """SEPA API endpoint tests via FastAPI TestClient."""

    def test_bic_validate_valid(self, client):
        resp = client.post(
            "/v1/banking/sepa/bic/validate",
            json={"bic": "BSCHESMM"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is True
        assert data["result"]["bic"] == "BSCHESMM"
        assert data["result"]["country_code"] == "ES"

    def test_bic_validate_invalid(self, client):
        resp = client.post(
            "/v1/banking/sepa/bic/validate",
            json={"bic": "ABC"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["valid"] is False

    def test_sepa_generate_valid(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "ES9121000418450200051332",
                "debtor_bic": "BSCHESMM",
                "execution_date": "2025-01-15",
                "transactions": [
                    {
                        "creditor_name": "Juan Perez",
                        "creditor_iban": "ES9121000418450200051332",
                        "amount": 1500.50,
                        "currency": "EUR",
                        "remittance_info": "Factura 001",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["document_type"] == "pain.001.001.03"
        assert data["group_header_msg_id"]
        assert data["payment_info_count"] == 1
        assert data["xml_size_bytes"] > 0

    def test_sepa_generate_multiple_transactions(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "ES9121000418450200051332",
                "transactions": [
                    {
                        "creditor_name": "Creditor A",
                        "creditor_iban": "ES9121000418450200051332",
                        "amount": 100.00,
                    },
                    {
                        "creditor_name": "Creditor B",
                        "creditor_iban": "DE89370400440532013000",
                        "amount": 200.00,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["payment_info_count"] == 2  # grouped by IBAN

    def test_sepa_generate_invalid_iban(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "INVALID",
                "transactions": [
                    {
                        "creditor_name": "Juan",
                        "creditor_iban": "ES9121000418450200051332",
                        "amount": 100.00,
                    },
                ],
            },
        )
        assert resp.status_code == 400

    def test_sepa_generate_invalid_bic(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "ES9121000418450200051332",
                "debtor_bic": "INVALID",
                "transactions": [
                    {
                        "creditor_name": "Juan",
                        "creditor_iban": "ES9121000418450200051332",
                        "amount": 100.00,
                    },
                ],
            },
        )
        assert resp.status_code == 400

    def test_sepa_generate_negative_amount(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "ES9121000418450200051332",
                "transactions": [
                    {
                        "creditor_name": "Juan",
                        "creditor_iban": "ES9121000418450200051332",
                        "amount": -100.00,
                    },
                ],
            },
        )
        assert resp.status_code == 400

    def test_sepa_generate_empty_transactions(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "ES9121000418450200051332",
                "transactions": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["payment_info_count"] == 0

    def test_sepa_group_transactions(self, client):
        resp = client.post(
            "/v1/banking/sepa/group",
            json={
                "transactions": [
                    {"creditor_iban": "ES111", "amount": 100.0},
                    {"creditor_iban": "ES222", "amount": 200.0},
                    {"creditor_iban": "ES111", "amount": 50.0},
                ],
                "group_by": "creditor_iban",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_transactions"] == 3
        assert data["total_batches"] == 2
        assert data["batches"][0]["transaction_count"] == 2
        assert data["batches"][1]["transaction_count"] == 1

    def test_sepa_group_with_max_batch_size(self, client):
        txs = [{"creditor_iban": "ES111", "amount": float(i)} for i in range(10)]
        resp = client.post(
            "/v1/banking/sepa/group",
            json={
                "transactions": txs,
                "max_batch_size": 3,
                "group_by": "creditor_iban",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_batches"] == 4  # 3+3+3+1

    def test_sepa_generate_default_execution_date(self, client):
        resp = client.post(
            "/v1/banking/sepa/generate",
            json={
                "debtor_name": "Test S.L.",
                "debtor_iban": "ES9121000418450200051332",
                "transactions": [
                    {
                        "creditor_name": "Juan",
                        "creditor_iban": "ES9121000418450200051332",
                        "amount": 100.00,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
