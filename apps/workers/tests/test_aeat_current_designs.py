from __future__ import annotations

import io
import sys
import zipfile
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

    assert [link["codigo"] for link in links[:3]] == ["111", "202", "222"]
    assert {"172", "173"}.issubset({link["codigo"] for link in links})
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


def test_extract_xsd_zip_fields_from_declaracion_informativa_schema():
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:ddii="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/dit/adu/eeca/esquemas"
               targetNamespace="https://example.test">
      <xs:complexType name="DeclaracionInformativa">
        <xs:sequence>
          <xs:element name="Cabecera" type="ddii:CabeceraDI"/>
          <xs:element name="Declarado" type="ddii:DeclaradoType" maxOccurs="10000"/>
        </xs:sequence>
      </xs:complexType>
      <xs:complexType name="CabeceraDI">
        <xs:sequence>
          <xs:element name="Modelo" type="ddii:ModeloType"/>
          <xs:element name="Ejercicio" type="ddii:YearType"/>
        </xs:sequence>
      </xs:complexType>
      <xs:complexType name="DeclaradoType">
        <xs:sequence>
          <xs:element name="IDRegistroDeclarado" type="ddii:TextMax20Type"/>
          <xs:element name="IDDeclarado">
            <xs:complexType>
              <xs:choice>
                <xs:element name="NIF" type="ddii:NIFType"/>
                <xs:element name="IDOtro" type="ddii:IDOtroType"/>
              </xs:choice>
            </xs:complexType>
          </xs:element>
        </xs:sequence>
      </xs:complexType>
    </xs:schema>
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipped:
        zipped.writestr("DeclaracionInformativa172.xsd", xsd)
        zipped.writestr("RespuestaDeclaracion172.xsd", xsd)

    fields = worker.extract_xsd_zip_fields(buffer.getvalue())

    assert [field["etiqueta"] for field in fields] == [
        "DeclaracionInformativa > Cabecera > Modelo",
        "DeclaracionInformativa > Cabecera > Ejercicio",
        "DeclaracionInformativa > Declarado > IDRegistroDeclarado",
        "DeclaracionInformativa > Declarado > IDDeclarado > NIF",
        "DeclaracionInformativa > Declarado > IDDeclarado > IDOtro",
    ]
    assert fields[0]["codigo"] == "XSD:DeclaracionInformativa/Cabecera/Modelo"
    assert fields[0]["tipo_casilla"] == "diseno_registro_xsd_campo"
    assert fields[4]["codigo"] == "XSD:DeclaracionInformativa/Declarado/IDDeclarado/IDOtro"
    assert "Fuente XSD: DeclaracionInformativa172.xsd" in fields[0]["descripcion"]
    assert "XPath: /DeclaracionInformativa/Cabecera/Modelo" in fields[0]["descripcion"]
    assert "maxOccurs: 1" in fields[0]["descripcion"]


