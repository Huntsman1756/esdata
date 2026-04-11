from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from teac import parse_resolution_html, run_sync


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
                    error_msg TEXT
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
                    error_msg TEXT
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
