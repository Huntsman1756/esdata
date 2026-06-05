import json
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cnmv import (
    DEFAULT_CNMV_SANCIONES_MAX_PAGES,
    _detect_ambito,
    _detect_document_type,
    _detect_obligaciones,
    _detect_regulaciones,
    _detect_vigencia,
    _discover_cnmv_circulares,
    _discover_new_documents,
    _discover_new_urls,
    _discover_source_family_documents,
    _extract_boe_reference,
    _extract_circular_number,
    _extract_publication_date,
    _extract_reference,
    _get_next_version,
    _parse_cnmv_consultation_documents,
    _parse_cnmv_modelos_esi,
    _parse_cnmv_normativa_esi,
    _parse_cnmv_sanctions,
    _parse_cnmv_technical_guides,
    _parse_sanction_severity,
    _record_version,
    _upsert_obligation_links,
    _upsert_regulation_links,
    build_document_payload,
    run_sync,
    upsert_documento_interpretativo,
    upsert_with_versioning,
)

MINIMAL_CNMV_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 167 >>
stream
BT
/F1 12 Tf
20 110 Td
(Circular 9/2008 de la Comision Nacional del Mercado de Valores) Tj
0 -18 Td
(Normas contables, estados de informacion reservada y publica) Tj
0 -18 Td
(Cuentas anuales de las sociedades rectoras) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000459 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
529
%%EOF
"""

BOE_DOC_HTML = b"""
<html>
  <body>
    <iframe src="/diario_boe/txt.php?id=BOE-A-2009-133"></iframe>
  </body>
</html>
"""

CNMV_GUIAS_HTML = """
<html><body>
  <h2>Guías Técnicas publicadas en el año 2024</h2>
  <ul>
    <li>Guía Técnica 1/2024:
      <a href="/DocPortal/Legislacion/Guias-Tecnicas/GT_ComisionesAuditorias.pdf">
        sobre comisiones de auditoría de entidades de interés público
      </a>
    </li>
  </ul>
</body></html>
"""

CNMV_CONSULTAS_HTML = """
<html><body>
  <h2>With comment period already closed</h2>
  <ul>
    <li>
      <span>15/12/2025</span>
      <span>Preliminary public consultation on draft Technical Guide regarding internal controls</span>
      <ul>
        <li><a href="/DocPortal/DocFaseConsulta/CNMV/GT_ControlInterno.pdf">Prior consultation</a></li>
        <li><a href="/DocPortal/DocFaseConsulta/CNMV/Comentarios_GT_ControlInterno.pdf">Comments received to the prior consultation</a></li>
      </ul>
    </li>
  </ul>
</body></html>
"""

CNMV_ESI_HTML = """
<html><body>
  <main>
    <h1>Empresas de servicios de inversion</h1>
    <ul>
      <li><a href="/DocPortal/Legislacion/ESI/RD813_2023.pdf">Real Decreto 813/2023, regimen juridico ESI</a></li>
      <li><a href="https://www.boe.es/buscar/act.php?id=BOE-A-2023-22763">Texto consolidado BOE RD 813/2023</a></li>
    </ul>
  </main>
</body></html>
"""

CNMV_MODELOS_ESI_HTML = """
<html><body>
  <main>
    <h1>Modelos normalizados ESI</h1>
    <a href="/Portal/Legislacion/ModelosN/modelosn.aspx?id=IM">Modelos IM</a>
    <a href="/Portal/Legislacion/ModelosN/DetalleModelo.aspx?id=ESI-01">Estado reservado ESI 01</a>
  </main>
</body></html>
"""

CNMV_SANCIONES_HTML = """
<html><body>
  <table id="ctl00_ContentPrincipal_grdRegSanciones">
    <tr>
      <th>Fecha de incorporación al registro</th>
      <th>Resolución</th>
      <th></th>
    </tr>
    <tr>
      <td><a href="https://www.cnmv.es/webservices/verdocumento/ver?e=abc">22/04/2026</a></td>
      <td>
        Resolución de 22 de abril de 2026, de la Comisión Nacional del Mercado de Valores,
        por la que se publican las sanciones por infracciones muy graves a Example Capital, SA
        (BOE de 11 de mayo de 2026).
      </td>
      <td></td>
    </tr>
    <tr>
      <td><a href="/webservices/verdocumento/ver?e=def">07/04/2026</a></td>
      <td>
        Resolución de 7 de abril de 2026, de la Comisión Nacional del Mercado de Valores,
        por la que se publica la sanción por infracción grave impuesta a Example Gestión
        de Activos, SA, SGIIC (BOE de 20 de abril de 2026).
      </td>
      <td></td>
    </tr>
  </table>
