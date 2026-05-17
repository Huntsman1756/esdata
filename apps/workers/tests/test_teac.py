from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from teac import (
    DYCTEA_ROOT_URL,
    _extract_hidden_inputs,
    discover_resolution_urls,
    parse_dyctea_search_results,
    parse_resolution_html,
    run_sync,
    upsert_documento_interpretativo,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_resolution_html_extracts_core_fields():
    html = (FIXTURES / "teac-resolution.html").read_text(encoding="utf-8")

    data = parse_resolution_html(html)

    assert data == {
        "referencia": "00/1234/2024",
        "fecha": "2024-03-15",
        "organo": "Tribunal Economico-Administrativo Central",
        "titulo": "IVA. Base imponible en operaciones vinculadas.",
        "texto": "Se estima parcialmente la reclamacion y se fija criterio sobre la base imponible del IVA. La resolucion analiza el articulo 91 de la Ley 37/1992 y su aplicacion al caso.",
    }


def test_parse_resolution_html_supports_live_dyctea_markup():
    html = """
    <div id='criterioDatosTitulo' class='criterioDatosFila'>
        Criterio <span class='criterioNegrita'>1</span> de <span class='criterioNegrita'>1</span> de la resolucion: <span class='criterioNegrita'>00/01362/2024/00/00</span>
    </div>
    <div id='criterioDatosUnidad' class='criterioDatosFila'>
        Unidad resolutoria: <span class='criterioNegrita'>TEAC</span>
    </div>
    <div id='criterioDatosFecha' class='criterioDatosFila'>
        Fecha de la resolucion: <span class='criterioNegrita'>27/02/2026</span>
    </div>
    <div id='criterioDatosAsunto' class='criterioDatosFila'>
        <span class='criterioNegrita'>Asunto: </span><br /><p>IVA. Plazo para el ejercicio del derecho a la rectificacion.</p>
    </div>
    <div id='criterioDatosContenido' class='criterioDatosFila'>
        <span class='criterioNegrita'>Criterio: </span><br />
        <p>El articulo 89.Cinco b) de la Ley 37/1992 permite regularizar la situacion tributaria.</p>
    </div>
    """

    data = parse_resolution_html(html)

    assert data == {
        "referencia": "00/01362/2024/00/00",
        "fecha": "2026-02-27",
        "organo": "TEAC",
        "titulo": "IVA. Plazo para el ejercicio del derecho a la rectificacion.",
        "texto": "El articulo 89.Cinco b) de la Ley 37/1992 permite regularizar la situacion tributaria.",
    }


def test_run_sync_persists_teac_document_and_metrics(monkeypatch):
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
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    html = (FIXTURES / "teac-resolution.html").read_text(encoding="utf-8")

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", lambda url: html)

    result = run_sync(
        seed_urls=["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-1234-2024"]
    )

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente FROM documento_interpretativo"
            )
        ).fetchone()
        sync_row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log"
            )
        ).fetchone()
        link_row = conn.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1}
    assert row == ("00/1234/2024", "resolucion_teac", "TEAC", "teac")
    assert sync_row == ("worker-teac", "ok", 1, 1)
    assert link_row == ("LIVA", "91", 1.0)


def test_run_sync_uses_default_seed_urls(monkeypatch):
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
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    html = (FIXTURES / "teac-resolution.html").read_text(encoding="utf-8")

    monkeypatch.setattr(
        "teac.SEED_URLS",
        ["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-1234-2024"],
    )
    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", lambda url: html)

    result = run_sync()

    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM documento_interpretativo")
        ).scalar_one()
        sync_row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted FROM sync_log"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1}
    assert count == 1
    assert sync_row == ("worker-teac", "ok", 1, 1)


def test_teac_run_once_flag_accepts_argparse():
    workers_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "teac.py", "--help"],
        capture_output=True,
        text=True,
        cwd=workers_dir,
        env={**__import__("os").environ, "DATABASE_URL": "sqlite:///:memory:"},
    )
    assert result.returncode == 0
    assert "--run-once" in result.stdout
    assert "--interval" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--max-results" in result.stdout