def test_extract_direct_xsd_fields_from_declaracion_informativa_schema():
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               targetNamespace="https://example.test">
      <xs:complexType name="DeclaracionInformativa">
        <xs:sequence>
          <xs:element name="Cabecera">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="Modelo" type="xs:string"/>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
        </xs:sequence>
      </xs:complexType>
    </xs:schema>
    """

    fields = worker.extract_xsd_fields(xsd.encode("utf-8"), "DeclaracionInformativa.xsd")

    assert fields == [
        {
            "codigo": "XSD:DeclaracionInformativa/Cabecera/Modelo",
            "etiqueta": "DeclaracionInformativa > Cabecera > Modelo",
            "descripcion": (
                "XPath: /DeclaracionInformativa/Cabecera/Modelo; "
                "Fuente XSD: DeclaracionInformativa.xsd; Tipo XSD: xs:string; "
                "minOccurs: 1; maxOccurs: 1"
            ),
            "tipo_casilla": "diseno_registro_xsd_campo",
            "pagina": None,
            "orden": 1,
        }
    ]


def test_extract_xsd_zip_fields_resolves_presentation_imported_types():
    presentation = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:body="urn:test:body"
               targetNamespace="urn:test:presentation">
      <xs:import namespace="urn:test:body" schemaLocation="BodyTypes.xsd"/>
      <xs:complexType name="PresentationHeader_Type">
        <xs:sequence>
          <xs:element name="PresentationCode" type="xs:string">
            <xs:annotation><xs:documentation>Identificador del mensaje</xs:documentation></xs:annotation>
          </xs:element>
        </xs:sequence>
      </xs:complexType>
      <xs:element name="Presentation">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="PresentationHeader" type="PresentationHeader_Type"/>
            <xs:element name="PresentationBody" type="body:Body_Type"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>
    """
    body = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               targetNamespace="urn:test:body">
      <xs:complexType name="Base_Type">
        <xs:sequence>
          <xs:element name="BaseField" type="xs:string"/>
        </xs:sequence>
      </xs:complexType>
      <xs:complexType name="Body_Type">
        <xs:complexContent>
          <xs:extension base="Base_Type">
            <xs:sequence>
              <xs:element name="ReportingPeriod" type="xs:date"/>
              <xs:element name="Amount" type="xs:decimal" minOccurs="0"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>
    </xs:schema>
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipped:
        zipped.writestr("ModelPresentation_v1.0.xsd", presentation)
        zipped.writestr("BodyTypes.xsd", body)

    fields = worker.extract_xsd_zip_fields(buffer.getvalue())

    assert [field["codigo"] for field in fields] == [
        "XSD:Presentation/PresentationHeader/PresentationCode",
        "XSD:Presentation/PresentationBody/BaseField",
        "XSD:Presentation/PresentationBody/ReportingPeriod",
        "XSD:Presentation/PresentationBody/Amount",
    ]
    assert fields[0]["tipo_casilla"] == "diseno_registro_xsd_campo"
    assert "Documentacion: Identificador del mensaje" in fields[0]["descripcion"]
    assert "minOccurs: 0" in fields[3]["descripcion"]


def test_extract_xsd_zip_fields_accepts_spanish_presentacion_root():
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="M240Presentacion">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="Cabecera">
              <xs:complexType>
                <xs:sequence>
                  <xs:element name="CodigoPresentacion" type="xs:string"/>
                </xs:sequence>
              </xs:complexType>
            </xs:element>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipped:
        zipped.writestr("M240CDNtnlPresentacion_v1.1.xsd", xsd)

    fields = worker.extract_xsd_zip_fields(buffer.getvalue())

    assert fields[0]["codigo"] == "XSD:M240Presentacion/Cabecera/CodigoPresentacion"


def test_supplemental_links_include_modelo_289_official_xsd_zip():
    links = {link["codigo"]: link for link in worker.SUPPLEMENTAL_CURRENT_DESIGN_LINKS}

    link = links["289"]

    assert link["tipo_recurso"] == "diseno_registro_xsd"
    assert link["formato"] == "zip"
    assert link["url"].endswith("289_XSD_2.0_WSDL_2.0.1.zip")
    assert "agenciatributaria.gob.es" in link["url"]


def test_supplemental_links_use_current_modelo_172_xsd_wsdl_zip():
    links = {link["codigo"]: link for link in worker.SUPPLEMENTAL_CURRENT_DESIGN_LINKS}

    link = links["172"]

    assert link["tipo_recurso"] == "diseno_registro_xsd"
    assert link["formato"] == "zip"
    assert link["url"].endswith("GI53/2024/Esquemas_WSDL_servicios_web.zip")
    assert "Esquemas172.zip" not in link["url"]


def test_supplemental_links_include_modelo_303_official_design_xlsx():
    links = {link["codigo"]: link for link in worker.SUPPLEMENTAL_CURRENT_DESIGN_LINKS}

    link = links["303"]

    assert link["tipo_recurso"] == "diseno_registro"
    assert link["formato"] == "xlsx"
    assert link["url"].endswith("DR303e26v101.xlsx")
    assert "modelos-300-399.html" in link["source_index"]


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