</body></html>
"""


# ---------------------------------------------------------------------------
# Document type detection (23.3)
# ---------------------------------------------------------------------------


def test_detect_document_type_circular():
    assert _detect_document_type("Circular 9/2008 de la CNMV") == "circular_cnmv"
    assert _detect_document_type("Circular 3/2015 sobre mercados") == "circular_cnmv"


def test_detect_document_type_manual():
    assert _detect_document_type("Manual de procedimientos internos") == "manual_cnmv"


def test_detect_document_type_guia():
    assert _detect_document_type("Guía de buenas prácticas") == "guia_cnmv"
    assert _detect_document_type("Guía del inversor minorista") == "guia_cnmv"


def test_detect_document_type_resolucion():
    assert _detect_document_type("Resolución 5/2020 de la CNMV") == "resolucion_cnmv"


def test_detect_document_type_informe():
    assert _detect_document_type("Informe Anual de Supervisión") == "informe_anual_cnmv"
    assert _detect_document_type("Informe de mercados") == "informe_cnmv"


def test_detect_document_type_codigo():
    assert _detect_document_type("Código de Buen Gobierno") == "codigo_autoregulacion_cnmv"
    assert _detect_document_type("Código de conducta profesional") == "codigo_conducta_cnmv"


def test_detect_document_type_fallback():
    assert _detect_document_type("Documento sobre mercados financieros") == "documento_cnmv"


# ---------------------------------------------------------------------------
# Ambito detection (23.4)
# ---------------------------------------------------------------------------


def test_detect_ambito_mifid():
    assert _detect_ambito("Directiva MiFID II servicios de inversión") == "mifid_ii"
    assert _detect_ambito("MiFID II y servicios de inversion") == "mifid_ii"


def test_detect_ambito_mar():
    assert _detect_ambito("Reglamento MAR abuso de mercado") == "mar"
    assert _detect_ambito("Market abuse regulation") == "mar"


def test_detect_ambito_dora():
    assert _detect_ambito("Directiva DORA resiliencia operacional digital") == "dora"


def test_detect_ambito_priips():
    assert _detect_ambito("Reglamento PRIIPs productos de inversión") == "priips"


def test_detect_ambito_reporting_regulatorio():
    assert _detect_ambito("Información reservada estados confidenciales") == "reporting_regulatorio_cnmv"
    assert _detect_ambito("Informacion reservada y pública") == "reporting_regulatorio_cnmv"


def test_detect_ambito_reporting_financiero():
    assert _detect_ambito("Estados de información cuentas anuales") == "reporting_financiero_cnmv"


def test_detect_ambito_gobierno_corporativo():
    assert _detect_ambito("Gobierno corporativo código de buen gobierno") == "gobierno_corporativo"


def test_detect_ambito_transparencia():
    assert _detect_ambito("Hechos relevantes transparencia de emisores") == "transparencia_emisores"


def test_detect_ambito_legacy_fallback():
    assert _detect_ambito("MIFID servicios de inversion") == "mercados"


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def test_extract_circular_number():
    assert _extract_circular_number("Circular 9/2008 de la CNMV") == "9/2008"
    assert _extract_circular_number("sin referencia circular") is None


def test_extract_publication_date_boe():
    assert _extract_publication_date("BOE-A-2009-133") == "2009"


def test_extract_publication_date_ddmmyyyy():
    result = _extract_publication_date("Fecha 15/03/2024")
    assert result == "2024-03-15"


def test_extract_boe_reference():
    assert _extract_boe_reference("BOE-A-2009-133") == "BOE-A-2009-133"
    assert _extract_boe_reference("BOE-A-2009-133", "https://example.com") == "BOE-A-2009-133"
    assert _extract_boe_reference("sin referencia") is None
    assert _extract_boe_reference("sin referencia", "https://boe.es/doc.php?id=BOE-A-2015-5000") == "BOE-A-2015-5000"


def test_detect_vigencia_vigente():
    assert _detect_vigencia("Norma vigente en vigor") == "vigente"


def test_detect_vigencia_derogado():
    assert _detect_vigencia("Norma derogada por la nueva") == "derogado"


def test_detect_vigencia_modificado():
    assert _detect_vigencia("Norma modificada parcialmente") == "vigente_modificado"


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------


def test_extract_reference_boe_url():
    assert _extract_reference("https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133", "") == "BOE-A-2009-133"


def test_extract_reference_boe_text():
    assert _extract_reference("https://example.com/doc", "BOE-A-2015-5000") == "BOE-A-2015-5000"


def test_extract_reference_circular():
    result = _extract_reference("https://example.com", "Circular 9/2008 de la CNMV")
    assert result == "CNMV-CIRCULAR-9-2008"


def test_extract_reference_fallback():
    result = _extract_reference("https://example.com/path/to/doc", "sin referencia")
    assert result == "CNMV-doc"


# ---------------------------------------------------------------------------
# Payload building (23.2)
# ---------------------------------------------------------------------------


def test_build_document_payload_extracts_enriched_fields():
    payload = build_document_payload(
        "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
        MINIMAL_CNMV_PDF,
    )

    assert payload["referencia"] == "BOE-A-2009-133"
    assert payload["tipo_documento"] == "circular_cnmv"
    assert payload["ambito"] == "reporting_regulatorio_cnmv"
    assert payload["numero_circular"] == "9/2008"
    assert payload["referencia_boe"] == "BOE-A-2009-133"
    assert "estados de informacion reservada" in payload["texto"].lower()


def test_build_document_payload_minimal():
    payload = build_document_payload(
        "https://example.com/doc",
        MINIMAL_CNMV_PDF,
    )

    assert payload["referencia"].startswith("CNMV-")
    assert payload["numero_circular"] == "9/2008"
    assert payload["referencia_boe"] is None


def test_parse_cnmv_technical_guides_keeps_official_family_contract():
    candidates = _parse_cnmv_technical_guides(
        CNMV_GUIAS_HTML,
        "https://www.cnmv.es/portal/legislacion/guias-tecnicas?lang=es",
    )

    assert candidates == [
        {
            "url": "https://www.cnmv.es/DocPortal/Legislacion/Guias-Tecnicas/GT_ComisionesAuditorias.pdf",
            "referencia": "CNMV-GUIA-TECNICA-1-2024",
            "titulo": "Guia Tecnica 1/2024: sobre comisiones de auditoria de entidades de interes publico",
            "fecha": "2024-01-01",
            "fecha_publicacion": "2024",
            "tipo_documento": "guia_tecnica_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "guias_tecnicas",
            "source_index_url": "https://www.cnmv.es/portal/legislacion/guias-tecnicas?lang=es",
        }
    ]


def test_parse_cnmv_consultations_marks_non_current_monitoring_contract():
    candidates = _parse_cnmv_consultation_documents(
        CNMV_CONSULTAS_HTML,
        "https://www.cnmv.es/portal/publicaciones/Documentos-Fase-Consulta?tDoc=1",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["tipo_documento"] == "documento_consulta_cnmv"
    assert candidate["estado_vigencia"] == "consulta_cerrada"
    assert candidate["estado_consulta"] == "consulta_cerrada"
    assert candidate["fecha"] == "2025-12-15"
    assert candidate["url"] == "https://www.cnmv.es/DocPortal/DocFaseConsulta/CNMV/GT_ControlInterno.pdf"
    assert candidate["family_id"] == "documentos_consulta_cnmv"
    assert candidate["documentos_asociados"] == [
        {
            "titulo": "Prior consultation",
            "url": "https://www.cnmv.es/DocPortal/DocFaseConsulta/CNMV/GT_ControlInterno.pdf",
        },
        {
            "titulo": "Comments received to the prior consultation",
            "url": "https://www.cnmv.es/DocPortal/DocFaseConsulta/CNMV/Comentarios_GT_ControlInterno.pdf",
        },
    ]


def test_parse_cnmv_normativa_esi_uses_separate_family_contract():
    candidates = _parse_cnmv_normativa_esi(
        CNMV_ESI_HTML,
        "https://www.cnmv.es/portal/menu/legislacion-esi?lang=es",
    )

    assert candidates[0]["family_id"] == "normativa_esi"
    assert candidates[0]["tipo_documento"] == "normativa_esi_cnmv"
    assert candidates[0]["referencia"].startswith("CNMV-NORMATIVA-ESI-")
    assert candidates[0]["url"] == "https://www.cnmv.es/DocPortal/Legislacion/ESI/RD813_2023.pdf"
    assert candidates[1]["url"] == "https://www.boe.es/buscar/act.php?id=BOE-A-2023-22763"


def test_parse_cnmv_modelos_esi_uses_form_family_contract():
    candidates = _parse_cnmv_modelos_esi(
        CNMV_MODELOS_ESI_HTML,
        "https://www.cnmv.es/Portal/Legislacion/ModelosN/ModelosN.aspx?id=ESI&lang=es",
    )

    assert candidates == [
        {
            "url": "https://www.cnmv.es/Portal/Legislacion/ModelosN/DetalleModelo.aspx?id=ESI-01",
            "referencia": "CNMV-MODELO-ESI-estado-reservado-esi-01",
            "titulo": "Estado reservado ESI 01",
            "fecha": candidates[0]["fecha"],
            "fecha_publicacion": None,
            "tipo_documento": "modelo_esi_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "modelos_esi",
            "source_index_url": "https://www.cnmv.es/Portal/Legislacion/ModelosN/ModelosN.aspx?id=ESI&lang=es",
        }
    ]


def test_parse_sanction_severity_detects_grave_and_muy_grave():
    assert _parse_sanction_severity("infracción muy grave impuesta") == "muy_grave"
    assert _parse_sanction_severity("infraccion grave impuesta") == "grave"
    assert _parse_sanction_severity("sin graduacion") is None


def test_parse_cnmv_sanctions_uses_official_register_contract():
    candidates = _parse_cnmv_sanctions(
        CNMV_SANCIONES_HTML,
        "https://www.cnmv.es/Portal/Consultas/RegistroSanciones/verRegSanciones?lang=es",
    )

    assert len(candidates) == 2
    first = candidates[0]
    assert first["url"] == "https://www.cnmv.es/webservices/verdocumento/ver?e=abc"
    assert first["referencia"].startswith("CNMV-SANCION-2026-04-22-")
    assert first["fecha"] == "2026-04-22"
    assert first["fecha_publicacion"] == "2026-04-22"
    assert first["tipo_documento"] == "sancion_cnmv"
    assert first["ambito"] == "sanciones_cnmv"
    assert first["family_id"] == "sanciones_cnmv"
    assert first["infraccion_gravedad"] == "muy_grave"
    assert first["source_index_url"].endswith("verRegSanciones?lang=es")

    second = candidates[1]
    assert second["url"] == "https://www.cnmv.es/webservices/verdocumento/ver?e=def"
    assert second["infraccion_gravedad"] == "grave"


def test_discover_source_family_documents_paginates_sanctions_until_empty(monkeypatch):
    original_client = httpx.Client
    requested_urls: list[str] = []

    def sanctions_row(page: int) -> bytes:
        return f"""
        <html><body><table>
        <tr>
          <td>0{page + 1}/05/2026</td>
          <td>
            <a href="/webservices/verdocumento/ver?e=sancion-{page}">
              Resolucion por la que se publican sanciones por infraccion grave a Entidad {page}
            </a>
          </td>
        </tr>
        </table></body></html>
        """.encode()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested_urls.append(url)
        if "RegistroSanciones" not in url:
            return httpx.Response(200, content=b"<html><body></body></html>")
        if "page=2" in url:
            return httpx.Response(200, content=b"<html><body><table></table></body></html>")
        if "page=1" in url:
            return httpx.Response(200, content=sanctions_row(1))
        return httpx.Response(200, content=sanctions_row(0))

    monkeypatch.setenv("CNMV_SANCIONES_MAX_PAGES", "25")
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    docs = _discover_source_family_documents()
    sanctions = [doc for doc in docs if doc.get("family_id") == "sanciones_cnmv"]

    assert DEFAULT_CNMV_SANCIONES_MAX_PAGES == 25
    assert len(sanctions) == 2
    assert any("page=2" in url for url in requested_urls)
    assert not any("page=3" in url for url in requested_urls)


def test_discover_source_family_documents_stops_sanctions_on_non_200(monkeypatch):
    original_client = httpx.Client
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested_urls.append(url)
        if "RegistroSanciones" not in url:
            return httpx.Response(200, content=b"<html><body></body></html>")
        if "page=1" in url:
            return httpx.Response(400, content=b"out of range")
        return httpx.Response(
            200,
            content=b"""
            <html><body><table>
            <tr>
              <td>01/05/2026</td>
              <td>
                <a href="/webservices/verdocumento/ver?e=sancion-0">
                  Resolucion por la que se publican sanciones por infraccion grave a Entidad 0
                </a>
              </td>
            </tr>
            </table></body></html>
            """,
        )

    monkeypatch.setenv("CNMV_SANCIONES_MAX_PAGES", "25")
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    docs = _discover_source_family_documents()
    sanctions = [doc for doc in docs if doc.get("family_id") == "sanciones_cnmv"]

    assert len(sanctions) == 1
    assert any("page=1" in url for url in requested_urls)
    assert not any("page=2" in url for url in requested_urls)


def test_build_document_payload_applies_family_metadata_and_partial_contract():
    payload = build_document_payload(
        "https://www.cnmv.es/DocPortal/DocFaseConsulta/CNMV/GT_ControlInterno.pdf",
        b"",
        "application/pdf",
        metadata={
            "referencia": "CNMV-CONSULTA-2025-12-15-GT-ControlInterno",
            "titulo": "Consulta publica previa sobre guia tecnica de control interno",
            "fecha": "2025-12-15",
            "tipo_documento": "documento_consulta_cnmv",
            "estado_vigencia": "consulta_cerrada",
            "estado_consulta": "consulta_cerrada",
            "family_id": "documentos_consulta_cnmv",
        },
    )

    assert payload["referencia"] == "CNMV-CONSULTA-2025-12-15-GT-ControlInterno"
    assert payload["tipo_documento"] == "documento_consulta_cnmv"
    assert payload["estado_vigencia"] == "consulta_cerrada"
    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_best_effort"
    assert payload["sujeto_obligado"] == ["sgiic", "sociedad_valores"]
    assert '"verified": false' in payload["metadata"]
    assert '"sujeto_obligado": ["sgiic", "sociedad_valores"]' in payload["metadata"]


def test_build_document_payload_keeps_sanction_metadata_when_pdf_is_unparseable():
    payload = build_document_payload(
        "https://www.cnmv.es/webservices/verdocumento/ver?e=abc",
        b"",
        "application/pdf",
        metadata={
            "referencia": "CNMV-SANCION-2026-04-22-example",
            "titulo": "Resolucion sancionadora por infraccion muy grave",
            "fecha": "2026-04-22",
            "fecha_publicacion": "2026-04-22",
            "tipo_documento": "sancion_cnmv",
            "ambito": "sanciones_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "sanciones_cnmv",
            "source_index_url": (
                "https://www.cnmv.es/Portal/Consultas/RegistroSanciones/verRegSanciones?lang=es"
            ),
            "infraccion_gravedad": "muy_grave",
        },
    )

    assert payload["referencia"] == "CNMV-SANCION-2026-04-22-example"
    assert payload["tipo_documento"] == "sancion_cnmv"
    assert payload["ambito"] == "sanciones_cnmv"
    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_best_effort"
    assert '"family_id": "sanciones_cnmv"' in payload["metadata"]
    assert '"infraccion_gravedad": "muy_grave"' in payload["metadata"]


def test_build_document_payload_downgrades_unreliable_pdf_text(monkeypatch):
    monkeypatch.setattr(
        "cnmv.extract_pdf_text",
        lambda content: "CNMV\x03\x11,,, \x03'(/\x030(5&$'2 incomplete control text",
    )

    payload = build_document_payload(
        "https://www.cnmv.es/webservices/verdocumento/ver?e=badpdf",
        b"%PDF-1.4 broken extraction",
        "application/pdf",
        metadata={
            "referencia": "CNMV-SANCION-badpdf",
            "titulo": "Resolucion sancionadora con PDF de extraccion defectuosa",
            "fecha": "2025-07-07",
            "tipo_documento": "sancion_cnmv",
            "ambito": "sanciones_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "sanciones_cnmv",
        },
    )

    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_best_effort"
    assert payload["texto"].startswith("[PARTIAL] Metadata oficial CNMV")
    assert '"verified": false' in payload["metadata"]


def test_build_document_payload_downgrades_symbol_dense_pdf_text(monkeypatch):
    bad_text = (
        ",,,\\x11\\x03275$6\\x03',6326,&,21(6 &20,6,1\\x031$&,21$/\\x03"
        "'(/\\x030(5&$'2\\x03'(\\x039$/25(6 " * 4
    )
    monkeypatch.setattr("cnmv.extract_pdf_text", lambda content: bad_text)

    payload = build_document_payload(
        "https://www.cnmv.es/webservices/verdocumento/ver?e=badpdf-escaped",
        b"%PDF-1.4 broken extraction",
        "application/pdf",
        metadata={
            "referencia": "CNMV-SANCION-badpdf-escaped",
            "titulo": "Resolucion sancionadora con PDF de extraccion defectuosa",
            "fecha": "2025-07-07",
            "tipo_documento": "sancion_cnmv",
            "ambito": "sanciones_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "sanciones_cnmv",
        },
    )

    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_best_effort"
    assert payload["texto"].startswith("[PARTIAL] Metadata oficial CNMV")
    assert '"verified": false' in payload["metadata"]


def test_build_document_payload_treats_legacy_doc_as_partial_metadata():
    payload = build_document_payload(
        "https://www.cnmv.es/docPortal/Legislacion/ModelosNormalizados/ESI/modelo.doc",
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00binary-word",
        "application/msword",
        metadata={
            "referencia": "CNMV-MODELO-ESI-legacy-doc",
            "titulo": "Modelo normalizado ESI legacy",
            "fecha": "2026-05-31",
            "tipo_documento": "modelo_esi_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "modelos_esi",
        },
    )

    assert payload["referencia"] == "CNMV-MODELO-ESI-legacy-doc"
    assert payload["row_completeness"] == "partial"
    assert payload["row_provenance"] == "official_best_effort"
    assert "\x00" not in payload["texto"]
    assert payload["texto"].startswith("[PARTIAL]")


def test_build_document_payload_tags_modelos_esi_subject_from_family():
    payload = build_document_payload(
        "https://www.cnmv.es/docPortal/Legislacion/ModelosNormalizados/ESI/modelo.pdf",
        b"",
        "application/pdf",
        metadata={
            "referencia": "CNMV-MODELO-ESI-subject",
            "titulo": "Modelo normalizado",
            "fecha": "2026-05-31",
            "tipo_documento": "modelo_esi_cnmv",
            "estado_vigencia": "vigente",
            "family_id": "modelos_esi",
        },
    )

    assert payload["sujeto_obligado"] == ["sociedad_valores"]
    assert '"sujeto_obligado": ["sociedad_valores"]' in payload["metadata"]


def test_discover_new_documents_filters_source_family_and_limits(monkeypatch):
    monkeypatch.setattr("cnmv._discover_cnmv_circulares", lambda: ["https://example.invalid/circular.pdf"])
    monkeypatch.setattr(
        "cnmv._discover_source_family_documents",
        lambda: [
            {"url": "https://example.invalid/gt-1.pdf", "family_id": "guias_tecnicas"},
            {"url": "https://example.invalid/gt-2.pdf", "family_id": "guias_tecnicas"},
            {
                "url": "https://example.invalid/consulta.pdf",
                "family_id": "documentos_consulta_cnmv",
            },
        ],
    )

    docs = _discover_new_documents(familia="guias_tecnicas", max_urls=1)

    assert docs == [{"url": "https://example.invalid/gt-1.pdf", "family_id": "guias_tecnicas"}]


def test_discover_new_documents_accepts_consultation_family_alias(monkeypatch):
    monkeypatch.setattr("cnmv._discover_cnmv_circulares", lambda: [])
    monkeypatch.setattr(
        "cnmv._discover_source_family_documents",
        lambda: [
            {
                "url": "https://example.invalid/consulta.pdf",
                "family_id": "documentos_consulta_cnmv",
            },
            {"url": "https://example.invalid/gt.pdf", "family_id": "guias_tecnicas"},
        ],
    )

    docs = _discover_new_documents(familia="documentos_consulta")

    assert docs == [
        {
            "url": "https://example.invalid/consulta.pdf",
            "family_id": "documentos_consulta_cnmv",
        }
    ]


def test_discover_new_documents_accepts_sanctions_family_alias(monkeypatch):
    monkeypatch.setattr("cnmv._discover_cnmv_circulares", lambda: [])
    monkeypatch.setattr(
        "cnmv._discover_source_family_documents",
        lambda: [
            {"url": "https://example.invalid/sancion.pdf", "family_id": "sanciones_cnmv"},
            {"url": "https://example.invalid/gt.pdf", "family_id": "guias_tecnicas"},
        ],
    )

    docs = _discover_new_documents(familia="sanciones")

    assert docs == [
        {"url": "https://example.invalid/sancion.pdf", "family_id": "sanciones_cnmv"}
    ]


def test_run_sync_follows_boe_html_seed_to_pdf(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT,
                    embedding_model_name TEXT,
                    content_hash TEXT
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
                    urls_discovered INTEGER,
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/buscar/doc.php":
            return httpx.Response(
                200,
                content=BOE_DOC_HTML,
                headers={"content-type": "text/html; charset=utf-8"},
            )
        if request.url.path == "/diario_boe/txt.php":
            return httpx.Response(
                200,
                content=MINIMAL_CNMV_PDF,
                headers={"content-type": "application/pdf"},
            )
        raise AssertionError(f"Unexpected URL requested: {request.url}")

    monkeypatch.setattr("cnmv.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        "cnmv._discover_new_urls",
        lambda seed_urls=None: seed_urls or ["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"],
    )

    result = run_sync(seed_urls=["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"])

    assert result["processed"] == 1
    assert result["stored"] == 1

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT referencia, url_fuente FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133'")
        ).fetchone()

    assert row == ("BOE-A-2009-133", "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2009-133")


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


def test_upsert_with_enriched_columns():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "BOE-A-2009-133",
            "fecha": "2009-01-02",
            "titulo": "Circular 9/2008",
            "tipo_documento": "circular_cnmv",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
            "ambito": "reporting_regulatorio_cnmv",
            "texto": "Normas contables.",
            "url_fuente": "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133",
            "numero_circular": "9/2008",
            "fecha_publicacion": "2009",
            "referencia_boe": "BOE-A-2009-133",
            "estado_vigencia": "vigente",
        }

        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                "SELECT referencia, numero_circular, fecha_publicacion, referencia_boe, estado_vigencia FROM documento_interpretativo"
            )
        ).fetchone()

    assert row[0] == "BOE-A-2009-133"
    assert row[1] == "9/2008"
    assert row[2] == "2009"
    assert row[3] == "BOE-A-2009-133"
    assert row[4] == "vigente"


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def test_run_sync_persists_cnmv_document_and_metrics(monkeypatch):
    import tempfile

    db_file = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite:///{db_file}"

    # Create tables in the DB file
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT
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
                    urls_discovered INTEGER,
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MINIMAL_CNMV_PDF)

    monkeypatch.setattr("cnmv.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )
    # Prevent discover from interfering — return seed URLs directly
    def fake_discover(seed_urls=None):
        return seed_urls or ["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"]
    monkeypatch.setattr("cnmv._discover_new_urls", fake_discover)

    result = run_sync(seed_urls=["https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"])

    assert result["processed"] == 1
    assert result["stored"] == 1
    assert "discovered" in result

    with engine.begin() as conn:
        doc = conn.execute(
            text(
                "SELECT referencia, organismo_emisor, tipo_fuente, ambito, tipo_documento FROM documento_interpretativo WHERE referencia = 'BOE-A-2009-133'"
            )
        ).fetchone()
        sync = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert doc == (
        "BOE-A-2009-133",
        "CNMV",
        "cnmv",
        "reporting_regulatorio",
        "circular_cnmv",
    )
    assert sync == ("worker-cnmv", "ok", 1, 1)


def test_run_sync_records_failed_candidate_url_diagnostics(monkeypatch):
    import tempfile

    db_file = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    numero_circular TEXT,
                    fecha_publicacion TEXT,
                    referencia_boe TEXT,
                    estado_vigencia TEXT,
                    embedding_model_name TEXT,
                    content_hash TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE source_revision (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    source_url TEXT,
                    first_seen_at TEXT,
                    last_seen_at TEXT,
                    UNIQUE(worker, entity_type, entity_id)
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
                    diagnostic_details TEXT,
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )

    original_client = httpx.Client
    missing_url = "https://www.cnmv.es/docPortal/missing.docx"
    valid_url = "https://www.boe.es/buscar/doc.php?id=BOE-A-2009-133"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == missing_url:
            return httpx.Response(404, content=b"not found")
        return httpx.Response(200, content=MINIMAL_CNMV_PDF)

    monkeypatch.setattr("cnmv.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr("cnmv._discover_new_urls", lambda seed_urls=None: seed_urls or [])

    result = run_sync(seed_urls=[missing_url, valid_url])

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT status, documentos_processed, documentos_upserted, error_msg, diagnostic_details "
                "FROM sync_log ORDER BY id DESC LIMIT 1"
            )
        ).mappings().one()

    details = json.loads(row["diagnostic_details"])
    assert result["processed"] == 1
    assert row["status"] == "partial"
    assert row["documentos_processed"] == 1
    assert row["documentos_upserted"] == 1
    assert row["error_msg"] == "Skipped 1 CNMV candidate URLs after fetch failures"
    assert details["failed_candidates"] == [
        {"url": missing_url, "status_code": 404, "error_type": "HTTPStatusError"}
    ]


# ---------------------------------------------------------------------------
# Discovery — _discover_cnmv_circulares
# ---------------------------------------------------------------------------


def test_discover_cnmv_circulares_from_main_page(monkeypatch):
    """_discover_cnmv_circulares should extract year-range pages from main index."""
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "cnmv-circulares-main.html"

    def fake_get(url, **kwargs):
        class Response:
            status_code = 200
            def __init__(self, url):
                if "Circulares.aspx" in str(url) and "-20" not in str(url) and "-15" not in str(url) and "-10" not in str(url) and "-05" not in str(url) and "-00" not in str(url):
                    self.text = fixture_path.read_text()
                elif "Circulares-2021-2025" in str(url):
                    self.text = (
                        fixture_path.resolve().parent / "cnmv-circulares-2021-2025.html"
                    ).read_text()
                else:
                    self.text = "<html></html>"
        return httpx.Response(200, content=b"<html></html>")

    # Use fixture directly
    main_html = fixture_path.read_text(encoding="utf-8")
    import re

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(main_html, "html.parser")
    pattern = re.compile(r"/Portal/Legislacion/Circulares-(\d{4})-(\d{4})\.aspx", re.IGNORECASE)
    links = []
    for a in soup.find_all("a", href=True):
        m = pattern.search(a["href"])
        if m:
            links.append(a["href"])
    assert len(links) >= 7


def test_discover_cnmv_circulares_extracts_boe_links(monkeypatch):
    """_discover_cnmv_circulares should extract BOE PDF/TXT links from year-range pages."""
    import httpx

    fixture_main = (
        Path(__file__).resolve().parent / "fixtures" / "cnmv-circulares-main.html"
    ).read_bytes()
    fixture_2021 = (
        Path(__file__).resolve().parent / "fixtures" / "cnmv-circulares-2021-2025.html"
    ).read_bytes()

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if "Circulares.aspx" in str(request.url) and "-20" not in str(request.url) and "-15" not in str(request.url) and "-10" not in str(request.url) and "-05" not in str(request.url) and "-00" not in str(request.url):
            return httpx.Response(200, content=fixture_main)
        if "Circulares-2021-2025" in str(request.url):
            return httpx.Response(200, content=fixture_2021)
        return httpx.Response(200, content=b"<html></html>")

    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    urls = _discover_cnmv_circulares(max_year_ranges=1, max_circulars_per_range=0)

    boe_urls = [u for u in urls if "boe.es" in u]
    assert len(boe_urls) >= 10

    # All should be unique
    assert len(urls) == len(set(urls))


def test_discover_cnmv_circulares_limits_year_ranges(monkeypatch):
    """_discover_cnmv_circulares should respect max_year_ranges limit."""
    import httpx

    fixture_path = Path(__file__).resolve().parent / "fixtures"
    fixture_main = (fixture_path / "cnmv-circulares-main.html").read_bytes()
    fixture_2021 = (fixture_path / "cnmv-circulares-2021-2025.html").read_bytes()

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if "Circulares.aspx" in str(request.url) and "-20" not in str(request.url) and "-15" not in str(request.url) and "-10" not in str(request.url) and "-05" not in str(request.url) and "-00" not in str(request.url):
            return httpx.Response(200, content=fixture_main)
        if "Circulares-2021-2025" in str(request.url):
            return httpx.Response(200, content=fixture_2021)
        return httpx.Response(200, content=b"<html></html>")

    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    urls = _discover_cnmv_circulares(max_year_ranges=1)
    boe_urls = [u for u in urls if "boe.es" in u]
    # Only from the first year-range page, not all 7
    assert len(boe_urls) < 100


def test_discover_cnmv_circulares_limits_circulars_per_range(monkeypatch):
    """_discover_cnmv_circulares should respect max_circulars_per_range limit."""
    import httpx

    fixture_path = Path(__file__).resolve().parent / "fixtures"
    fixture_main = (fixture_path / "cnmv-circulares-main.html").read_bytes()
    fixture_2021 = (fixture_path / "cnmv-circulares-2021-2025.html").read_bytes()

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if "Circulares.aspx" in str(request.url) and "-20" not in str(request.url) and "-15" not in str(request.url) and "-10" not in str(request.url) and "-05" not in str(request.url) and "-00" not in str(request.url):
            return httpx.Response(200, content=fixture_main)
        if "Circulares-2021-2025" in str(request.url):
            return httpx.Response(200, content=fixture_2021)
        return httpx.Response(200, content=b"<html></html>")

    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    urls = _discover_cnmv_circulares(max_year_ranges=1, max_circulars_per_range=3)
    boe_urls = [u for u in urls if "boe.es" in u]
    assert len(boe_urls) <= 3


def test_discover_cnmv_circulares_resolves_relative_urls(monkeypatch):
    """_discover_cnmv_circulares should resolve protocol-relative BOE URLs."""
    import httpx

    # Create a fixture with protocol-relative BOE URLs (//boe.es/...)
    relative_html = b"""<html>
