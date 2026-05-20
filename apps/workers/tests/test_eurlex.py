"""Tests para worker EUR-Lex (Fase 35.9).

Cubre:
- _infer_tipo_y_numero
- _is_supported_block
- _eli_path
- _yyyymmdd_to_iso
- _parse_block_xml
- parse_index
- EURLEX_NORMAS (estructura y conteo)
"""

# ruff: noqa: I001

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, text

import eurlex
from eurlex import (
    _extract_consolidation_manifestation_url_from_celex_rdf,
    _extract_consolidation_manifestation_urls_from_celex_rdf,
    _extract_consolidation_item_url,
    _extract_consolidation_manifestation_url,
    _extract_consolidation_vigente_desde,
    _fetch_index_html_fallback,
    _infer_tipo_y_numero,
    _eli_path,
    _is_supported_block,
    _parse_block_xml,
    _parse_official_consolidation_html,
    _selected_seed_normas,
    _yyyymmdd_to_iso,
    fetch_block,
    fetch_index,
    log_sync,
    parse_index,
    update_eurlex_quality,
)


def test_infer_tipo_y_numero_articulo_accented():
    tipo, numero = _infer_tipo_y_numero("Artículo 1. Disposiciones generales")
    assert tipo == "articulo"
    assert numero == "1"


def test_infer_tipo_y_numero_articulo_unaccented():
    tipo, numero = _infer_tipo_y_numero("Articulo 5. Definiciones")
    assert tipo == "articulo"
    assert numero == "5"


def test_infer_tipo_y_numero_disposicion_adicional():
    tipo, numero = _infer_tipo_y_numero("Disposición adicional primera")
    assert tipo == "disposicion_adicional"
    assert numero == "primera"


def test_infer_tipo_y_numero_disposicion_transitoria():
    tipo, numero = _infer_tipo_y_numero("Disposición transitoria segunda")
    assert tipo == "disposicion_transitoria"
    assert numero == "segunda"


def test_infer_tipo_y_numero_disposicion_final():
    tipo, numero = _infer_tipo_y_numero("Disposición final tercera")
    assert tipo == "disposicion_final"
    assert numero == "tercera"


def test_infer_tipo_y_numero_disposicion_derogatoria():
    tipo, numero = _infer_tipo_y_numero("Disposición derogatoria única")
    assert tipo == "disposicion_derogatoria"
    assert numero == "única"


def test_infer_tipo_y_numero_seccion():
    tipo, numero = _infer_tipo_y_numero("Sección 2. Requisitos de autorización")
    assert tipo == "seccion"
    assert numero == "Sección 2. Requisitos de autorización"


def test_infer_tipo_y_numero_capitulo():
    tipo, numero = _infer_tipo_y_numero("Capítulo 3. Derechos de los inversores")
    assert tipo == "capitulo"
    assert numero == "Capítulo 3. Derechos de los inversores"


def test_infer_tipo_y_numero_otro():
    tipo, numero = _infer_tipo_y_numero("Prólogo")
    assert tipo == "otro"
    assert numero == "Prólogo"


def test_is_supported_block_articulo():
    assert _is_supported_block("Artículo 1. Disposiciones generales") is True
    assert _is_supported_block("Articulo 2. Definiciones") is True


def test_is_supported_block_disposicion():
    assert _is_supported_block("Disposición adicional primera") is True
    assert _is_supported_block("Disposición transitoria segunda") is True
    assert _is_supported_block("Disposición final tercera") is True
    assert _is_supported_block("Disposición derogatoria única") is True


def test_is_supported_block_seccion_capitulo():
    assert _is_supported_block("Sección 2. Requisitos") is True
    assert _is_supported_block("Capítulo 3. Derechos") is True


def test_is_supported_block_other():
    assert _is_supported_block("Índice") is False
    assert _is_supported_block("Prólogo") is False
    assert _is_supported_block("Anexo") is False


def test_eli_path_regulation():
    assert _eli_path("EUR-CELEX-32014R0909") == "reg/2014/909/oj"