def test_extract_pdf_text_fields_accepts_nature_with_trailing_dot():
    text = """
    POSICIONES NATURALEZA DESCRIPCION DE LOS CAMPOS
    1 Numerico. TIPO DE REGISTRO.
    2-4 Numerico. MODELO DECLARACION.
    9-17 Alfanumerico. NIF DEL DECLARANTE.
    """

    fields = worker.extract_pdf_text_fields(text)

    assert [field["codigo"] for field in fields] == [
        "DRPDF:POS:1",
        "DRPDF:POS:2-4",
        "DRPDF:POS:9-17",
    ]
    assert fields[2]["etiqueta"] == "NIF DEL DECLARANTE"


def test_extract_pdf_text_fields_rejects_lowercase_nature_noise():
    text = """
    POSICIONES NATURALEZA DESCRIPCION DE LOS CAMPOS
    224 a 235 correspondientes al registro de tipo 2)
    """

    fields = worker.extract_pdf_text_fields(text)

    assert fields == []


def test_extract_pdf_text_fields_accepts_mixed_case_nature_abbreviation():
    text = """
    POSICIONES NATURALEZA DESCRIPCION DE LOS CAMPOS
    1 Num TIPO DE REGISTRO.
    2-4 AN MODELO DECLARACION.
    """

    fields = worker.extract_pdf_text_fields(text)

    assert [field["codigo"] for field in fields] == ["DRPDF:POS:1", "DRPDF:POS:2-4"]


def test_extract_pdf_text_fields_from_model_296_logical_design_sample():
    text = """
    Diseños lógicos M296 2024
    TIPO DE REGISTRO 1: REGISTRO DEL DECLARANTE
    POSICIONES NATURALEZA DESCRIPCIÓN DE LOS CAMPOS
    1 Numérico TIPO DE REGISTRO
    2-4 Numérico MODELO DECLARACIÓN
    5-8 Numérico EJERCICIO
    9-17 Alfanumérico NIF DEL DECLARANTE
    TIPO DE REGISTRO 2: REGISTRO DE PERCEPTOR
    18-57 Alfanumérico APELLIDOS Y NOMBRE O RAZÓN SOCIAL
    122-124 Alfabético CLAVE
    """

    fields = worker.extract_pdf_text_fields(text)

    assert len(fields) == 6
    assert fields[0]["codigo"] == "DRPDF:POS:1"
    assert fields[3]["etiqueta"] == "NIF DEL DECLARANTE"
    assert fields[5]["etiqueta"] == "CLAVE"
    assert "Posiciones: 122-124" in fields[5]["descripcion"]


def test_delete_existing_design_fields_only_removes_design_rows():
    class FakeResult:
        rowcount = 3

    class FakeConn:
        def __init__(self):
            self.statement = ""
            self.params = None

        def execute(self, statement, params):
            self.statement = str(statement)
            self.params = params
            return FakeResult()

    conn = FakeConn()

    deleted = worker._delete_existing_design_fields(conn, 123)

    assert deleted == 3
    assert conn.params == {"campana_id": 123}
    assert "DELETE FROM modelo_casilla" in conn.statement
    assert "diseno_registro_campo" in conn.statement
    assert "diseno_registro_xsd_campo" in conn.statement
    assert "tipo_casilla IN" in conn.statement


def test_is_pdf_format_detects_official_design_pdf_urls():
    assert worker._is_pdf_format("https://sede.agenciatributaria.gob.es/static_files/dr196.pdf")
    assert worker._is_pdf_format("https://sede.agenciatributaria.gob.es/static_files/dr196.PDF?download=1")
    assert not worker._is_pdf_format("https://sede.agenciatributaria.gob.es/static_files/dr196.xlsx")


def test_extract_deadline_date_from_calendar_title():
    assert worker._extract_deadline_date("Hasta el 20 de enero").isoformat() == "2026-01-20"
    assert worker._extract_deadline_date("Hasta el 30 de junio").isoformat() == "2026-06-30"
    assert worker._extract_deadline_date("Sin fecha") is None