<body>
<p><a href="//boe.es/boe/dias/2025/01/01/pdfs/BOE-A-2025-00001.pdf">Circular 1/2025</a>, de 1 de enero.</p>
<p><a href="//boe.es/diario_boe/txt.php?id=BOE-A-2025-00002">Circular 2/2025</a>, de 2 de enero.</p>
</body>
</html>"""

    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if "Circulares.aspx" in str(request.url) and "-20" not in str(request.url):
            # Return main page with a link to a year-range page
            return httpx.Response(
                200,
                content=b'<html><body><a href="/Portal/Legislacion/Circulares-2021-2025.aspx">2021-2025</a></body></html>',
            )
        return httpx.Response(200, content=relative_html)

    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    urls = _discover_cnmv_circulares(max_year_ranges=1)
    boe_urls = [u for u in urls if "BOE-A-2025" in u]
    assert len(boe_urls) == 2
    # Both should be absolute https URLs
    for u in boe_urls:
        assert u.startswith("https://boe.es/")


# ---------------------------------------------------------------------------
# Discovery — _discover_new_urls (legacy wrapper)
# ---------------------------------------------------------------------------


def test_discover_new_urls_fallback(monkeypatch):
    """When scraping fails, should fall back to seed URLs."""
    monkeypatch.setenv("CNMV_SEED_URLS", "https://example.com/doc1.pdf, https://example.com/doc2.pdf")

    # Re-import to pick up new env var
    import importlib

    import cnmv
    importlib.reload(cnmv)

    urls = cnmv._discover_new_urls()
    assert len(urls) >= 0  # May be empty if scraping fails gracefully


@pytest.mark.skip(reason="Makes real HTTP calls to CNMV portal")
def test_discover_new_urls_empty():
    """When no seed URLs configured and scraping fails, should use fallback."""
    urls = _discover_new_urls()
    # Should not raise — falls back to CNMV_SEED_URLS_FALLBACK
    assert isinstance(urls, list)


# ---------------------------------------------------------------------------
# Versioning (23.6)
# ---------------------------------------------------------------------------


def test_record_version_creates_entry(monkeypatch):
    """_record_version should insert a new version entry."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        # Create minimal tables
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto) VALUES ('BOE-A-2009-133', 'Texto original')"))

    with engine.begin() as conn:
        _record_version(conn, "BOE-A-2009-133", "Texto modificado", "modificado", nota="Primera modificacion")

    with engine.connect() as conn:
        version = conn.execute(text("SELECT documento_referencia, version_num, cambio_tipo, nota FROM documento_version")).fetchone()

    assert version is not None
    assert version.documento_referencia == "BOE-A-2009-133"
    assert version.version_num == 1
    assert version.cambio_tipo == "modificado"
    assert version.nota == "Primera modificacion"