def test_eli_path_directive():
    assert _eli_path("EUR-CELEX-32014L0065") == "dir/2014/65/oj"


def test_eli_path_decision():
    assert _eli_path("EUR-CELEX-32013D0048") == "dec/2013/48/oj"


def test_eli_path_invalid():
    assert _eli_path("INVALID") == "unknown/oj"


def test_yyyymmdd_to_iso():
    assert _yyyymmdd_to_iso("20140912") == "2014-09-12"
    assert _yyyymmdd_to_iso("20220125") == "2022-01-25"


def test_selected_seed_normas_filters_allowlist(monkeypatch):
    monkeypatch.setenv("EURLEX_ONLY_CELEX", "32014L0065")
    monkeypatch.delenv("EURLEX_CELEX_ALLOWLIST", raising=False)
    monkeypatch.delenv("EURLEX_MAX_CELEX_PER_RUN", raising=False)

    selected = _selected_seed_normas(eurlex.EURLEX_NORMAS)

    assert [item["boe_id"] for item in selected] == ["EUR-CELEX-32014L0065"]


def test_selected_seed_normas_applies_run_budget(monkeypatch):
    monkeypatch.delenv("EURLEX_ONLY_CELEX", raising=False)
    monkeypatch.delenv("EURLEX_CELEX_ALLOWLIST", raising=False)
    monkeypatch.setenv("EURLEX_MAX_CELEX_PER_RUN", "2")

    selected = _selected_seed_normas(eurlex.EURLEX_NORMAS)

    assert len(selected) == 2
    assert selected == eurlex.EURLEX_NORMAS[:2]


def test_update_eurlex_quality_records_parity_counters():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE,
                    tipo_fuente TEXT,
                    articles_expected INTEGER,
                    articles_parsed INTEGER,
                    quality_status TEXT,
                    quality_checked_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    norma_id INTEGER,
                    numero TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER,
                    texto TEXT,
                    vigente_hasta TEXT
                )
                """
            )
        )
        conn.execute(text("INSERT INTO norma (codigo, tipo_fuente) VALUES ('MIFID2_2014_65', 'eurlex')"))
        conn.execute(text("INSERT INTO articulo (norma_id, numero) VALUES (1, '1'), (1, '2')"))
        conn.execute(
            text(
                """
                INSERT INTO version_articulo (articulo_id, texto, vigente_hasta)
                VALUES (1, 'Texto oficial 1', NULL), (2, 'Texto oficial 2', NULL)
                """
            )
        )

        update_eurlex_quality(conn, "MIFID2_2014_65", expected=2)

        row = conn.execute(
            text(
                """
                SELECT articles_expected, articles_parsed, quality_status, quality_checked_at
                FROM norma WHERE codigo='MIFID2_2014_65'
                """
            )
        ).one()
        assert row[0] == 2
        assert row[1] == 2
        assert row[2] == "article_text_available"
        assert row[3] is not None


def test_update_eurlex_quality_reconciles_official_empty_blocks():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE,
                    tipo_fuente TEXT,
                    articles_expected INTEGER,
                    articles_parsed INTEGER,
                    articles_empty_official INTEGER,
                    quality_status TEXT,
                    quality_checked_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    norma_id INTEGER,
                    numero TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER,
                    texto TEXT,
                    vigente_hasta TEXT
                )
                """
            )
        )
        conn.execute(text("INSERT INTO norma (codigo, tipo_fuente) VALUES ('MIFID2_2014_65', 'eurlex')"))
        conn.execute(text("INSERT INTO articulo (norma_id, numero) VALUES (1, '95'), (1, '95 bis')"))
        conn.execute(
            text(
                """
                INSERT INTO version_articulo (articulo_id, texto, vigente_hasta)
                VALUES (1, 'Texto oficial 95', NULL), (2, '', NULL)
                """
            )
        )

        update_eurlex_quality(conn, "MIFID2_2014_65", expected=2, empty_official=1)

        row = conn.execute(
            text(
                """
                SELECT articles_expected, articles_parsed, articles_empty_official, quality_status
                FROM norma WHERE codigo='MIFID2_2014_65'
                """
            )
        ).one()
        assert row[0] == 2
        assert row[1] == 1
        assert row[2] == 1
        assert row[3] == "article_text_available"


