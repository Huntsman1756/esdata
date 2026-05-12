import boe_diario
from sqlalchemy import create_engine, text

BOE_B_XML = """<?xml version="1.0" encoding="UTF-8"?>
<documento fecha_actualizacion="20260511071559">
  <metadatos>
    <identificador>BOE-B-2026-15000</identificador>
    <departamento codigo="9546">JUZGADOS DE PRIMERA INSTANCIA E INSTRUCCION</departamento>
    <titulo>FIGUERES</titulo>
    <diario codigo="BOE">Boletin Oficial del Estado</diario>
    <fecha_publicacion>20260511</fecha_publicacion>
    <url_pdf>/boe/dias/2026/05/11/pdfs/BOE-B-2026-15000.pdf</url_pdf>
  </metadatos>
  <texto>
    <p class="parrafo">JUZGADO 1a INST E INSTRUCC. 6.- Anuncio de subasta judicial.</p>
    <p class="parrafo">Direccion electronica: https://subastas.boe.es/ds.php?id=SUB-JA-2016-26470</p>
  </texto>
</documento>
"""


def test_parse_boe_diario_xml_extracts_official_text_and_metadata():
    doc = boe_diario.parse_boe_diario_xml(
        BOE_B_XML,
        xml_url="https://www.boe.es/diario_boe/xml.php?id=BOE-B-2026-15000",
    )

    assert doc.referencia == "BOE-B-2026-15000"
    assert doc.fecha == "2026-05-11"
    assert doc.titulo == "FIGUERES"
    assert "Anuncio de subasta judicial" in doc.texto
    assert doc.url_fuente == "https://www.boe.es/diario_boe/xml.php?id=BOE-B-2026-15000"
    assert doc.pdf_url == "https://www.boe.es/boe/dias/2026/05/11/pdfs/BOE-B-2026-15000.pdf"
    assert doc.row_completeness == "complete"
    assert doc.row_provenance == "official_exact"
    assert doc.metadata["source_format"] == "boe_daily_xml"


def test_upsert_documento_interpretativo_is_idempotent_and_uses_separate_source():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT,
                    organismo_emisor TEXT,
                    jurisdiccion TEXT,
                    tipo_fuente TEXT,
                    ambito TEXT,
                    referencia TEXT UNIQUE,
                    fecha TEXT,
                    titulo TEXT,
                    texto TEXT,
                    url_fuente TEXT,
                    metadata TEXT,
                    row_completeness TEXT,
                    row_provenance TEXT
                )
                """
            )
        )
        doc = boe_diario.parse_boe_diario_xml(
            BOE_B_XML,
            xml_url="https://www.boe.es/diario_boe/xml.php?id=BOE-B-2026-15000",
        )

        boe_diario.upsert_documento_interpretativo(conn, doc)
        boe_diario.upsert_documento_interpretativo(conn, doc)

        row = conn.execute(
            text(
                """
                SELECT COUNT(*), tipo_fuente, organismo_emisor, row_completeness, row_provenance
                FROM documento_interpretativo
                WHERE referencia = 'BOE-B-2026-15000'
                GROUP BY tipo_fuente, organismo_emisor, row_completeness, row_provenance
                """
            )
        ).one()
        assert row == (1, "boe_diario", "BOE", "complete", "official_exact")