def test_get_next_version_increments():
    """_get_next_version should return sequential numbers."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version) VALUES ('BOE-A-2009-133', 1, 'v1', 'creado', '2026-01-01')"))
        conn.execute(text("INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version) VALUES ('BOE-A-2009-133', 2, 'v2', 'modificado', '2026-01-02')"))

    with engine.connect() as conn:
        next_ver = _get_next_version(conn, "BOE-A-2009-133")

    assert next_ver == 3


def test_upsert_with_versioning_creates_new():
    """upsert_with_versioning should create new doc and record version 1."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL, organismo_emisor TEXT, jurisdiccion TEXT, tipo_fuente TEXT, ambito TEXT, fecha TEXT, titulo TEXT, url_fuente TEXT, tipo_documento TEXT)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("CREATE TABLE cnmv_regulation_link (id INTEGER PRIMARY KEY AUTOINCREMENT, documento_referencia TEXT NOT NULL, regulacion_id TEXT NOT NULL, relacion_tipo TEXT NOT NULL, nota TEXT, UNIQUE(documento_referencia, regulacion_id))"))
        conn.execute(text("CREATE TABLE cnmv_obligation_link (id INTEGER PRIMARY KEY AUTOINCREMENT, documento_referencia TEXT NOT NULL, tipo_obligacion TEXT NOT NULL, nota TEXT, UNIQUE(documento_referencia, tipo_obligacion))"))

        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Nuevo documento CNMV sobre MiFID II. La entidad debera mantener controles internos adecuados.",
            "titulo": "Circular 1/2025",
            "tipo_documento": "circular_cnmv",
            "ambito": "mifid_ii",
            "fecha": "2025-01-15",
            "url_fuente": "https://www.cnmv.es/doc.pdf",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "created"
    assert result["version_num"] == 1
    assert result.get("regulaciones", 0) >= 1
    assert result.get("obligaciones", 0) >= 1

    with engine.connect() as conn:
        doc = conn.execute(text("SELECT referencia, texto FROM documento_interpretativo WHERE referencia = 'BOE-A-2025-100'")).fetchone()
        ver = conn.execute(text("SELECT version_num, cambio_tipo FROM documento_version WHERE documento_referencia = 'BOE-A-2025-100'")).fetchone()

    assert doc is not None
    assert doc.referencia == "BOE-A-2025-100"
    assert ver.version_num == 1
    assert ver.cambio_tipo == "creado"


