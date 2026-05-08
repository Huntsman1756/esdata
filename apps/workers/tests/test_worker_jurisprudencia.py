import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jurisprudencia
from jurisprudencia import (
    JurisprudenciaRecord,
    build_canonical_reference,
    main,
    normalize_jurisprudencia_record,
    upsert_jurisprudencia_documento,
)


def test_build_canonical_reference_prefers_ecli_then_roj_then_fallback():
    assert (
        build_canonical_reference(
            ecli="ECLI:ES:TS:2024:2741",
            roj="STS 741/2024",
            organismo_emisor="TS",
            fecha="2024-06-15",
            titulo="STS sobre IVA",
        )
        == "ECLI:ES:TS:2024:2741"
    )

    assert (
        build_canonical_reference(
            ecli=None,
            roj="STS 741/2024",
            organismo_emisor="TS",
            fecha="2024-06-15",
            titulo="STS sobre IVA",
        )
        == "STS 741/2024"
    )

    fallback = build_canonical_reference(
        ecli=None,
        roj=None,
        organismo_emisor="TS",
        fecha="2024-06-15",
        titulo="STS sobre IVA",
    )
    assert fallback.startswith("JURIS-")


def test_normalize_jurisprudencia_record_maps_ts_to_sentencia_ts():
    raw = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "STS 741/2024 - IVA",
        "resumen": "Resumen de prueba",
        "legislacion_citada": [("LIVA", "20")],
        "url_fuente": "https://example.invalid/ts-2741",
        "tipo_fuente": "boe",
    }

    record = normalize_jurisprudencia_record(raw)

    assert record.tipo_documento == "sentencia_ts"
    assert record.ambito == "tributario"
    assert record.jurisdiccion == "es"
    assert record.referencia_canonica == "ECLI:ES:TS:2024:2741"


def test_upsert_jurisprudencia_documento_is_idempotent():
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

        record = JurisprudenciaRecord(
            referencia_canonica="ECLI:ES:TS:2024:2741",
            ecli="ECLI:ES:TS:2024:2741",
            roj="STS 741/2024",
            tipo_documento="sentencia_ts",
            organismo_emisor="TS",
            jurisdiccion="es",
            tipo_fuente="boe",
            ambito="tributario",
            fecha="2024-06-15",
            titulo="STS 741/2024 - IVA",
            resumen="Resumen de prueba",
            ponente=None,
            numero_recurso=None,
            tipo_resolucion=None,
            sala=None,
            legislacion_citada=[("LIVA", "20")],
            url_fuente="https://example.invalid/ts-2741",
            source_priority=100,
        )

        upsert_jurisprudencia_documento(conn, record)
        upsert_jurisprudencia_documento(conn, record)

        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, COUNT(*) FROM documento_interpretativo GROUP BY referencia, tipo_documento, organismo_emisor"
            )
        ).fetchone()

    assert row == ("ECLI:ES:TS:2024:2741", "sentencia_ts", "TS", 1)


def test_upsert_jurisprudencia_documento_updates_mutable_fields():
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

        original = JurisprudenciaRecord(
            referencia_canonica="ECLI:ES:TS:2024:2741",
            ecli="ECLI:ES:TS:2024:2741",
            roj="STS 741/2024",
            tipo_documento="sentencia_ts",
            organismo_emisor="TS",
            jurisdiccion="es",
            tipo_fuente="boe",
            ambito="tributario",
            fecha="2024-06-15",
            titulo="Titulo original",
            resumen="Texto original",
            ponente=None,
            numero_recurso=None,
            tipo_resolucion=None,
            sala=None,
            legislacion_citada=[],
            url_fuente="https://example.invalid/original",
            source_priority=100,
        )
        updated = JurisprudenciaRecord(
            referencia_canonica="ECLI:ES:TS:2024:2741",
            ecli="ECLI:ES:TS:2024:2741",
            roj="STS 741/2024",
            tipo_documento="sentencia_ts",
            organismo_emisor="TS",
            jurisdiccion="es",
            tipo_fuente="boe",
            ambito="tributario",
            fecha="2024-06-15",
            titulo="Titulo actualizado",
            resumen="Texto actualizado",
            ponente=None,
            numero_recurso=None,
            tipo_resolucion=None,
            sala=None,
            legislacion_citada=[],
            url_fuente="https://example.invalid/updated",
            source_priority=100,
        )

        upsert_jurisprudencia_documento(conn, original)
        upsert_jurisprudencia_documento(conn, updated)

        row = conn.execute(
            text(
                "SELECT titulo, texto, url_fuente FROM documento_interpretativo WHERE referencia = 'ECLI:ES:TS:2024:2741'"
            )
        ).fetchone()

    assert row == (
        "Titulo actualizado",
        "Texto actualizado",
        "https://example.invalid/updated",
    )