def test_parse_index_basic():
    payload = {
        "data": [
            {
                "bloque": [
                    {"id": "block-001", "titulo": "Artículo 1. Disposiciones generales", "fecha_actualizacion": ""},
                    {"id": "block-002", "titulo": "Artículo 2. Definiciones", "fecha_actualizacion": ""},
                    {"id": "block-003", "titulo": "", "fecha_actualizacion": ""},  # sin titulo -> skip
                ]
            }
        ]
    }
    result = parse_index(payload)
    assert len(result) == 2
    assert result[0]["id"] == "block-001"
    assert result[0]["titulo"] == "Artículo 1. Disposiciones generales"
    assert result[1]["id"] == "block-002"


def test_parse_index_empty():
    result = parse_index({"data": []})
    assert result == []


def test_parse_index_no_data_key():
    result = parse_index({})
    assert result == []


def test_parse_index_no_bloque_key():
    result = parse_index({"data": [{}]})
    assert result == []


def test_fetch_index_html_fallback_handles_html_entities():
    class FakeResponse:
        status_code = 200
        text = """
        <html>
          <body>
            <h2>Artículo 1&nbsp;Objeto</h2>
            <h3>Capítulo I&nbsp;Disposiciones generales</h3>
          </body>
        </html>
        """

    class FakeClient:
        def get(self, url, headers=None, timeout=None):
            return FakeResponse()

    result = _fetch_index_html_fallback(FakeClient(), "32014R0909")

    assert [item["titulo"] for item in result] == [
        "Artículo 1 Objeto",
        "Capítulo I Disposiciones generales",
    ]


def test_extract_consolidation_manifestation_url_prefers_revisioned_xhtml():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <NOTICE>
      <RESOURCE_LEGAL_BASIS_FOR_ACT_CONSOLIDATED>
        <EMBEDDED_NOTICE>
          <EXPRESSION>
            <EXPRESSION_MANIFESTED_BY_MANIFESTATION>
              <SAMEAS><URI><VALUE>http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323.SPA.xhtml</VALUE></URI></SAMEAS>
            </EXPRESSION_MANIFESTED_BY_MANIFESTATION>
            <EXPRESSION_MANIFESTED_BY_MANIFESTATION>
              <SAMEAS><URI><VALUE>http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323_0100010.SPA.xhtml</VALUE></URI></SAMEAS>
            </EXPRESSION_MANIFESTED_BY_MANIFESTATION>
          </EXPRESSION>
        </EMBEDDED_NOTICE>
      </RESOURCE_LEGAL_BASIS_FOR_ACT_CONSOLIDATED>
    </NOTICE>
    """

    assert _extract_consolidation_manifestation_url(xml_text) == (
        "http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323_0100010.SPA.xhtml"
    )


def test_extract_consolidation_item_url_from_rdf():
    rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323.SPA.xhtml.CL2014L0065ES0100010.0001.html"/>
      </rdf:Description>
    </rdf:RDF>
    """

    assert _extract_consolidation_item_url(rdf_text) == (
        "http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323.SPA.xhtml.CL2014L0065ES0100010.0001.html"
    )


def test_extract_consolidation_manifestation_url_from_celex_rdf():
    rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/eli/dir/2024/1760/2026-03-18"/>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2024L1760%2F20260318_0020020"/>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/celex/02024L1760-20260318"/>
      </rdf:Description>
    </rdf:RDF>
    """

    assert _extract_consolidation_manifestation_url_from_celex_rdf(rdf_text) == (
        "http://publications.europa.eu/resource/consolidation/2024L1760%2F20260318_0020020.SPA.xhtml"
    )


def test_extract_consolidation_manifestation_urls_from_celex_rdf_sorts_revisioned_first():
    rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014R1286%2F20141229"/>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014R1286%2F20161224_0010040"/>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014R1286%2F20141229_0000010"/>
      </rdf:Description>
    </rdf:RDF>
    """

    assert _extract_consolidation_manifestation_urls_from_celex_rdf(rdf_text) == [
        "http://publications.europa.eu/resource/consolidation/2014R1286%2F20161224_0010040.SPA.xhtml",
        "http://publications.europa.eu/resource/consolidation/2014R1286%2F20141229_0000010.SPA.xhtml",
        "http://publications.europa.eu/resource/consolidation/2014R1286%2F20141229.SPA.xhtml",
    ]