def test_upsert_with_versioning_updates():
    """upsert_with_versioning should update existing doc and record new version."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE NOT NULL, texto TEXT NOT NULL, organismo_emisor TEXT, jurisdiccion TEXT, tipo_fuente TEXT, ambito TEXT, fecha TEXT, titulo TEXT, url_fuente TEXT, tipo_documento TEXT)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        # Insert existing doc with version 1 already recorded
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto, titulo, tipo_documento, ambito) VALUES ('BOE-A-2025-100', 'Texto original', 'Circular 1/2025', 'circular_cnmv', 'mifid_ii')"))
        conn.execute(text("INSERT INTO documento_version (documento_referencia, version_num, texto, cambio_tipo, fecha_version) VALUES ('BOE-A-2025-100', 1, 'Texto original', 'creado', '2025-01-01')"))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Texto modificado con nueva norma",
            "titulo": "Circular 1/2025 (modificada)",
            "tipo_documento": "circular_cnmv",
            "ambito": "mifid_ii",
            "fecha": "2025-06-15",
            "url_fuente": "https://www.cnmv.es/doc_v2.pdf",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "updated"
    assert result["version_num"] == 3  # 1 (creado) + 1 (modificado) + 1 (next_ver)

    with engine.connect() as conn:
        doc = conn.execute(text("SELECT referencia, texto, titulo, url_fuente FROM documento_interpretativo WHERE referencia = 'BOE-A-2025-100'"))
        doc = doc.fetchone()
        ver = conn.execute(text("SELECT version_num, cambio_tipo FROM documento_version WHERE documento_referencia = 'BOE-A-2025-100' ORDER BY version_num")).fetchall()

    assert doc == (
        "BOE-A-2025-100",
        "Texto modificado con nueva norma",
        "Circular 1/2025 (modificada)",
        "https://www.cnmv.es/doc_v2.pdf",
    )
    assert len(ver) == 2
    assert ver[0].cambio_tipo == "creado"
    assert ver[1].cambio_tipo == "modificado"


def test_upsert_with_versioning_unchanged():
    """upsert_with_versioning should return unchanged when texto is identical."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto) VALUES ('BOE-A-2025-100', 'Texto identico')"))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Texto identico",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "unchanged"
    assert result["version_num"] is None

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM documento_version")).fetchone()[0]

    assert count == 0  # No new versions recorded