def test_parse_dyctea_search_results_extracts_metadata_and_url():
    html = """
    <div id='resultadosCriterios'>
      <ul>
        <li class='resultadoCriterio'>
          <span class='resultadoCriterioTitulo'>
            <a href='criterio.aspx?id=00/01234/2024/00/0/1'>
              Criterio 1 de la resolucion 00/01234/2024/00/00 del 15/03/2024 - TEAC
            </a>
          </span>
          <span>Unidad resolutoria: Sala Primera</span>
          <span>Concepto: IRNR. Retencion no residente</span>
        </li>
      </ul>
    </div>
    """

    results = parse_dyctea_search_results(html, DYCTEA_ROOT_URL)

    assert results == [
        {
            "referencia": "00/01234/2024/00/00",
            "fecha": "2024-03-15",
            "sala": "Sala Primera",
            "materia": "IRNR. Retencion no residente",
            "titulo": "Criterio 1 de la resolucion 00/01234/2024/00/00 del 15/03/2024 - TEAC",
            "url_oficial": "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/criterio.aspx?id=00/01234/2024/00/0/1",
        }
    ]


def test_extract_hidden_inputs_excludes_search_and_reset_controls():
    html = """
    <input type="hidden" name="__VIEWSTATE" value="abc" />
    <input name="ctl00$contentBody$tbFechaDesde" type="text" value="" />
    <input type="checkbox" name="ctl00$contentBody$cbCriterios" checked="checked" />
    <input type="submit" name="ctl00$contentBody$btSearch" value="Buscar" />
    <input type="submit" name="ctl00$contentBody$btReset" value="Limpiar" />
    """

    assert _extract_hidden_inputs(html) == {"__VIEWSTATE": "abc"}


def test_upsert_documento_interpretativo_is_idempotent_and_stores_quality_contract():
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
                    metadata TEXT,
                    row_completeness TEXT,
                    row_provenance TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "00/01234/2024/00/00",
            "fecha": "2024-03-15",
            "titulo": "IRNR. Retencion no residente",
            "texto": "Criterio completo oficial del TEAC.",
            "url_fuente": "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/criterio.aspx?id=00/01234/2024/00/0/1",
            "sala": "Sala Primera",
            "materia": "IRNR",
            "row_completeness": "complete",
            "row_provenance": "official_exact",
            "verified": True,
        }

        upsert_documento_interpretativo(conn, payload)
        upsert_documento_interpretativo(conn, payload)

        row = conn.execute(
            text(
                """
                SELECT COUNT(*), row_completeness, row_provenance, metadata
                FROM documento_interpretativo
                GROUP BY row_completeness, row_provenance, metadata
                """
            )
        ).fetchone()

    assert row[0] == 1
    assert row[1] == "complete"
    assert row[2] == "official_exact"
    assert '"verified": true' in row[3]
    assert '"sala": "Sala Primera"' in row[3]


def test_run_sync_applies_request_delay_between_resolution_fetches(monkeypatch):
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

    def _html_for(url: str) -> str:
        ref = "00/01234/2024/00/00" if "01234" in url else "00/05678/2024/00/00"
        return f"""
        <div id='criterioDatosTitulo'>resolucion: <span class='criterioNegrita'>{ref}</span></div>
        <div id='criterioDatosUnidad'>Unidad resolutoria: <span class='criterioNegrita'>TEAC</span></div>
        <div id='criterioDatosFecha'>Fecha de la resolucion: <span class='criterioNegrita'>15/03/2024</span></div>
        <div id='criterioDatosAsunto'><p>IVA. Base imponible.</p></div>
        <div id='criterioDatosContenido'><p>Texto completo oficial.</p></div>
        """

    sleeps = []
    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", _html_for)
    monkeypatch.setenv("WORKER_REQUEST_DELAY", "0.25")
    monkeypatch.setattr("teac.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("teac.auto_link_doctrina", lambda conn: 0)

    result = run_sync(
        seed_urls=[
            f"{DYCTEA_ROOT_URL}criterio.aspx?id=00/01234/2024/00/0/1",
            f"{DYCTEA_ROOT_URL}criterio.aspx?id=00/05678/2024/00/0/1",
        ]
    )

    assert result == {"processed": 2, "stored": 2}
    assert sleeps == [0.25, 0.25]


def test_run_sync_handles_fetch_errors_without_nameerror(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)

    def _raise_timeout(url):
        raise TimeoutError("upstream timeout")

    monkeypatch.setattr("teac.fetch_resolution_html", _raise_timeout)

    with pytest.raises(TimeoutError, match="upstream timeout"):
        run_sync(seed_urls=["https://example.com/teac"])


def test_discover_resolution_urls_extracts_links_from_search_results():
    html = """
    <div id='resultadosCriterios'>
      <ul>
        <li class='resultadoCriterio'>
          <span class='resultadoCriterioTitulo'>
            <a href='criterio.aspx?id=00/07402/2022/00/0/1&amp;q=s%3d1'>
              Criterio 1 de la resolución 00/07402/2022/00/00 del 07/04/2026 - TEAC
            </a>
          </span>
        </li>
      </ul>
    </div>
    """

    urls = discover_resolution_urls(DYCTEA_ROOT_URL, html)

    assert urls == [
        "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/criterio.aspx?id=00/07402/2022/00/0/1&q=s%3d1"
    ]


def test_run_sync_supports_dyctea_landing_seed(monkeypatch):
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
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    search_html = """
    <div id='resultadosCriterios'>
      <ul>
        <li class='resultadoCriterio'>
          <span class='resultadoCriterioTitulo'>
            <a href='criterio.aspx?id=00/07402/2022/00/0/1&amp;q=s%3d1'>
              Criterio 1 de la resolución 00/07402/2022/00/00 del 07/04/2026 - TEAC
            </a>
          </span>
        </li>
      </ul>
    </div>
    """
    resolution_html = (FIXTURES / "teac-resolution.html").read_text(encoding="utf-8")

    def _fetch(url):
        if url == DYCTEA_ROOT_URL:
            return search_html
        return resolution_html

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", _fetch)

    result = run_sync(seed_urls=[DYCTEA_ROOT_URL])

    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM documento_interpretativo")).scalar_one()

    assert result == {"processed": 1, "stored": 1}
    assert count == 1


def test_run_sync_teac_creates_contextual_liva_link(monkeypatch):
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
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    html = (FIXTURES / "teac-contextual-resolution.html").read_text(encoding="utf-8")

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", lambda url: html)

    result = run_sync(
        seed_urls=["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-9876-2024"]
    )

    with engine.begin() as conn:
        link_row = conn.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1}
    assert link_row == ("LIVA", "91", 0.75)


