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
