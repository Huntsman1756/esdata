"""Tests for dedicated EUR-Lex market loaders."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eurlex_market import (
    MARKET_ACTS,
    DownloadedAct,
    _candidate_belongs_to_act,
    _extract_spanish_oj_expression_urls,
    _parse_official_oj_html,
)


def test_market_acts_include_emir():
    emir = MARKET_ACTS["32012R0648"]

    assert emir.tipo == "REGULATION"
    assert emir.fecha_publicacion == "2012-07-27"
    assert "EMIR" in emir.titulo


def test_market_acts_include_current_market_expansion_targets():
    expected = {
        "32024R0791": ("REGULATION", "2024-03-08", "MiFIR"),
        "32024L0790": ("DIRECTIVE", "2024-03-08", "MiFID"),
        "32014R0596": ("REGULATION", "2014-06-12", "MAR"),
        "32017R0587": ("REGULATION", "2017-03-31", "RTS 1"),
        "32017R0583": ("REGULATION", "2017-03-31", "RTS 2"),
    }

    for celex, (tipo, fecha_publicacion, title_marker) in expected.items():
        act = MARKET_ACTS[celex]
        assert act.tipo == tipo
        assert act.fecha_publicacion == fecha_publicacion
        assert title_marker in act.titulo


def test_candidate_belongs_to_requested_celex_only():
    assert _candidate_belongs_to_act(
        "http://publications.europa.eu/resource/consolidation/2022R0858%2F20220602_0000010.SPA.xhtml",
        "32022R0858",
    )
    assert not _candidate_belongs_to_act(
        "http://publications.europa.eu/resource/consolidation/2014R0909%2F20220622_0020010.SPA.xhtml",
        "32022R0858",
    )


def test_extract_spanish_oj_expression_url_from_celex_rdf():
    rdf_text = """
    <rdf:RDF
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:cdm="http://publications.europa.eu/ontology/cdm#">
      <rdf:Description rdf:about="http://publications.europa.eu/resource/celex/32022R0858">
        <cdm:work_has_expression rdf:resource="http://publications.europa.eu/resource/oj/JOL_2022_151_R_0001.SPA"/>
        <cdm:work_has_expression rdf:resource="http://publications.europa.eu/resource/oj/JOL_2022_151_R_0001.CES"/>
      </rdf:Description>
    </rdf:RDF>
    """

    assert _extract_spanish_oj_expression_urls(rdf_text) == [
        "http://publications.europa.eu/resource/oj/JOL_2022_151_R_0001.SPA"
    ]


def test_parse_official_oj_html_articles():
    html = """
    <html><body>
      <div class="eli-subdivision" id="art_1">
        <p class="oj-ti-art">Artículo 1</p>
        <div class="eli-title"><p class="oj-sti-art">Objeto</p></div>
        <p>Texto del primer artículo.</p>
      </div>
      <div class="eli-subdivision" id="art_2">
        <p class="oj-ti-art">Artículo 2</p>
        <div class="eli-title"><p class="oj-sti-art">Definiciones</p></div>
        <p>Texto del segundo artículo.</p>
      </div>
    </body></html>
    """
    download = DownloadedAct(
        act=MARKET_ACTS["32022R0858"],
        source_url="http://publications.europa.eu/resource/oj/JOL_2022_151_R_0001.SPA",
        source_hash="abc123",
        vigente_desde="2022-06-02",
        html=html,
    )

    articles = _parse_official_oj_html(download)

    assert [article["numero"] for article in articles] == ["1", "2"]
    assert articles[0]["titulo"] == "Objeto"
    assert articles[0]["texto"] == "Texto del primer artículo."
