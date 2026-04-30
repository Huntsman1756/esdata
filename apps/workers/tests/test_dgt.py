import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dgt import (
    build_search_payload,
    fetch_document_html,
    fetch_search_html,
    parse_document_html,
    parse_search_results,
    run_sync,
    start_session,
    upsert_documento_interpretativo,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_search_results_extracts_doc_id_and_summary():
    html = (FIXTURES / "V2274-22-search.html").read_text(encoding="utf-8")

    results = parse_search_results(html)

    assert len(results) == 1
    assert results[0]["doc_id"] == "46632"
    assert results[0]["referencia"] == "V2274-22"
    assert "Impuesto sobre el Valor Añadido" in results[0]["cuestion"]


def test_parse_document_html_extracts_core_fields():
    html = (FIXTURES / "V2274-22-document.html").read_text(encoding="utf-8")

    doc = parse_document_html(html)

    assert doc["referencia"] == "V2274-22"
    assert doc["organo"] == "SG de Impuestos sobre el Consumo"
    assert doc["fecha"] == "2022-10-27"
    assert doc["normativa"] == "Ley 37/1992 arts. 4, 5, 8, 11, 69 y 70"
    assert "Tributación en el Impuesto sobre el Valor Añadido" in doc["cuestion"]
    assert "tipo general del Impuesto del 21 por ciento" in doc["texto"]


def test_parse_document_html_detects_target_normas():
    html = (FIXTURES / "V2274-22-document.html").read_text(encoding="utf-8")

    doc = parse_document_html(html)

    assert doc["normas_objetivo"] == ["LIVA"]


def test_upsert_documento_interpretativo_is_idempotent_and_stores_dgt_fields():
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)

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
                    url_fuente TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "V2274-22",
            "fecha": "2022-10-27",
            "titulo": "Consulta DGT sobre NFTs e IVA",
            "texto": "Documento relacionado con la Ley del IVA.",
            "url_fuente": "https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2274-22",
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                """
                SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, COUNT(*)
                FROM documento_interpretativo
                GROUP BY referencia, tipo_documento, organismo_emisor, tipo_fuente
                """
            )
        ).fetchone()

    assert row == ("V2274-22", "consulta_vinculante", "DGT", "dgt", 1)


def test_parse_document_html_can_be_filtered_to_liva_and_lis_only():
    html = (FIXTURES / "V2274-22-document.html").read_text(encoding="utf-8")

    doc = parse_document_html(html)

    assert set(doc["normas_objetivo"]) <= {"LIVA", "LIS"}


def test_build_search_payload_for_num_consulta():
    payload = build_search_payload("V2274-22")

    assert payload == {
        "type2": "on",
        "NMCMP_1": "NUM-CONSULTA",
        "VLCMP_1": "V2274-22",
        "OPCMP_1": ".Y",
        "cmpOrder": "NUM-CONSULTA",
        "dirOrder": "0",
        "tab": "2",
        "page": "1",
        "auto": "true",
    }


