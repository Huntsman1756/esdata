"""Tests for ESMA FIRDS DLTINS loader."""

import sys
import zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker_esma_firds import parse_dltins_instruments


def test_parse_dltins_instruments_extracts_bounded_sample():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <BizData xmlns="urn:iso:std:iso:20022:tech:xsd:head.003.001.01">
      <Pyld>
        <Document>
          <FinInstrmRptgRefDataDltaRpt>
            <FinInstrm>
              <NewRcrd>
                <FinInstrmGnlAttrbts>
                  <Id>ES0000000001</Id>
                  <FullNm>Instrument One</FullNm>
                  <ClssfctnTp>ESXXXX</ClssfctnTp>
                  <NtnlCcy>EUR</NtnlCcy>
                </FinInstrmGnlAttrbts>
                <TradgVnRltdAttrbts>
                  <Id>XMAD</Id>
                  <FrstTradDt>2026-05-12T00:00:00Z</FrstTradDt>
                </TradgVnRltdAttrbts>
              </NewRcrd>
            </FinInstrm>
          </FinInstrmRptgRefDataDltaRpt>
        </Document>
      </Pyld>
    </BizData>
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        archive.writestr("DLTINS.xml", xml)

    instruments = parse_dltins_instruments(zip_buffer.getvalue(), limit=1000)

    assert instruments == [
        {
            "isin": "ES0000000001",
            "nombre": "Instrument One",
            "tipo_instrumento": "ESXXXX",
            "fecha_admision": instruments[0]["fecha_admision"],
            "mic": "XMAD",
            "moneda": "EUR",
        }
    ]
    assert instruments[0]["fecha_admision"].isoformat() == "2026-05-12"