def test_extract_consolidation_vigente_desde_from_manifestation_url():
    assert _extract_consolidation_vigente_desde(
        "http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323_0100010.SPA.xhtml"
    ) == "2023-03-23"


def test_parse_official_consolidation_html_extracts_article_blocks():
    html_text = """
    <html>
      <body>
        <p class="title-article-norm">Artículo 1</p>
        <p class="stitle-article-norm">Ámbito de aplicación</p>
        <div class="norm"><span>1.</span><div>La presente Directiva se aplicará.</div></div>
        <p class="title-article-norm">Artículo 2</p>
        <p class="stitle-article-norm">Excepciones</p>
        <div class="norm"><span>1.</span><div>La presente Directiva no se aplicará a:</div></div>
      </body>
    </html>
    """

    blocks = _parse_official_consolidation_html("32014L0065", html_text)

    assert [block.titulo for block in blocks] == ["Artículo 1", "Artículo 2"]
    assert blocks[0].texto == "Ámbito de aplicación\n1. La presente Directiva se aplicará."
    assert blocks[1].texto == "Excepciones\n1. La presente Directiva no se aplicará a:"


def test_parse_official_consolidation_html_sets_vigente_desde():
    html_text = """
    <html>
      <body>
        <p class="title-article-norm">Artículo 1</p>
        <div class="norm">Texto oficial.</div>
      </body>
    </html>
    """

    blocks = _parse_official_consolidation_html("32014L0065", html_text, vigente_desde="2023-03-23")

    assert blocks[0].vigente_desde == "2023-03-23"


def test_fetch_index_uses_official_notice_and_consolidation_fallback():
    eurlex._OFFICIAL_CONSOLIDATION_CACHE.clear()

    notice_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <NOTICE>
      <RESOURCE_LEGAL_BASIS_FOR_ACT_CONSOLIDATED>
        <EMBEDDED_NOTICE>
          <EXPRESSION>
            <EXPRESSION_MANIFESTED_BY_MANIFESTATION>
              <SAMEAS><URI><VALUE>http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323_0100010.SPA.xhtml</VALUE></URI></SAMEAS>
            </EXPRESSION_MANIFESTED_BY_MANIFESTATION>
          </EXPRESSION>
        </EMBEDDED_NOTICE>
      </RESOURCE_LEGAL_BASIS_FOR_ACT_CONSOLIDATED>
    </NOTICE>
    """
    rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014L0065%2F20230323.SPA.xhtml.CL2014L0065ES0100010.0001.html"/>
      </rdf:Description>
    </rdf:RDF>
    """
    html_text = """
    <html>
      <body>
        <p class="title-article-norm">Artículo 1</p>
        <p class="stitle-article-norm">Ámbito de aplicación</p>
        <div class="norm"><span>1.</span><div>La presente Directiva se aplicará.</div></div>
      </body>
    </html>
    """

    client = _build_official_fallback_client(notice_xml, rdf_text, html_text)
    result = fetch_index(client, "32014L0065")

    assert result == [
        {
            "id": "official:32014L0065:0",
            "titulo": "Artículo 1",
            "fecha_actualizacion": "",
        }
    ]
    assert any("legal-content/ES/TXT/XML" in url for url in client.calls)
    assert any("/resource/consolidation/" in url for url in client.calls)


