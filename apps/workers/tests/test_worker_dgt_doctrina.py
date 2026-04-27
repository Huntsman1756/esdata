"""Tests unitarios para el worker dgt_doctrina de rendimientos mobiliarios."""

import sys
import subprocess
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dgt_doctrina import (
    _extract_target_normas_rendimiento,
    run_sync,
)


def test_extract_target_normas_rendimiento_detects_lirpf():
    html = """
    <table>
      <tr class="NORMATIVA"><td class="value">Ley 35/2006 del IRPF</td></tr>
      <tr class="CONTESTACION-COMPL"><td class="value">Los dividendos constituyen rendimientos del capital mobiliario segun art. 30 LIRPF.</td></tr>
    </table>
    """
    normas = _extract_target_normas_rendimiento(
        "Los dividendos constituyen rendimientos del capital mobiliario segun art. 30 LIRPF.",
        "Ley 35/2006 del IRPF",
    )
    assert "LIRPF" in normas


def test_extract_target_normas_rendimiento_detects_irnr():
    normas = _extract_target_normas_rendimiento(
        "No residente en Espana sujeto a IRNR por dividendos.",
        "RLD 435/1995 RIRNR",
    )
    assert "IRNR" in normas


def test_extract_target_normas_rendimiento_detects_lis():
    normas = _extract_target_normas_rendimiento(
        "Rendimientos de sociedades sujetos a LIS.",
        "Ley 27/2014 del Impuesto de Sociedades",
    )
    assert "LIS" in normas


def test_extract_target_normas_rendimiento_detects_liva():
    normas = _extract_target_normas_rendimiento(
        "IVA sobre entregas de bienes.",
        "Ley 37/1992 del IVA",
    )
    assert "LIVA" in normas


def test_extract_target_normas_rendimiento_detects_multiple_normas():
    normas = _extract_target_normas_rendimiento(
        "Dividendos de sociedad no residente: rendimientos mobiliarios IRNR y LIS.",
        "Ley 35/2006 IRPF, RLD 435/1995 RIRNR, Ley 27/2014 LIS",
    )
    assert "LIRPF" in normas
    assert "IRNR" in normas
    assert "LIS" in normas


def test_extract_target_normas_rendimiento_returns_empty_for_unrelated():
    normas = _extract_target_normas_rendimiento(
        "Consulta sobre rendimientos del trabajo.",
        "Ley 35/2006 IRPF",
    )
    assert normas == []


def test_extract_target_normas_rendimiento_handles_none():
    normas = _extract_target_normas_rendimiento(None, None)
    assert normas == []


def test_run_sync_persists_dgt_rendimiento_document(monkeypatch):
    """Verifica que run_sync almacena documentos con normas de rendimiento."""
    engine = create_engine("sqlite:///:memory:", future=True)
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
                    error_msg TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
                VALUES ('LIRPF', 'Ley IRPF', 'BOE-A-2006-20764', NULL, 'es', 'boe', 'fiscal', '2006-12-01')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '30', 'Rendimientos del capital mobiliario', 'articulo' FROM norma WHERE codigo = 'LIRPF'
                """
            )
        )

    search_html = """
    <table>
      <tr>
        <td id="doc_55555">
          <span class="NUM-CONSULTA">V2965-17</span>
          <span class="DESCRIPCION-HECHOS">Rendimientos mobiliarios y retenciones.</span>
          <span class="CUESTION-PLANTEADA"><i>Retenciones en dividendos al 19%.</i></span>
        </td>
      </tr>
    </table>
    """

    document_html = """
    <table>
      <tr class="NUM-CONSULTA"><td class="value">V2965-17</td></tr>
      <tr class="ORGANO"><td class="value">SG de Impuestos sobre la Renta</td></tr>
      <tr class="FECHA-SALIDA"><td class="value">10/05/2017</td></tr>
      <tr class="NORMATIVA"><td class="value">Ley 35/2006 art. 30 LIRPF</td></tr>
      <tr class="CUESTION-PLANTEADA"><td class="value">Retenciones en dividendos.</td></tr>
      <tr class="CONTESTACION-COMPL"><td class="value">Los dividendos constituyen rendimientos del capital mobiliario sujetos a retencion del 19%.</td></tr>
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
            return httpx.Response(200, text=document_html)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(
        "dgt_doctrina.SEED_URLS",
        ["https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V2965-17"],
    )
    monkeypatch.setattr("dgt_doctrina.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "dgt_doctrina.httpx.Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            base_url="https://petete.tributos.hacienda.gob.es",
        ),
    )

    result = run_sync(worker_name="test-dgt-rendimiento")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT referencia, tipo_fuente, organismo_emisor FROM documento_interpretativo"
            )
        ).fetchone()
        sync_row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted, doctrina_links_created "
                "FROM sync_log"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1}
    assert row == ("V2965-17", "dgt", "DGT")
    assert sync_row == ("test-dgt-rendimiento", "ok", 1, 1, 0)


def test_run_sync_skips_non_rendimiento_documents(monkeypatch):
    """Verifica que documentos sin normas de rendimiento se omiten."""
    engine = create_engine("sqlite:///:memory:", future=True)
    original_client = httpx.Client

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
                    error_msg TEXT
                )
                """
            )
        )

    search_html = """
    <table>
      <tr>
        <td id="doc_66666">
          <span class="NUM-CONSULTA">V0001-26</span>
          <span class="DESCRIPCION-HECHOS">Hechos del caso.</span>
          <span class="CUESTION-PLANTEADA"><i>Consulta sobre IRPF rendimientos del trabajo.</i></span>
        </td>
      </tr>
    </table>
    """

    document_html = """
    <table>
      <tr class="NUM-CONSULTA"><td class="value">V0001-26</td></tr>
      <tr class="ORGANO"><td class="value">SG de Impuestos sobre la Renta</td></tr>
      <tr class="FECHA-SALIDA"><td class="value">15/01/2026</td></tr>
      <tr class="NORMATIVA"><td class="value">Ley 35/2006 art. 25 LIRPF</td></tr>
      <tr class="CUESTION-PLANTEADA"><td class="value">Rendimientos del trabajo.</td></tr>
      <tr class="CONTESTACION-COMPL"><td class="value">La consulta trata sobre rendimientos del trabajo, no mobiliarios.</td></tr>
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
            return httpx.Response(200, text=document_html)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(
        "dgt_doctrina.SEED_URLS",
        ["https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V0001-26"],
    )
    monkeypatch.setattr("dgt_doctrina.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "dgt_doctrina.httpx.Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            base_url="https://petete.tributos.hacienda.gob.es",
        ),
    )

    result = run_sync(worker_name="test-dgt-rendimiento")

    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM documento_interpretativo")
        ).scalar_one()
        sync_row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted "
                "FROM sync_log"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 0}
    assert count == 0
    assert sync_row == ("test-dgt-rendimiento", "ok", 1, 0)


def test_dgt_doctrina_run_once_flag_accepts_argparse():
    workers_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "dgt_doctrina.py", "--help"],
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

    monkeypatch.setattr("dgt_doctrina.httpx.Client", fake_client)
    monkeypatch.setattr("dgt_doctrina.create_engine", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr("dgt_doctrina._ensure_sync_log_table", lambda conn: None)
    monkeypatch.setattr("dgt_doctrina.log_sync", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="stop after client init"):
        run_sync(seed_urls=[])

    assert captured["verify"] is False