def test_upsert_jurisprudencia_documento_refreshes_provenance_fields():
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

        original = JurisprudenciaRecord(
            referencia_canonica="ECLI:ES:TS:2024:2741",
            ecli="ECLI:ES:TS:2024:2741",
            roj="STS 741/2024",
            tipo_documento="sentencia_ts",
            organismo_emisor="TS",
            jurisdiccion="es-old",
            tipo_fuente="cendoj",
            ambito="general",
            fecha="2024-01-01",
            titulo="Titulo original",
            resumen="Texto original",
            ponente=None,
            numero_recurso=None,
            tipo_resolucion=None,
            sala=None,
            legislacion_citada=[],
            url_fuente="https://example.invalid/original",
            source_priority=50,
        )
        updated = JurisprudenciaRecord(
            referencia_canonica="ECLI:ES:TS:2024:2741",
            ecli="ECLI:ES:TS:2024:2741",
            roj="STS 741/2024",
            tipo_documento="sentencia_ts",
            organismo_emisor="TS",
            jurisdiccion="es",
            tipo_fuente="boe",
            ambito="tributario",
            fecha="2024-06-15",
            titulo="Titulo actualizado",
            resumen="Texto actualizado",
            ponente=None,
            numero_recurso=None,
            tipo_resolucion=None,
            sala=None,
            legislacion_citada=[],
            url_fuente="https://example.invalid/updated",
            source_priority=100,
        )

        upsert_jurisprudencia_documento(conn, original)
        upsert_jurisprudencia_documento(conn, updated)

        row = conn.execute(
            text(
                "SELECT jurisdiccion, tipo_fuente, ambito, fecha FROM documento_interpretativo WHERE referencia = 'ECLI:ES:TS:2024:2741'"
            )
        ).fetchone()

    assert row == ("es", "boe", "tributario", "2024-06-15")


def test_normalize_jurisprudencia_record_rejects_unsupported_emitter():
    raw = {
        "organismo_emisor": "JCA",
        "fecha": "2024-06-15",
        "titulo": "Resolucion desconocida",
        "resumen": "Resumen",
        "tipo_fuente": "boe",
    }

    try:
        normalize_jurisprudencia_record(raw)
    except ValueError as exc:
        assert "Unsupported organismo_emisor" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported emitter")


def test_sync_jurisprudencia_keeps_outer_transaction_usable_for_logging():
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

        processed, upserted, links, errors = jurisprudencia.sync_jurisprudencia(
            conn,
            [
                (
                    "ECLI:ES:TS:2024:2741",
                    "STS 741/2024",
                    "TS",
                    "Sala de lo Contencioso-Administrativo, Seccion 2",
                    "2024-06-15",
                    "Resumen de prueba",
                    [],
                    "https://example.invalid/ts-2741",
                )
            ],
        )

        jurisprudencia._log_sync_result(
            conn,
            worker_name="jurisprudencia",
            status="ok",
            processed=processed,
            upserted=upserted,
            links=links,
            error_msg="; ".join(errors) if errors else None,
        )

        row = conn.execute(
            text("SELECT worker, status, documentos_processed FROM sync_log")
        ).fetchone()

    assert row == ("jurisprudencia", "ok", 1)


def test_run_once_uses_canonical_reference_and_shared_log_helpers(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    helper_calls = {"ensure": 0, "log": []}

    monkeypatch.setattr("jurisprudencia.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "jurisprudencia.SENTENCIAS_SEED",
        [
            (
                "ECLI:ES:TS:2024:2741",
                "STS 741/2024",
                "TS",
                "Sala de lo Contencioso-Administrativo, Seccion 2",
                "2024-06-15",
                "Resumen de prueba",
                [],
                "https://example.invalid/ts-2741",
            )
        ],
    )
    monkeypatch.setattr(
        "jurisprudencia._ensure_sync_log_table",
        lambda conn: helper_calls.__setitem__("ensure", helper_calls["ensure"] + 1),
    )

    def fake_log_sync(conn, worker, status, **kwargs):
        helper_calls["log"].append((worker, status, kwargs))

    monkeypatch.setattr("jurisprudencia.log_sync", fake_log_sync)
    monkeypatch.setattr(
        sys,
        "argv",
        ["jurisprudencia.py", "--run-once", "--db-url", "sqlite:///:memory:"],
    )

    main()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, jurisdiccion FROM documento_interpretativo"
            )
        ).fetchone()

    assert row == ("ECLI:ES:TS:2024:2741", "sentencia_ts", "TS", "es")
    assert helper_calls["ensure"] == 1
    assert helper_calls["log"] == [
        (
            "cron-jurisprudencia-weekly",
            "ok",
            {
                "documentos_processed": 1,
                "documentos_upserted": 1,
                "doctrina_links_created": 0,
            },
        )
    ]