def test_fetch_index_uses_celex_rdf_when_notice_xml_is_202_empty():
    eurlex._OFFICIAL_CONSOLIDATION_CACHE.clear()

    celex_rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2024L1760%2F20260318_0020020"/>
      </rdf:Description>
    </rdf:RDF>
    """
    manifestation_rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2024L1760%2F20260318.SPA.xhtml.CL2024L1760ES0020020.0001.html"/>
      </rdf:Description>
    </rdf:RDF>
    """
    html_text = """
    <html>
      <body>
        <p class="title-article-norm">Artículo 1</p>
        <div class="norm">Texto oficial.</div>
      </body>
    </html>
    """

    client = _build_celex_rdf_fallback_client(celex_rdf_text, manifestation_rdf_text, html_text)
    result = fetch_index(client, "32024L1760")

    assert result == [
        {
            "id": "official:32024L1760:0",
            "titulo": "Artículo 1",
            "fecha_actualizacion": "",
        }
    ]
    assert any("/resource/celex/32024L1760" in url for url in client.calls)
    assert any("/resource/consolidation/2024L1760%2F20260318_0020020.SPA.xhtml" in url for url in client.calls)


def test_fetch_index_tries_multiple_celex_rdf_manifestation_candidates():
    eurlex._OFFICIAL_CONSOLIDATION_CACHE.clear()

    celex_rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014R1286%2F20240109_0040020"/>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014R1286%2F20161224_0010040"/>
      </rdf:Description>
    </rdf:RDF>
    """
    manifestation_rdf_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
      <rdf:Description>
        <owl:sameAs rdf:resource="http://publications.europa.eu/resource/consolidation/2014R1286%2F20161224.SPA.xhtml.CL2014R1286ES0010040.0001.html"/>
      </rdf:Description>
    </rdf:RDF>
    """
    html_text = """
    <html>
      <body>
        <p class="title-article-norm">Artículo 1</p>
        <div class="norm">Texto oficial.</div>
      </body>
    </html>
    """

    client = _build_multi_candidate_celex_rdf_client(celex_rdf_text, manifestation_rdf_text, html_text)
    result = fetch_index(client, "32014R1286")

    assert result == [
        {
            "id": "official:32014R1286:0",
            "titulo": "Artículo 1",
            "fecha_actualizacion": "",
        }
    ]
    assert any(url.endswith("20240109_0040020.SPA.xhtml") for url in client.calls)
    assert any(url.endswith("20161224_0010040.SPA.xhtml") for url in client.calls)


def test_fetch_block_reads_cached_official_consolidation_block():
    eurlex._OFFICIAL_CONSOLIDATION_CACHE.clear()
    eurlex._OFFICIAL_CONSOLIDATION_CACHE["32014L0065"] = [
        eurlex.BloqueTexto(
            bloque_id="official:32014L0065:0",
            tipo_bloque="official_consolidation",
            numero="1",
            titulo="Artículo 1",
            tipo_articulo="articulo",
            texto="Texto oficial",
            vigente_desde="",
        )
    ]

    bloque = fetch_block(object(), "official:32014L0065:0")

    assert bloque.titulo == "Artículo 1"
    assert bloque.texto == "Texto oficial"


class _FakeOfficialFallbackResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return {"data": []}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("boom")


def _get_official_fallback_response(url: str, notice_xml: str, rdf_text: str, html_text: str):
    if "rest.tx.legal-acts-index" in url:
        return _FakeOfficialFallbackResponse("{}")
    if "legal-content/ES/TXT/XML" in url:
        return _FakeOfficialFallbackResponse(notice_xml)
    if url.endswith(".SPA.xhtml"):
        return _FakeOfficialFallbackResponse(rdf_text)
    if url.endswith(".html"):
        return _FakeOfficialFallbackResponse(html_text)
    raise AssertionError(url)


def _build_official_fallback_client(notice_xml: str, rdf_text: str, html_text: str):
    class FakeClient:
        def __init__(self):
            self.calls = []

        def get(self, url, headers=None, timeout=None, follow_redirects=None):
            self.calls.append(url)
            return _get_official_fallback_response(url, notice_xml, rdf_text, html_text)

    return FakeClient()


