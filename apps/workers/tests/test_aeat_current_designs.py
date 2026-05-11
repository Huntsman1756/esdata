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


def test_extract_deadline_date_from_calendar_title():
    assert worker._extract_deadline_date("Hasta el 20 de enero").isoformat() == "2026-01-20"
    assert worker._extract_deadline_date("Hasta el 30 de junio").isoformat() == "2026-06-30"
    assert worker._extract_deadline_date("Sin fecha") is None
