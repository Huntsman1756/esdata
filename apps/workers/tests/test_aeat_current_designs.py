from __future__ import annotations

import io
import sys
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aeat_current_designs as worker


class FakeResponse:
    def __init__(self, text: str = "", content: bytes = b""):
        self.text = text
        self.content = content

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def get(self, url: str):
        return FakeResponse(text=self.pages[url])


def test_discover_current_design_links_filters_1xx_2xx_official_links():
    pages = {
        worker.DESIGN_INDEX_URLS[0]: """
            <a href="modelos-100-199.html">100 - indice sin recurso</a>
            <a href="/static_files/Sede/Disenyo_registro/DR_100_199/dr111.xls">
              111 - Orden EHA/3127/2009 (xls)
            </a>
            <a href="https://example.com/bad.xls">123 - externo</a>
        """,
        worker.DESIGN_INDEX_URLS[1]: """
            <a href="/static_files/Sede/Disenyo_registro/DR_200_299/DR202e25.xlsx">
              202 - Ejercicio 2025 y siguientes
            </a>
            <a href="/static_files/Sede/Disenyo_registro/DR_Resto_Mod/anexo.xlsx">
              Anexo modelo 222: Comunicación de datos adicionales
            </a>
        """,
    }

    links = worker.discover_current_design_links(FakeClient(pages))

    assert [link["codigo"] for link in links] == ["111", "202", "222"]
    assert all(link["url"].startswith(worker.AEAT_SEDE) for link in links)


def test_extract_spreadsheet_fields_from_design_register():
    wb = Workbook()
    ws = wb.active
    ws.title = "dr M202 (1)"
    ws.append(["Agencia Tributaria"])
    ws.append(["Nº", "Posic.", "Lon", "Tipo", "Descripción", "Contenido"])
    ws.append([1, 1, 2, "An", "Inicio del identificador", 'Constante "<T"'])
    ws.append([2, 3, 3, "Num", "Modelo", 'Constante "202"'])
    payload = io.BytesIO()
    wb.save(payload)

    fields = worker.extract_spreadsheet_fields(payload.getvalue())

    assert [field["codigo"] for field in fields] == ["DR:1:1", "DR:1:2"]
    assert fields[0]["tipo_casilla"] == "diseno_registro_campo"
    assert "Posic." in fields[0]["descripcion"]


def test_extract_properties_fields_from_model_100_dictionary():
    payload = (
        "DPNIF_D=[/DatosIdentificativos/Declarante/DPNIF_D][X][*01][Primer Declarante: NIF]\n"
        "INDV=[/DatosIdentificativos/Declarante/INDV][LGC][###][Calculo individual]\n"
    ).encode("iso-8859-1")

    fields = worker.extract_properties_fields(payload)

    assert [field["codigo"] for field in fields] == ["DRP:DPNIF_D", "DRP:INDV"]
    assert fields[0]["etiqueta"] == "Primer Declarante: NIF"
    assert "Casilla oficial: *01" in fields[0]["descripcion"]
    assert "Casilla oficial" not in fields[1]["descripcion"]


def test_extract_pdf_text_fields_from_numbered_design_table():
    text = """
    Descripcion de hoja DISENO DE REGISTRO
    No Posic. Lon Tipo Descripcion Validacion Contenido Uso
    1 1 9 An Inicio del identificador de modelo y pagina obligatorio <T145010>
    2 10 1 A Indicador de pagina complementaria obligatorio blanco o C
    3 11 9 An NIF del declarante obligatorio
    """

    fields = worker.extract_pdf_text_fields(text)

    assert [field["codigo"] for field in fields] == ["DRPDF:N:1", "DRPDF:N:2", "DRPDF:N:3"]
    assert fields[0]["etiqueta"] == "Inicio del identificador de modelo y pagina"
    assert fields[0]["tipo_casilla"] == "diseno_registro_campo"
    assert "Posic.: 1" in fields[0]["descripcion"]
    assert "Lon.: 9" in fields[0]["descripcion"]


def test_extract_pdf_text_fields_from_positions_nature_table():
    text = """
    MODELO 196
    DISENOS DE REGISTRO
    POSICIONES NATURALEZA DESCRIPCION DE LOS CAMPOS
    1 Numerico TIPO DE REGISTRO.
    Constante numero 1.
    2-4 Numerico MODELO DECLARACION.
    Constante 196.
    5-8 Numerico EJERCICIO.
    """

    fields = worker.extract_pdf_text_fields(text)

    assert [field["codigo"] for field in fields] == [
        "DRPDF:POS:1",
        "DRPDF:POS:2-4",
        "DRPDF:POS:5-8",
    ]
    assert fields[1]["etiqueta"] == "MODELO DECLARACION"
    assert "Posiciones: 2-4" in fields[1]["descripcion"]
    assert "Naturaleza: Numerico" in fields[1]["descripcion"]


def test_is_pdf_format_detects_official_design_pdf_urls():
    assert worker._is_pdf_format("https://sede.agenciatributaria.gob.es/static_files/dr196.pdf")
    assert worker._is_pdf_format("https://sede.agenciatributaria.gob.es/static_files/dr196.PDF?download=1")
    assert not worker._is_pdf_format("https://sede.agenciatributaria.gob.es/static_files/dr196.xlsx")


def test_extract_deadline_date_from_calendar_title():
    assert worker._extract_deadline_date("Hasta el 20 de enero").isoformat() == "2026-01-20"
    assert worker._extract_deadline_date("Hasta el 30 de junio").isoformat() == "2026-06-30"
    assert worker._extract_deadline_date("Sin fecha") is None