def _build_celex_rdf_fallback_client(celex_rdf_text: str, manifestation_rdf_text: str, html_text: str):
    class FakeClient:
        def __init__(self):
            self.calls = []

        def get(self, url, headers=None, timeout=None, follow_redirects=None):
            self.calls.append(url)
            if "rest.tx.legal-acts-index" in url:
                return _FakeOfficialFallbackResponse("{}", status_code=202)
            if "legal-content/ES/TXT/XML" in url:
                return _FakeOfficialFallbackResponse("", status_code=202)
            if "/resource/celex/" in url:
                return _FakeOfficialFallbackResponse(celex_rdf_text)
            if url.endswith(".SPA.xhtml"):
                return _FakeOfficialFallbackResponse(manifestation_rdf_text)
            if url.endswith(".html"):
                return _FakeOfficialFallbackResponse(html_text)
            raise AssertionError(url)

    return FakeClient()


def _build_multi_candidate_celex_rdf_client(celex_rdf_text: str, manifestation_rdf_text: str, html_text: str):
    class FakeClient:
        def __init__(self):
            self.calls = []

        def get(self, url, headers=None, timeout=None, follow_redirects=None):
            self.calls.append(url)
            if "rest.tx.legal-acts-index" in url:
                return _FakeOfficialFallbackResponse("{}", status_code=202)
            if "legal-content/ES/TXT/XML" in url:
                return _FakeOfficialFallbackResponse("", status_code=202)
            if "/resource/celex/" in url:
                return _FakeOfficialFallbackResponse(celex_rdf_text)
            if url.endswith("20240109_0040020.SPA.xhtml"):
                return _FakeOfficialFallbackResponse("", status_code=404)
            if url.endswith("20161224_0010040.SPA.xhtml"):
                return _FakeOfficialFallbackResponse(manifestation_rdf_text)
            if url.endswith(".html"):
                return _FakeOfficialFallbackResponse(html_text)
            raise AssertionError(url)

    return FakeClient()


def test_parse_index_block_xml():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <bloque titulo="Artículo 1. Disposiciones generales" tipo="articulo">
            <p>Los Estados miembros adoptarán las disposiciones necesarias.</p>
            <p>Las mismas entrarán en vigor el 1 de enero de 2025.</p>
        </bloque>
        <version fecha_vigencia="20240101"/>
    </documento>
    """
    bloque = _parse_block_xml("block-001", xml_text)
    assert bloque.bloque_id == "block-001"
    assert bloque.tipo_bloque == "articulo"
    assert bloque.numero == "1"
    assert bloque.titulo == "Artículo 1. Disposiciones generales"
    assert bloque.tipo_articulo == "articulo"
    assert "Los Estados miembros adoptarán las disposiciones necesarias." in bloque.texto
    assert "Las mismas entrarán en vigor" in bloque.texto
    assert bloque.vigente_desde == "2024-01-01"


def test_parse_index_block_xml_disposicion():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <bloque titulo="Disposición adicional primera. Referencia" tipo="disposicion">
            <p>Se hace referencia al anexo I.</p>
        </bloque>
        <version fecha_vigencia="20230601"/>
    </documento>
    """
    bloque = _parse_block_xml("block-002", xml_text)
    assert bloque.tipo_articulo == "disposicion_adicional"
    assert bloque.numero == "primera"
    assert "Se hace referencia al anexo I." in bloque.texto
    assert bloque.vigente_desde == "2023-06-01"


def test_parse_index_block_xml_invalid_no_bloque():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <version fecha_vigencia="20240101"/>
    </documento>
    """
    with pytest.raises(ValueError, match="Invalid EUR-Lex block payload"):
        _parse_block_xml("block-bad", xml_text)


def test_parse_index_block_xml_invalid_no_version():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <documento>
        <bloque titulo="Artículo 1" tipo="articulo">
            <p>Texto.</p>
        </bloque>
    </documento>
    """
    with pytest.raises(ValueError, match="Invalid EUR-Lex block payload"):
        _parse_block_xml("block-bad", xml_text)