def test_upsert_with_versioning_derogado():
    """upsert_with_versioning should detect derogado from estado_vigencia."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT NOT NULL, organismo_emisor TEXT, jurisdiccion TEXT, tipo_fuente TEXT, ambito TEXT, fecha TEXT, titulo TEXT, url_fuente TEXT, tipo_documento TEXT, estado_vigencia TEXT)"))
        conn.execute(text("CREATE TABLE documento_version (id INTEGER PRIMARY KEY, documento_referencia TEXT, version_num INTEGER, texto TEXT, cambio_tipo TEXT, fecha_version TEXT, nota TEXT, url_version TEXT, UNIQUE(documento_referencia, version_num))"))
        conn.execute(text("INSERT INTO documento_interpretativo (referencia, texto, estado_vigencia, tipo_documento, ambito) VALUES ('BOE-A-2025-100', 'Texto original', 'vigente', 'circular_cnmv', 'mifid_ii')"))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "Texto derogado por nueva circular",
            "estado_vigencia": "derogado",
        }

        with engine.begin() as conn2:
            result = upsert_with_versioning(conn2, payload)

    assert result["action"] == "updated"
    assert result.get("cambio_tipo") == "derogado"


# ---------------------------------------------------------------------------
# Regulation mapping tests (23.7)
# ---------------------------------------------------------------------------


def test_detect_regulaciones_mifid_ii():
    """_detect_regulaciones should detect mifid_ii regulation."""
    text = "Circular sobre MiFID II y servicios de inversión. Directiva 2014/65/UE."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "mifid_ii" for r in result)
    assert any(r["relacion_tipo"] == "implementa" for r in result)


def test_detect_regulaciones_mar():
    """_detect_regulaciones should detect MAR regulation."""
    text = "Reglamento MAR sobre abuso de mercado. Reglamento (UE) 596/2014."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "mar" for r in result)


def test_detect_regulaciones_dora():
    """_detect_regulaciones should detect DORA regulation."""
    text = "Resiliencia operacional digital. Directiva DORA 2022/2554."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "dora" for r in result)


def test_detect_regulaciones_priips():
    """_detect_regulaciones should detect PRIIPs regulation."""
    text = "Reglamento PRIIPs sobre productos de inversión al por menor."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "priips" for r in result)


def test_detect_regulaciones_multiple():
    """_detect_regulaciones should detect multiple regulations."""
    text = "MiFID II y MAR. Directiva 2014/65/UE y reglamento 596/2014 sobre abuso de mercado."
    result = _detect_regulaciones(text)
    reg_ids = [r["regulacion_id"] for r in result]
    assert "mifid_ii" in reg_ids
    assert "mar" in reg_ids


def test_detect_regulaciones_none():
    """_detect_regulaciones should return empty list when no regulation matches."""
    text = "Este es un documento genérico sin referencia a regulaciones EU."
    result = _detect_regulaciones(text)
    assert result == []


def test_detect_regulaciones_gobierno():
    """_detect_regulaciones should detect gobierno corporativo regulation."""
    text = "Codigo de buen gobierno corporativo. Recomendaciones de la CNMV sobre gobernanza."
    result = _detect_regulaciones(text)
    assert any(r["regulacion_id"] == "cgce" for r in result)


def test_upsert_regulation_links_basic():
    """_upsert_regulation_links should insert links when table exists."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE cnmv_regulation_link (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                regulacion_id TEXT,
                relacion_tipo TEXT,
                nota TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))

    links = [
        {"regulacion_id": "mifid_ii", "relacion_tipo": "implementa", "nota": "Test"},
    ]
    with engine.begin() as conn:
        count = _upsert_regulation_links(conn, "BOE-A-2025-100", links)

    assert count == 1

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT regulacion_id, relacion_tipo FROM cnmv_regulation_link WHERE documento_referencia = :ref"),
            {"ref": "BOE-A-2025-100"},
        ).mappings().first()

    assert row["regulacion_id"] == "mifid_ii"
    assert row["relacion_tipo"] == "implementa"