def test_start_session_sets_cookie_and_ajax_headers():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/consultas/"
        return httpx.Response(
            200,
            text="<html></html>",
            headers={"set-cookie": "JSESSIONID=abc123; Path=/consultas; HttpOnly"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://petete.tributos.hacienda.gob.es",
    )

    start_session(client)

    assert client.cookies.get("JSESSIONID") == "abc123"
    assert client.headers["X-Requested-With"] == "XMLHttpRequest"
    assert (
        client.headers["Referer"]
        == "https://petete.tributos.hacienda.gob.es/consultas/"
    )


def test_fetch_search_and_document_html_use_ajax_flow():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/consultas/":
            return httpx.Response(
                200,
                text="<html></html>",
                headers={"set-cookie": "JSESSIONID=abc123; Path=/consultas; HttpOnly"},
            )
        if request.url.path == "/consultas/do/search":
            return httpx.Response(
                200,
                text=(FIXTURES / "V2274-22-search.html").read_text(encoding="utf-8"),
            )
        if request.url.path == "/consultas/do/document":
            assert request.headers["X-Requested-With"] == "XMLHttpRequest"
            return httpx.Response(
                200,
                text=(FIXTURES / "V2274-22-document.html").read_text(encoding="utf-8"),
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://petete.tributos.hacienda.gob.es",
    )

    start_session(client)
    search_html = fetch_search_html(client, "V2274-22")
    document_html = fetch_document_html(
        client, ".EN NUM-CONSULTA (V2274-22)", "NUM-CONSULTA|0", "46632"
    )

    assert "V2274-22" in search_html
    assert "Contestación completa" in document_html
    assert requests[1].url.path == "/consultas/do/search"
    assert requests[2].url.path == "/consultas/do/document"


def test_run_sync_persists_target_dgt_document(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    original_client = httpx.Client

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    titulo TEXT NOT NULL,
                    boe_id TEXT UNIQUE NOT NULL,
                    eli_uri TEXT UNIQUE,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    norma_id INTEGER NOT NULL,
                    numero TEXT NOT NULL,
                    titulo TEXT,
                    tipo TEXT NOT NULL,
                    UNIQUE (norma_id, numero)
                )
                """
            )
        )
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
                    url_fuente TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_articulo (
                    documento_id INTEGER NOT NULL,
                    articulo_id INTEGER NOT NULL,
                    metodo_enlace TEXT NOT NULL,
                    confianza_enlace REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, articulo_id)
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
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
                VALUES ('LIVA', 'Ley IVA', 'BOE-A-1992-28740', NULL, 'es', 'boe', 'fiscal', '1993-01-01')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '4', 'Hecho imponible', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    def build_search_html(referencia: str, doc_id: str) -> str:
        return f"""
        <table>
          <tr>
            <td id="doc_{doc_id}">
              <span class="NUM-CONSULTA">{referencia}</span>
              <span class="DESCRIPCION-HECHOS">Hechos del caso.</span>
              <span class="CUESTION-PLANTEADA"><i>Consulta sobre IVA.</i></span>
            </td>
          </tr>
        </table>
        """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/consultas/":
            return httpx.Response(
                200,
                text="<html></html>",
                headers={"set-cookie": "JSESSIONID=abc123; Path=/consultas; HttpOnly"},
            )
        if request.url.path == "/consultas/do/search":
            return httpx.Response(200, text=build_search_html("V2274-22", "46632"))
        if request.url.path == "/consultas/do/document":
            return httpx.Response(
                200,
                text=(FIXTURES / "V2274-22-document.html").read_text(encoding="utf-8"),
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(
        "dgt.SEED_URLS",
        ["https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2274-22"],
    )
    monkeypatch.setattr("dgt.DGT_DISCOVERY", False)
    monkeypatch.setattr("dgt.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "dgt.httpx.Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            base_url="https://petete.tributos.hacienda.gob.es",
        ),
    )
    monkeypatch.setattr("dgt.auto_link_doctrina", lambda conn: 1)
    monkeypatch.setattr("dgt.log_sync", lambda *args, **kwargs: None)

    result = run_sync()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT referencia, tipo_fuente, organismo_emisor FROM documento_interpretativo"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1, "discovered": 0}
    assert row == ("V2274-22", "dgt", "DGT")


def test_run_sync_skips_documents_outside_liva_and_lis(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    original_client = httpx.Client

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    titulo TEXT NOT NULL,
                    boe_id TEXT UNIQUE NOT NULL,
                    eli_uri TEXT UNIQUE,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    norma_id INTEGER NOT NULL,
                    numero TEXT NOT NULL,
                    titulo TEXT,
                    tipo TEXT NOT NULL,
                    UNIQUE (norma_id, numero)
                )
                """
            )
        )
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
                    url_fuente TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_articulo (
                    documento_id INTEGER NOT NULL,
                    articulo_id INTEGER NOT NULL,
                    metodo_enlace TEXT NOT NULL,
                    confianza_enlace REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, articulo_id)
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
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )

    search_html = """
    <table>
      <tr>
        <td id="doc_99999">
          <span class="NUM-CONSULTA">V0001-26</span>
          <span class="DESCRIPCION-HECHOS">Hechos del caso.</span>
          <span class="CUESTION-PLANTEADA"><i>Consulta sobre IRPF.</i></span>
        </td>
      </tr>
    </table>
    """

    non_target_document_html = """
    <table>
      <tr class="NUM-CONSULTA"><td class="value">V0001-26</td></tr>
      <tr class="ORGANO"><td class="value">SG de Impuestos Personales</td></tr>
      <tr class="FECHA-SALIDA"><td class="value">15/01/2026</td></tr>
      <tr class="NORMATIVA"><td class="value">Ley 35/2006 del IRPF</td></tr>
      <tr class="CUESTION-PLANTEADA"><td class="value">Rendimientos del trabajo.</td></tr>
      <tr class="CONTESTACION-COMPL"><td class="value">La consulta trata solo sobre IRPF.</td></tr>
    </table>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/consultas/":
            return httpx.Response(
                200,
                text="<html></html>",
                headers={"set-cookie": "JSESSIONID=abc123; Path=/consultas; HttpOnly"},
            )
        if request.url.path == "/consultas/do/search":
            return httpx.Response(200, text=search_html)
        if request.url.path == "/consultas/do/document":
            return httpx.Response(200, text=non_target_document_html)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(
        "dgt.SEED_URLS",
        ["https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0001-26"],
    )
    monkeypatch.setattr("dgt.DGT_DISCOVERY", False)
    monkeypatch.setattr("dgt.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "dgt.httpx.Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            base_url="https://petete.tributos.hacienda.gob.es",
        ),
    )
    monkeypatch.setattr("dgt.log_sync", lambda *args, **kwargs: None)

    result = run_sync()

    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM documento_interpretativo")
        ).scalar_one()
        link_count = conn.execute(
            text("SELECT COUNT(*) FROM documento_articulo")
        ).scalar_one()

    assert result == {"processed": 1, "stored": 0, "discovered": 0}
    assert count == 0
    assert link_count == 0


def test_dgt_run_once_flag_accepts_argparse():
    workers_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "dgt.py", "--help"],
        capture_output=True,
        text=True,
        cwd=workers_dir,
        env={**__import__("os").environ, "DATABASE_URL": "sqlite:///:memory:"},
    )
    assert result.returncode == 0
    assert "--run-once" in result.stdout
    assert "--interval" in result.stdout


def test_run_sync_uses_configurable_ssl_verification(monkeypatch):
    captured = {}

    def fake_client(*args, **kwargs):
        captured["verify"] = kwargs.get("verify")
        raise RuntimeError("stop after client init")

    class FakeConnection:
        def execute(self, *args, **kwargs):
            return None

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr("dgt.httpx.Client", fake_client)
    monkeypatch.setattr("dgt.create_engine", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr("dgt._ensure_sync_log_table", lambda conn: None)
    monkeypatch.setattr("dgt.log_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr("dgt.DGT_SSL_VERIFY", False)

    with pytest.raises(RuntimeError, match="stop after client init"):
        run_sync(seed_urls=[])

    assert captured["verify"] is False


def test_run_sync_uses_discovery_when_dgt_discovery_env_is_true(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    original_client = httpx.Client

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    titulo TEXT NOT NULL,
                    boe_id TEXT UNIQUE NOT NULL,
                    eli_uri TEXT UNIQUE,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    norma_id INTEGER NOT NULL,
                    numero TEXT NOT NULL,
                    titulo TEXT,
                    tipo TEXT NOT NULL,
                    UNIQUE (norma_id, numero)
                )
                """
            )
        )
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
                    url_fuente TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_articulo (
                    documento_id INTEGER NOT NULL,
                    articulo_id INTEGER NOT NULL,
                    metodo_enlace TEXT NOT NULL,
                    confianza_enlace REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, articulo_id)
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
                    rows_processed INTEGER,
                    errors INTEGER,
                    duration_ms INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
                VALUES ('LIVA', 'Ley IVA', 'BOE-A-1992-28740', NULL, 'es', 'boe', 'fiscal', '1993-01-01')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '4', 'Hecho imponible', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    search_html = """
    <table>
      <tr>
        <td id="doc_99999">
          <span class="NUM-CONSULTA">V0001-26</span>
          <span class="DESCRIPCION-HECHOS">Hechos del caso.</span>
          <span class="CUESTION-PLANTEADA"><i>Consulta sobre IVA.</i></span>
        </td>
      </tr>
    </table>
    """

    no_results_html = '<div class="extra_padding"><div class="message">La consulta realizada no devuelve resultados.</div></div>'

    document_html = (FIXTURES / "V2274-22-document.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/consultas/":
            return httpx.Response(
                200,
                text="<html></html>",
                headers={"set-cookie": "JSESSIONID=abc123; Path=/consultas; HttpOnly"},
            )
        if request.url.path == "/consultas/do/search":
            content = request.content.decode() if request.content else ""
            if "V0001-26" in content or "V0002-26" in content:
                return httpx.Response(200, text=search_html)
            return httpx.Response(200, text=no_results_html)
        if request.url.path == "/consultas/do/document":
            return httpx.Response(200, text=document_html)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr("dgt.DGT_DISCOVERY", True)
    monkeypatch.setattr("dgt.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "dgt.httpx.Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            base_url="https://petete.tributos.hacienda.gob.es",
        ),
    )
    monkeypatch.setattr("dgt.auto_link_doctrina", lambda conn: 0)

    # With new queue-based discovery: discovery inserts V0001-26 into pending queue,
    # processing picks it up from the queue
    result = run_sync(seed_urls=[])

    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM documento_interpretativo")
        ).scalar_one()

    assert result["stored"] == 1
    assert count == 1


def test_fetch_search_html_for_discovery_returns_none(monkeypatch):
    """fetch_search_html_for_discovery is deprecated — always returns None."""
    from dgt import fetch_search_html_for_discovery
    assert fetch_search_html_for_discovery("V2274-22") is None