def test_eurlex_normas_has_required_fields():
    """Verificar que cada entrada de EURLEX_NORMAS tiene los campos requeridos."""
    required = {"codigo", "boe_id", "tipo_documento", "titulo", "vigente_desde", "ambito"}
    for norma in eurlex.EURLEX_NORMAS:
        assert required.issubset(norma.keys()), f"Faltan campos en {norma.get('codigo', 'unknown')}"
        assert norma["boe_id"].startswith("EUR-CELEX-"), f"boe_id debe empezar con EUR-CELEX-: {norma['boe_id']}"


def test_eurlex_normas_count():
    """Verificar que tenemos una seed curada amplia sin entradas dudosas obvias."""
    assert len(eurlex.EURLEX_NORMAS) >= 28, f"Solo {len(eurlex.EURLEX_NORMAS)} CELEXs, se esperan >= 28"


def test_eurlex_normas_unique_codigos():
    """Verificar que los códigos son únicos."""
    codigos = [n["codigo"] for n in eurlex.EURLEX_NORMAS]
    assert len(codigos) == len(set(codigos)), f"Códigos duplicados encontrados: {len(codigos)} vs {len(set(codigos))}"


def test_eurlex_normas_boe_id_unique():
    """Verificar que los CELEXs son únicos."""
    celexs = [n["boe_id"] for n in eurlex.EURLEX_NORMAS]
    assert len(celexs) == len(set(celexs)), "CELEXs duplicados encontrados"


def test_eurlex_normas_uses_corrected_celex_for_known_skips():
    """Verificar que la seed curada usa los CELEX validados en la auditoria."""
    normas_by_codigo = {norma["codigo"]: norma for norma in eurlex.EURLEX_NORMAS}

    assert normas_by_codigo["MIFIR_2014_60"]["boe_id"] == "EUR-CELEX-32014R0600"
    assert normas_by_codigo["CRD_V_2019_2058"]["boe_id"] == "EUR-CELEX-32019L0878"
    assert normas_by_codigo["CRR_II_2019_2057"]["boe_id"] == "EUR-CELEX-32019R0876"
    assert normas_by_codigo["PSD2_2015_236"]["boe_id"] == "EUR-CELEX-32015L2366"
    assert normas_by_codigo["DAC6_2018_825"]["boe_id"] == "EUR-CELEX-32018L0822"
    assert normas_by_codigo["DAC7_2021_1689"]["boe_id"] == "EUR-CELEX-32021L0514"
    assert normas_by_codigo["PSD3_2024_884"]["boe_id"] == "EUR-CELEX-32024R0886"
    assert normas_by_codigo["EMIR_2012_648"]["boe_id"] == "EUR-CELEX-32012R0648"
    assert "contrapartida central" in normas_by_codigo["EMIR_2012_648"]["titulo"]


def test_eurlex_normas_excludes_dubious_seed_entries():
    """Verificar que la seed curada no conserva CELEX/titulos ya descartados."""
    codigos = {norma["codigo"] for norma in eurlex.EURLEX_NORMAS}

    assert "APM_2020_683" not in codigos
    assert "ESG_RATINGS_2023_2819" not in codigos


def test_eurlex_normas_types():
    """Verificar que solo hay directivas y reglamentos."""
    tipos = {n["tipo_documento"] for n in eurlex.EURLEX_NORMAS}
    assert tipos.issubset({"directiva", "reglamento"}), f"Tipos inesperados: {tipos}"


def test_eurlex_normas_amplitudes():
    """Verificar que los ambitos son razonables."""
    ambitos = {n["ambito"] for n in eurlex.EURLEX_NORMAS}
    # Deberia haber variedad de ambitos
    assert len(ambitos) >= 10, f"Solo {len(ambitos)} ambitos diferentes, se espera >= 10"


def test_eli_path_format():
    """Verificar que _eli_path genera paths válidos."""
    # Reglamentos
    assert _eli_path("EUR-CELEX-32014R0909") == "reg/2014/909/oj"
    assert _eli_path("EUR-CELEX-32017R1129") == "reg/2017/1129/oj"
    # Directivas
    assert _eli_path("EUR-CELEX-32014L0065") == "dir/2014/65/oj"
    assert _eli_path("EUR-CELEX-32011L0061") == "dir/2011/61/oj"
    # Decisiones
    assert _eli_path("EUR-CELEX-32013D0048") == "dec/2013/48/oj"