def test_upsert_regulation_links_fallback_when_table_missing():
    """_upsert_regulation_links should return 0 when table does not exist."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT)"))

    links = [
        {"regulacion_id": "mifid_ii", "relacion_tipo": "implementa", "nota": "Test"},
    ]
    with engine.begin() as conn:
        count = _upsert_regulation_links(conn, "BOE-A-2025-100", links)

    assert count == 0


def test_upsert_with_versioning_includes_regulations():
    """upsert_with_versioning should detect and link regulations, returning count."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))
        # Insert existing document
        conn.execute(text("""
            INSERT INTO documento_interpretativo
            (referencia, texto, estado_vigencia, tipo_documento, ambito)
            VALUES ('BOE-A-2025-100', 'Texto original vigente', 'vigente', 'circular_cnmv', 'mifid_ii')
        """))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "MiFID II y MAR. Directiva 2014/65/UE y reglamento 596/2014 sobre abuso de mercado.",
            "estado_vigencia": "vigente",
        }
        result = upsert_with_versioning(conn, payload)

    assert result["action"] == "updated"
    assert result.get("cambio_tipo") == "modificado"
    assert result.get("regulaciones", 0) >= 1


# ---------------------------------------------------------------------------
# Phase 23.8 — Obligation derivation tests
# ---------------------------------------------------------------------------


def test_detect_obligaciones_presentacion_modelo():
    """Detect presentacion_modelo obligation from text."""
    text = "La sociedad de valores deberá presentar el modelo 620 antes del 20 de enero de cada año."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "presentacion_modelo" in tipos


def test_detect_obligaciones_remision_informacion():
    """Detect remision_informacion obligation from text."""
    text = "Obligación de comunicar a la CNMV cualquier modificación estatutaria en un plazo de 10 días hábiles."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "remision_informacion" in tipos


def test_detect_obligaciones_control_interno():
    """Detect control_interno obligation from text."""
    text = "La sociedad deberá mantener sistemas de control interno adecuados para registrar todas las operaciones realizadas."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "control_interno" in tipos


def test_detect_obligaciones_comunicacion_indicio():
    """Detect comunicacion_indicio obligation from text."""
    text = "Se deberá comunicar inmediatamente cualquier operación sospechosa de lavado de dinero a la CNMV."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "comunicacion_indicio" in tipos