def test_run_sync_teac_creates_contextual_regimen_especial_link(monkeypatch):
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
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    html = (FIXTURES / "teac-regimen-especial-resolution.html").read_text(
        encoding="utf-8"
    )

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", lambda url: html)

    result = run_sync(
        seed_urls=["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-2468-2024"]
    )

    with engine.begin() as conn:
        link_row = conn.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1}
    assert link_row == ("LIVA", "91", 0.75)


def test_run_sync_teac_creates_contextual_recargo_link(monkeypatch):
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
                SELECT id, '24', 'Recargo de equivalencia', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    html = (FIXTURES / "teac-recargo-equivalencia-resolution.html").read_text(
        encoding="utf-8"
    )

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", lambda url: html)

    result = run_sync(
        seed_urls=["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-3579-2024"]
    )

    with engine.begin() as conn:
        link_row = conn.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1}
    assert link_row == ("LIVA", "24", 0.75)


def test_run_sync_records_correct_worker_name_for_continuous_vs_cron(monkeypatch):
    """Verify run_sync logs sync_log with the provided worker_name, not a hardcoded value."""
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
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )

    html = (FIXTURES / "teac-resolution.html").read_text(encoding="utf-8")

    monkeypatch.setattr("teac.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("teac.fetch_resolution_html", lambda url: html)

    # Continuous mode default
    run_sync(
        seed_urls=["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-1234-2024"]
    )
    # Cron mode explicit
    run_sync(
        seed_urls=["https://serviciostelematicosext.hacienda.gob.es/TEAC/00-1234-2024"],
        worker_name="cron-teac-weekly",
    )

    with engine.begin() as conn:
        workers = conn.execute(
            text("SELECT worker FROM sync_log ORDER BY id")
        ).fetchall()

    assert [w[0] for w in workers] == ["worker-teac", "cron-teac-weekly"]


def test_parse_resolution_html_fallback_when_date_is_none():
    html = (FIXTURES / "teac-no-date-resolution.html").read_text(encoding="utf-8")

    data = parse_resolution_html(html)

    assert data["referencia"] == "00/5678/2024"
    assert data["organo"] == "Tribunal Economico-Administrativo Central"
    assert data["titulo"] == "IRPF. Deduccion por doble imposicion en dividendos."
    assert data["texto"] == "Se estima la reclamacion y se aplica el criterio sobre la deduccion por doble imposicion en dividendos del IRPF."
    assert data["fecha"] is not None
    assert len(data["fecha"]) == 10
    assert "/" not in data["fecha"]


def test_run_sync_empty_seed_urls_returns_zero():
    """SEED_URLS vacío debe devolver processed=0, stored=0 sin hacer HTTP."""
    result = run_sync(seed_urls=[])
    assert result == {"processed": 0, "stored": 0}