def test_log_sync_preserves_zero_errors_when_error_msg_is_summary():
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        log_sync(
            conn,
            "worker-eurlex",
            "ok",
            bloques=10,
            articulos=4,
            error_msg="summary: unchanged=6; no_index=2; fetch_errors=0",
            started_at="2026-05-03T13:20:00+00:00",
            errors=0,
        )
        row = conn.execute(text("SELECT status, error_msg, errors, rows_processed FROM sync_log")).mappings().one()

    assert row["status"] == "ok"
    assert row["error_msg"] == "summary: unchanged=6; no_index=2; fetch_errors=0"
    assert row["errors"] == 0
    assert row["rows_processed"] == 10


def test_log_sync_records_nonzero_errors_when_requested():
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        log_sync(
            conn,
            "worker-eurlex",
            "partial",
            bloques=5,
            articulos=3,
            error_msg="summary: unchanged=1; no_index=1; fetch_errors=2",
            started_at="2026-05-03T13:20:00+00:00",
            errors=2,
        )
        row = conn.execute(text("SELECT status, error_msg, errors, rows_processed FROM sync_log")).mappings().one()

    assert row["status"] == "partial"
    assert row["errors"] == 2
    assert row["rows_processed"] == 5


def test_upsert_norma_conflict_on_boe_id_idempotent():
    """A-04b: upsert_norma must handle conflicts on boe_id, not only codigo.

    When a norma was previously loaded with a different internal codigo
    (e.g. CELEX normalisation) the same boe_id must not trigger a
    unique violation.
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    titulo TEXT NOT NULL,
                    boe_id TEXT UNIQUE NOT NULL,
                    eli_uri TEXT,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    tipo_documento TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    estado_cobertura TEXT NOT NULL,
                    vigente_desde DATE NOT NULL
                )
                """
            )
        )

    with engine.begin() as conn:
        eurlex.upsert_norma(
            conn,
            {
                "codigo": "MIFID2_2014_65",
                "boe_id": "EUR-CELEX-32014L0065",
                "tipo_documento": "directiva",
                "titulo": "MiFID II original",
                "vigente_desde": "2014-07-17",
                "ambito": "mercados_financieros",
            },
            "2014-07-17",
        )

    with engine.begin() as conn:
        # Same boe_id but different codigo (CELEX normalised) — must not crash
        eurlex.upsert_norma(
            conn,
            {
                "codigo": "32014L0065",
                "boe_id": "EUR-CELEX-32014L0065",
                "tipo_documento": "directiva",
                "titulo": "MiFID II normalised",
                "vigente_desde": "2014-07-17",
                "ambito": "mercados_financieros",
            },
            "2014-07-17",
        )

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT codigo, titulo FROM norma WHERE boe_id = 'EUR-CELEX-32014L0065'")
        ).one()
        assert row[0] in ("MIFID2_2014_65", "32014L0065")
        assert row[1] == "MiFID II normalised"


def test_dead_letter_idempotent_on_duplicate():
    """A-04b: add_dead_letter must not crash on duplicate (worker_name, entity_id).

    The original SELECT-then-INSERT pattern was racy; the new ON CONFLICT
    upsert must be safe for concurrent or repeated calls.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dead_letter import add_dead_letter, get_dead_letters

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_dead_letter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_name TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    error_message TEXT,
                    error_traceback TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    first_failed_at TEXT,
                    last_failed_at TEXT,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    notes TEXT,
                    UNIQUE(worker_name, entity_id)
                )
                """
            )
        )

    r1 = add_dead_letter(engine, "worker-eurlex", "eurlex", "sync_norma", "duplicate key error")
    assert r1 == 1

    r2 = add_dead_letter(engine, "worker-eurlex", "eurlex", "sync_norma", "duplicate key error retry")
    assert r2 == 2

    letters = get_dead_letters(engine)
    assert len(letters) == 1
    assert letters[0]["retry_count"] == 2
    assert letters[0]["error_message"] == "duplicate key error retry"