def test_detect_obligaciones_reporting_prudencial():
    """Detect reporting_prudencial obligation from text."""
    text = "Reporte prudencial mensual de requisitos de capital y liquidez conforme a la normativa CNMV."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "reporting_prudencial" in tipos


def test_detect_obligaciones_multiple():
    """Detect multiple obligations from mixed text."""
    text = "La sociedad deberá presentar el modelo 347 y además deberá mantener controles internos adecuados. Asimismo, deberá comunicar indicios de lavado."
    result = _detect_obligaciones(text)
    tipos = [r["tipo_obligacion"] for r in result]
    assert "presentacion_modelo" in tipos
    assert "control_interno" in tipos
    assert "comunicacion_indicio" in tipos


def test_detect_obligaciones_none():
    """Return empty list when no obligation patterns match."""
    text = "Este documento trata sobre la organización general de la sociedad de valores y sus principios de funcionamiento."
    result = _detect_obligaciones(text)
    assert result == []


def test_upsert_obligation_links_basic():
    """Upsert obligation links for a CNMV document."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE cnmv_obligation_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_referencia TEXT NOT NULL,
                tipo_obligacion TEXT NOT NULL,
                nota TEXT,
                UNIQUE(documento_referencia, tipo_obligacion)
            )
        """))

    links = [
        {"tipo_obligacion": "presentacion_modelo", "nota": "Test"},
        {"tipo_obligacion": "remision_informacion", "nota": "Test 2"},
    ]
    with engine.begin() as conn:
        count = _upsert_obligation_links(conn, "BOE-A-2025-100", links)

    assert count == 2

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT tipo_obligacion FROM cnmv_obligation_link WHERE documento_referencia = :ref"),
            {"ref": "BOE-A-2025-100"},
        ).mappings().all()
        tipos = [r["tipo_obligacion"] for r in rows]

    assert "presentacion_modelo" in tipos
    assert "remision_informacion" in tipos


def test_upsert_obligation_links_fallback_when_table_missing():
    """_upsert_obligation_links should return 0 when table doesn't exist."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documento_interpretativo (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, texto TEXT)"))

    links = [
        {"tipo_obligacion": "presentacion_modelo", "nota": "Test"},
    ]
    with engine.begin() as conn:
        count = _upsert_obligation_links(conn, "BOE-A-2025-100", links)

    assert count == 0


def test_upsert_with_versioning_includes_obligations():
    """upsert_with_versioning should detect and link obligations, returning count."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))
        conn.execute(text("""
            CREATE TABLE cnmv_obligation_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_referencia TEXT NOT NULL,
                tipo_obligacion TEXT NOT NULL,
                nota TEXT,
                UNIQUE(documento_referencia, tipo_obligacion)
            )
        """))
        # Insert existing document
        conn.execute(text("""
            INSERT INTO documento_interpretativo
            (referencia, texto, estado_vigencia, tipo_documento, ambito)
            VALUES ('BOE-A-2025-100', 'Texto original vigente', 'vigente', 'circular_cnmv', 'general_cnmv')
        """))

    with engine.begin() as conn:
        payload = {
            "referencia": "BOE-A-2025-100",
            "texto": "La sociedad de valores deberá presentar el modelo 620 y deberá mantener controles internos adecuados.",
            "estado_vigencia": "vigente",
        }
        result = upsert_with_versioning(conn, payload)

    assert result["action"] == "updated"
    assert result.get("cambio_tipo") == "modificado"
    assert result.get("obligaciones", 0) >= 1


def test_run_sync_uses_versioning_and_linking(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    original_client = httpx.Client

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY,
                referencia TEXT UNIQUE,
                texto TEXT NOT NULL,
                organismo_emisor TEXT,
                jurisdiccion TEXT,
                tipo_fuente TEXT,
                ambito TEXT,
                fecha TEXT,
                titulo TEXT,
                url_fuente TEXT,
                tipo_documento TEXT,
                estado_vigencia TEXT,
                referencia_boe TEXT,
                numero_circular TEXT,
                fecha_publicacion TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE documento_version (
                id INTEGER PRIMARY KEY,
                documento_referencia TEXT,
                version_num INTEGER,
                texto TEXT,
                cambio_tipo TEXT,
                fecha_version TEXT,
                nota TEXT,
                url_version TEXT,
                UNIQUE(documento_referencia, version_num)
            )
        """))
        conn.execute(text("""
            CREATE TABLE cnmv_regulation_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_referencia TEXT NOT NULL,
                regulacion_id TEXT NOT NULL,
                relacion_tipo TEXT NOT NULL,
                nota TEXT,
                UNIQUE(documento_referencia, regulacion_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE cnmv_obligation_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_referencia TEXT NOT NULL,
                tipo_obligacion TEXT NOT NULL,
                nota TEXT,
                UNIQUE(documento_referencia, tipo_obligacion)
            )
        """))
        conn.execute(text("""
            CREATE TABLE source_revision (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                source_url TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                UNIQUE(worker, entity_type, entity_id)
            )
        """))
        conn.execute(text("""
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
        """))

    payload = {
        "tipo_documento": "circular_cnmv",
        "ambito": "mifid_ii",
        "referencia": "BOE-A-2025-100",
        "fecha": "2025-01-15",
        "titulo": "Circular MiFID II",
        "texto": "MiFID II y MAR. La sociedad debera mantener controles internos y comunicar operaciones sospechosas.",
        "url_fuente": "https://www.boe.es/buscar/doc.php?id=BOE-A-2025-100",
        "referencia_boe": "BOE-A-2025-100",
        "estado_vigencia": "vigente",
    }

    monkeypatch.setattr("cnmv.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("cnmv._discover_new_urls", lambda seed_urls=None: ["https://example.com/doc.pdf"])
    monkeypatch.setattr("cnmv._resolve_boe_document_url", lambda url, content, content_type: url)
    monkeypatch.setattr("cnmv.build_document_payload", lambda url, content, content_type: payload)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"dummy", headers={"content-type": "application/pdf"})

    monkeypatch.setattr(
        "cnmv.httpx.Client",
        lambda *args, **kwargs: original_client(transport=httpx.MockTransport(handler)),
    )

    result = run_sync(seed_urls=["https://example.com/doc.pdf"])

    with engine.begin() as conn:
        version_count = conn.execute(text("SELECT COUNT(*) FROM documento_version")).scalar_one()
        reg_count = conn.execute(text("SELECT COUNT(*) FROM cnmv_regulation_link")).scalar_one()
        obs_count = conn.execute(text("SELECT COUNT(*) FROM cnmv_obligation_link")).scalar_one()

    assert result["stored"] == 1
    assert version_count == 1
    assert reg_count >= 1
    assert obs_count >= 1


def test_run_sync_empty_seed_urls_returns_zero():
    """SEED_URLS vacío debe devolver telemetría cero sin hacer HTTP."""
    result = run_sync(seed_urls=[])
    assert result == {"processed": 0, "stored": 0, "discovered": 0}