def test_run_sync_keeps_working_when_cendoj_fails(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    boe_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "STS 741/2024 - IVA",
        "resumen": "Resumen BOE",
        "legislacion_citada": [("LIVA", "20")],
        "url_fuente": "https://example.invalid/boe/2741",
        "tipo_fuente": "boe",
        "source_priority": 100,
    }

    monkeypatch.setattr("jurisprudencia.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("jurisprudencia.fetch_boe_records", lambda client: [boe_record])

    def failing_cendoj(client):
        raise httpx.HTTPError("cendoj unavailable")

    monkeypatch.setattr("jurisprudencia.fetch_cendoj_records", failing_cendoj)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL
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
                    numero TEXT NOT NULL
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
                    UNIQUE (documento_id, articulo_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO norma (codigo) VALUES ('LIVA')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero)
                VALUES ((SELECT id FROM norma WHERE codigo = 'LIVA'), '20')
                """
            )
        )

    result = jurisprudencia.run_sync(worker_name="worker-jurisprudencia")

    with engine.begin() as conn:
        documento_row = conn.execute(
            text(
                "SELECT id, referencia, tipo_fuente, texto FROM documento_interpretativo"
            )
        ).fetchone()
        link_row = conn.execute(
            text("SELECT metodo_enlace, confianza_enlace, nota FROM documento_articulo")
        ).fetchone()
        log_row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted, doctrina_links_created, error_msg FROM sync_log"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1, "links": 1, "errors": 1}
    assert documento_row == (1, "ECLI:ES:TS:2024:2741", "boe", "Resumen BOE")
    assert link_row == (
        "fuente_estructurada",
        1.0,
        "Jurisprudencia enlazada por legislacion citada",
    )
    assert log_row == (
        "worker-jurisprudencia",
        "ok",
        1,
        1,
        1,
        "cendoj unavailable",
    )


def test_run_sync_deduplicates_same_sentence_across_sources(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    boe_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "Sentencia BOE",
        "resumen": "Resumen BOE prioritario",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/boe/2741",
        "tipo_fuente": "boe",
        "source_priority": 100,
    }
    cendoj_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "Sentencia CENDOJ",
        "resumen": "Resumen CENDOJ secundario",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/cendoj/2741",
        "tipo_fuente": "cendoj",
        "source_priority": 50,
    }

    monkeypatch.setattr("jurisprudencia.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("jurisprudencia.fetch_boe_records", lambda client: [boe_record])
    monkeypatch.setattr(
        "jurisprudencia.fetch_cendoj_records", lambda client: [cendoj_record]
    )
    monkeypatch.setattr("jurisprudencia._ensure_sync_log_table", lambda conn: None)
    monkeypatch.setattr(
        "jurisprudencia.log_sync", lambda conn, worker, status, **kwargs: None
    )

    result = jurisprudencia.run_sync()

    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM documento_interpretativo")
        ).scalar_one()
        row = conn.execute(
            text(
                "SELECT referencia, tipo_fuente, titulo, texto, url_fuente FROM documento_interpretativo"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1, "links": 0, "errors": 0}
    assert count == 1
    assert row == (
        "ECLI:ES:TS:2024:2741",
        "boe",
        "Sentencia BOE",
        "Resumen BOE prioritario",
        "https://example.invalid/boe/2741",
    )


def test_run_sync_upgrades_existing_record_with_higher_priority_source(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    cendoj_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-01-10",
        "titulo": "Sentencia CENDOJ",
        "resumen": "Resumen CENDOJ",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/cendoj/2741",
        "tipo_fuente": "cendoj",
        "source_priority": 50,
    }
    boe_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "Sentencia BOE",
        "resumen": "Resumen BOE",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/boe/2741",
        "tipo_fuente": "boe",
        "source_priority": 100,
    }

    monkeypatch.setattr("jurisprudencia.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("jurisprudencia._ensure_sync_log_table", lambda conn: None)
    monkeypatch.setattr(
        "jurisprudencia.log_sync", lambda conn, worker, status, **kwargs: None
    )

    monkeypatch.setattr("jurisprudencia.fetch_boe_records", lambda client: [])
    monkeypatch.setattr(
        "jurisprudencia.fetch_cendoj_records", lambda client: [cendoj_record]
    )
    jurisprudencia.run_sync()

    monkeypatch.setattr("jurisprudencia.fetch_boe_records", lambda client: [boe_record])
    monkeypatch.setattr("jurisprudencia.fetch_cendoj_records", lambda client: [])
    jurisprudencia.run_sync()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT tipo_fuente, fecha, jurisdiccion, ambito, titulo, texto, url_fuente FROM documento_interpretativo WHERE referencia = 'ECLI:ES:TS:2024:2741'"
            )
        ).fetchone()

    assert row == (
        "boe",
        "2024-06-15",
        "es",
        "tributario",
        "Sentencia BOE",
        "Resumen BOE",
        "https://example.invalid/boe/2741",
    )


def test_run_sync_tolerates_malformed_cendoj_record_and_surfaces_degraded_signal(
    monkeypatch,
):
    engine = create_engine("sqlite:///:memory:", future=True)

    boe_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "Sentencia BOE",
        "resumen": "Resumen BOE",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/boe/2741",
        "tipo_fuente": "boe",
        "source_priority": 100,
    }
    malformed_cendoj_record = {
        "roj": "STS 999/2024",
        "fecha": "2024-06-15",
        "titulo": "Malformed CENDOJ",
        "resumen": "Sin organismo emisor",
        "tipo_fuente": "cendoj",
        "source_priority": 50,
    }

    monkeypatch.setattr("jurisprudencia.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("jurisprudencia.fetch_boe_records", lambda client: [boe_record])
    monkeypatch.setattr(
        "jurisprudencia.fetch_cendoj_records", lambda client: [malformed_cendoj_record]
    )

    result = jurisprudencia.run_sync(worker_name="worker-jurisprudencia")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted, error_msg FROM sync_log"
            )
        ).fetchone()

    assert result == {"processed": 1, "stored": 1, "links": 0, "errors": 1}
    assert row[0:4] == ("worker-jurisprudencia", "ok", 1, 1)
    assert "organismo_emisor" in row[4]


def test_run_sync_keeps_successful_rows_when_one_record_link_fails(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)

    good_record = {
        "ecli": "ECLI:ES:TS:2024:2741",
        "roj": "STS 741/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-15",
        "titulo": "Sentencia enlazable",
        "resumen": "Resumen enlazable",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/boe/2741",
        "tipo_fuente": "boe",
        "source_priority": 100,
    }
    failing_record = {
        "ecli": "ECLI:ES:TS:2024:9999",
        "roj": "STS 9999/2024",
        "organismo_emisor": "TS",
        "fecha": "2024-06-16",
        "titulo": "Sentencia con fallo",
        "resumen": "Resumen con fallo",
        "legislacion_citada": [],
        "url_fuente": "https://example.invalid/boe/9999",
        "tipo_fuente": "boe",
        "source_priority": 100,
    }

    monkeypatch.setattr("jurisprudencia.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "jurisprudencia.fetch_boe_records", lambda client: [good_record, failing_record]
    )
    monkeypatch.setattr("jurisprudencia.fetch_cendoj_records", lambda client: [])

    original_link = jurisprudencia.link_jurisprudencia_articulos

    def flaky_link(conn, documento_id, articulos):
        row = conn.execute(
            text("SELECT referencia FROM documento_interpretativo WHERE id = :id"),
            {"id": documento_id},
        ).fetchone()
        if row[0] == "ECLI:ES:TS:2024:9999":
            raise RuntimeError("forced link failure")
        return original_link(conn, documento_id, articulos)

    monkeypatch.setattr("jurisprudencia.link_jurisprudencia_articulos", flaky_link)

    result = jurisprudencia.run_sync(worker_name="worker-jurisprudencia")

    with engine.begin() as conn:
        refs = conn.execute(
            text("SELECT referencia FROM documento_interpretativo ORDER BY referencia")
        ).fetchall()
        log_row = conn.execute(
            text(
                "SELECT worker, status, documentos_processed, documentos_upserted, error_msg FROM sync_log"
            )
        ).fetchone()

    assert result == {"processed": 2, "stored": 1, "links": 0, "errors": 1}
    assert refs == [("ECLI:ES:TS:2024:2741",)]
    assert log_row[0:4] == ("worker-jurisprudencia", "ok", 2, 1)
    assert "forced link failure" in log_row[4]
