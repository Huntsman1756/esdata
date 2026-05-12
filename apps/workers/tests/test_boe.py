import sys
import subprocess
from contextlib import contextmanager
from pathlib import Path
import httpx
from unittest.mock import patch

from sqlalchemy import create_engine, event, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boe import (
    BloqueTexto,
    NormaMetadata,
    _hold_sync_lock,
    _ensure_sync_log_table,
    _ensure_schema,
    _yyyymmdd_to_iso,
    auto_link_doctrina,
    auto_link_materias,
    parse_block_xml,
    parse_block_xml_versions,
    parse_index,
    parse_metadata,
    upsert_articulo,
    upsert_norma,
)


def test_parse_block_xml_uses_latest_valid_boe_version():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <data>
    <bloque id="a90" tipo="precepto" titulo="ArtÃ­culo 90">
      <version fecha_vigencia="19930101">
        <p>ArtÃ­culo 90. Tipo impositivo general.</p>
        <p>Uno. El impuesto se exigirÃ¡ al tipo del 15 por 100.</p>
      </version>
      <version fecha_vigencia="20120715">
        <p>ArtÃ­culo 90. Tipo impositivo general.</p>
        <p>Uno. El impuesto se exigirÃ¡ al tipo del 21 por ciento.</p>
      </version>
    </bloque>
  </data>
</response>"""

    block = parse_block_xml("a90", xml)

    assert block.vigente_desde == "2012-07-15"
    assert "21 por ciento" in block.texto
    assert "15 por 100" not in block.texto


def test_parse_block_xml_versions_keeps_full_official_history():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <data>
    <bloque id="a90" tipo="precepto" titulo="ArtÃƒÂ­culo 90">
      <version fecha_vigencia="19930101">
        <p>ArtÃƒÂ­culo 90. Tipo impositivo general.</p>
        <p>Uno. El impuesto se exigirÃƒÂ¡ al tipo del 15 por 100.</p>
      </version>
      <version fecha_vigencia="20100701">
        <p>ArtÃƒÂ­culo 90. Tipo impositivo general.</p>
        <p>Uno. El impuesto se exigirÃƒÂ¡ al tipo del 18 por ciento.</p>
      </version>
      <version fecha_vigencia="20120715">
        <p>ArtÃƒÂ­culo 90. Tipo impositivo general.</p>
        <p>Uno. El Impuesto se exigirÃƒÂ¡ al tipo del 21 por ciento.</p>
      </version>
    </bloque>
  </data>
</response>"""

    versions = parse_block_xml_versions("a90", xml)

    assert [version.vigente_desde for version in versions] == [
        "1993-01-01",
        "2010-07-01",
        "2012-07-15",
    ]
    assert "18 por ciento" in versions[1].texto


def test_yyyymmdd_to_iso_rejects_malformed_boe_date():
    try:
        _yyyymmdd_to_iso("--")
    except ValueError as exc:
        assert "Invalid BOE date" in str(exc)
    else:
        raise AssertionError("malformed BOE date must be rejected")


def test_parse_metadata_maps_boe_payload():
    payload = {
        "data": [
            {
                "titulo": "Ley 37/1992, de 28 de diciembre, del Impuesto sobre el Valor Anadido.",
                "fecha_vigencia": "19930101",
                "url_eli": "https://www.boe.es/eli/es/l/1992/12/28/37",
            }
        ]
    }

    metadata = parse_metadata("LIVA", "BOE-A-1992-28740", payload)

    assert metadata == NormaMetadata(
        codigo="LIVA",
        boe_id="BOE-A-1992-28740",
        titulo="Ley 37/1992, de 28 de diciembre, del Impuesto sobre el Valor Anadido.",
        eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
        jurisdiccion="es",
        tipo_fuente="boe",
        tipo_documento="ley",
        ambito="tributario",
        estado_cobertura="ingestada",
        vigente_desde="1993-01-01",
    )


def test_parse_metadata_uses_per_code_classification_for_itpajd():
    payload = {
        "data": [
            {
                "titulo": "Real Decreto Legislativo 1/1993, de 24 de septiembre, por el que se aprueba el texto refundido de la Ley del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados.",
                "fecha_vigencia": "19930925",
                "url_eli": "https://www.boe.es/eli/es/rdlg/1993/09/24/1",
            }
        ]
    }

    metadata = parse_metadata("ITPAJD", "BOE-A-1993-25359", payload)

    assert metadata == NormaMetadata(
        codigo="ITPAJD",
        boe_id="BOE-A-1993-25359",
        titulo="Real Decreto Legislativo 1/1993, de 24 de septiembre, por el que se aprueba el texto refundido de la Ley del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados.",
        eli_uri="https://www.boe.es/eli/es/rdlg/1993/09/24/1",
        jurisdiccion="es",
        tipo_fuente="boe",
        tipo_documento="real_decreto_legislativo",
        ambito="tributario",
        estado_cobertura="ingestada",
        vigente_desde="1993-09-25",
    )


def test_parse_metadata_keeps_existing_tax_norms_as_tributario():
    payload = {
        "data": [
            {
                "titulo": "Ley 58/2003, de 17 de diciembre, General Tributaria.",
                "fecha_vigencia": "20040701",
                "url_eli": "https://www.boe.es/eli/es/l/2003/12/17/58",
            }
        ]
    }

    metadata = parse_metadata("LGT", "BOE-A-2003-23186", payload)

    assert metadata.ambito == "tributario"
    assert metadata.tipo_documento == "ley"


def test_default_normas_include_itpajd():
    from boe import DEFAULT_NORMAS

    assert DEFAULT_NORMAS["ITPAJD"] == "BOE-A-1993-25359"


def test_run_sync_ingests_itpajd_article_and_version():
    from boe import run_sync

    class FakeResponse:
        def __init__(self, *, json_data=None, text_data=""):
            self._json_data = json_data
            self.text = text_data

        def raise_for_status(self):
            return None

        def json(self):
            return self._json_data

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None):
            if url.endswith("/id/BOE-A-1993-25359/metadatos"):
                return FakeResponse(
                    json_data={
                        "data": [
                            {
                                "titulo": "Real Decreto Legislativo 1/1993, de 24 de septiembre, por el que se aprueba el texto refundido de la Ley del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados.",
                                "fecha_vigencia": "19930925",
                                "url_eli": "https://www.boe.es/eli/es/rdlg/1993/09/24/1",
                            }
                        ]
                    }
                )
            if url.endswith("/id/BOE-A-1993-25359/texto/indice"):
                return FakeResponse(
                    json_data={
                        "data": [
                            {
                                "bloque": [
                                    {
                                        "id": "a7",
                                        "titulo": "Artículo 7",
                                        "fecha_actualizacion": "20240101",
                                    }
                                ]
                            }
                        ]
                    }
                )
            if url.endswith("/id/BOE-A-1993-25359/texto/bloque/a7"):
                return FakeResponse(
                    text_data="""
                    <response>
                      <data>
                        <bloque id="a7" tipo="precepto" titulo="Artículo 7">
                          <version id_norma="BOE-A-1993-25359" fecha_publicacion="19930925" fecha_vigencia="19930925">
                            <p class="articulo">Artículo 7. Operaciones societarias.</p>
                            <p class="parrafo">Uno. Son operaciones societarias sujetas las previstas en esta norma.</p>
                          </version>
                        </bloque>
                      </data>
                    </response>
                    """
                )
            raise AssertionError(f"Unexpected URL requested: {url}")

    engine = create_engine("sqlite:///:memory:", future=True)

    with patch("boe.httpx.Client", return_value=FakeClient()):
        with patch("boe.create_engine", return_value=engine):
            result = run_sync(["ITPAJD"])

    assert result == {"bloques": 1, "articulos": 1}

    with engine.begin() as conn:
        norma = conn.execute(
            text(
                "SELECT codigo, boe_id, tipo_documento, ambito, estado_cobertura FROM norma WHERE codigo = 'ITPAJD'"
            )
        ).fetchone()
        articulo = conn.execute(
            text(
                "SELECT a.numero, a.tipo FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'ITPAJD'"
            )
        ).fetchone()
        version = conn.execute(
            text(
                "SELECT va.boe_bloque_id, va.texto FROM version_articulo va JOIN articulo a ON a.id = va.articulo_id JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'ITPAJD'"
            )
        ).fetchone()

    assert norma == (
        "ITPAJD",
        "BOE-A-1993-25359",
        "real_decreto_legislativo",
        "tributario",
        "ingestada",
    )
    assert articulo == ("7", "articulo")
    assert version == (
        "a7",
        "Artículo 7. Operaciones societarias.\nUno. Son operaciones societarias sujetas las previstas en esta norma.",
    )


def test_run_sync_does_not_fetch_remote_blocks_inside_transaction():
    from boe import run_sync

    class FakeResponse:
        def __init__(self, *, json_data=None, text_data=""):
            self._json_data = json_data
            self.text = text_data

        def raise_for_status(self):
            return None

        def json(self):
            return self._json_data

    class FakeClient:
        def __init__(self, engine):
            self.engine = engine
            self.transaction_states = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None):
            if "/texto/indice" in url or "/texto/bloque/" in url:
                self.transaction_states.append(self.engine.in_transaction)
            if url.endswith("/id/BOE-A-1993-25359/metadatos"):
                return FakeResponse(
                    json_data={
                        "data": [
                            {
                                "titulo": "Real Decreto Legislativo 1/1993",
                                "fecha_vigencia": "19930925",
                                "url_eli": "https://www.boe.es/eli/es/rdlg/1993/09/24/1",
                            }
                        ]
                    }
                )
            if url.endswith("/id/BOE-A-1993-25359/texto/indice"):
                return FakeResponse(
                    json_data={
                        "data": [
                            {
                                "bloque": [
                                    {
                                        "id": "a7",
                                        "titulo": "Artículo 7",
                                        "fecha_actualizacion": "20240101",
                                    }
                                ]
                            }
                        ]
                    }
                )
            if url.endswith("/id/BOE-A-1993-25359/texto/bloque/a7"):
                return FakeResponse(
                    text_data="""
                    <response>
                      <data>
                        <bloque id="a7" tipo="precepto" titulo="Artículo 7">
                          <version id_norma="BOE-A-1993-25359" fecha_publicacion="19930925" fecha_vigencia="19930925">
                            <p class="articulo">Artículo 7. Operaciones societarias.</p>
                          </version>
                        </bloque>
                      </data>
                    </response>
                    """
                )
            raise AssertionError(f"Unexpected URL requested: {url}")

    class FakeConnection:
        engine = type("DialectEngine", (), {"dialect": type("Dialect", (), {"name": "sqlite"})()})()

    class FakeBegin:
        def __init__(self, engine):
            self.engine = engine

        def __enter__(self):
            self.engine.in_transaction = True
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            self.engine.in_transaction = False
            return False

    class FakeEngine:
        def __init__(self):
            self.in_transaction = False
            self.dialect = type("Dialect", (), {"name": "sqlite"})()

        def begin(self):
            return FakeBegin(self)

    fake_engine = FakeEngine()
    fake_client = FakeClient(fake_engine)

    with patch("boe.httpx.Client", return_value=fake_client):
        with patch("boe.create_engine", return_value=fake_engine):
            with patch("boe.ensure_database_connection"):
                with patch("boe._ensure_schema"):
                    with patch("boe.upsert_norma"):
                        with patch("boe.upsert_articulo"):
                            with patch("boe.auto_link_materias"):
                                with patch("boe.auto_link_doctrina"):
                                    with patch("boe.log_sync"):
                                        with patch("boe.time.sleep"):
                                            run_sync(["ITPAJD"])

    assert fake_client.transaction_states == [False, False]


def test_auto_link_doctrina_materializes_documents_before_writes():
    from boe import auto_link_doctrina

    class FakeMappingsResult:
        def __init__(self, rows, conn):
            self._rows = rows
            self._conn = conn

        def __iter__(self):
            self._conn.iterating_docs = True
            try:
                yield from self._rows
            finally:
                self._conn.iterating_docs = False

        def all(self):
            return list(self._rows)

    class FakeConn:
        def __init__(self):
            self.iterating_docs = False
            self.insert_calls = 0

        def execute(self, statement, params=None):
            sql = str(statement)
            if "SELECT id, referencia, texto FROM documento_interpretativo" in sql:
                return type(
                    "Result",
                    (),
                    {
                        "mappings": lambda _self: FakeMappingsResult(
                            [{"id": 1, "referencia": "V0000-24", "texto": "LIVA 91"}],
                            self,
                        )
                    },
                )()
            if "INSERT INTO documento_articulo" in sql:
                if self.iterating_docs:
                    raise AssertionError("write attempted while docs cursor still open")
                self.insert_calls += 1
                return None
            raise AssertionError(f"Unexpected SQL: {sql}")

    conn = FakeConn()

    links = auto_link_doctrina(conn)

    assert links == 1
    assert conn.insert_calls == 1


def test_run_sync_skips_when_boe_lock_is_unavailable(monkeypatch):
    from boe import run_sync

    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
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

    monkeypatch.setattr("boe.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("boe.ensure_database_connection", lambda *args, **kwargs: None)
    monkeypatch.setattr("boe._ensure_schema", lambda conn: None)
    monkeypatch.setattr("boe.DEFAULT_NORMAS", {"LIVA": "BOE-A-1992-28740"})
    monkeypatch.setattr("boe.KNOWN_BOE_CODES", {"LIVA"})
    monkeypatch.setattr(
        "boe.httpx.Client",
        lambda *args, **kwargs: type(
            "Client",
            (),
            {"__enter__": lambda self: self, "__exit__": lambda self, exc_type, exc, tb: False},
        )(),
    )
    monkeypatch.setattr(
        "boe.fetch_metadata",
        lambda client, codigo, boe_id: NormaMetadata(
            codigo="LIVA",
            titulo="Ley 37/1992",
            boe_id="BOE-A-1992-28740",
            eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
            jurisdiccion="es",
            tipo_fuente="boe",
            tipo_documento="ley",
            ambito="tributario",
            estado_cobertura="ingestada",
            vigente_desde="1993-01-01",
        ),
    )
    @contextmanager
    def fake_hold_sync_lock(engine):
        yield False

    monkeypatch.setattr("boe._hold_sync_lock", fake_hold_sync_lock)
    monkeypatch.setattr(
        "boe.fetch_index",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fetch_index should not run without lock")),
    )

    run_sync(codigos=["LIVA"])

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT status, bloques_processed, articulos_upserted, error_msg FROM sync_log ORDER BY id DESC LIMIT 1")
        ).fetchone()

    assert row == ("partial", 0, 0, "BOE sync already in progress")


def test_hold_sync_lock_uses_autocommit_connection_for_postgres():
    class FakeResult:
        def __init__(self, value):
            self._value = value

        def scalar(self):
            return self._value

    class FakeConnection:
        def __init__(self):
            self.execution_options_calls = []
            self.execute_calls = []
            self.closed = False

        def execution_options(self, **kwargs):
            self.execution_options_calls.append(kwargs)
            return self

        def execute(self, statement, params):
            sql = str(statement)
            self.execute_calls.append((sql, params))
            if "pg_try_advisory_lock" in sql:
                return FakeResult(True)
            if "pg_advisory_unlock" in sql:
                return FakeResult(True)
            raise AssertionError(f"Unexpected SQL: {sql}")

        def close(self):
            self.closed = True

    class FakeEngine:
        def __init__(self, conn):
            self.dialect = type("Dialect", (), {"name": "postgresql"})()
            self._conn = conn

        def connect(self):
            return self._conn

    conn = FakeConnection()
    engine = FakeEngine(conn)

    with _hold_sync_lock(engine) as acquired:
        assert acquired is True

    assert conn.execution_options_calls == [{"isolation_level": "AUTOCOMMIT"}]
    assert conn.closed is True


def test_upsert_norma_inserts_record():
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
                    tipo_documento TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    estado_cobertura TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL
                )
                """
            )
        )

        upsert_norma(
            conn,
            NormaMetadata(
                codigo="LIVA",
                boe_id="BOE-A-1992-28740",
                titulo="Ley 37/1992",
                eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
                jurisdiccion="es",
                tipo_fuente="boe",
                tipo_documento="ley",
                ambito="tributario",
                estado_cobertura="ingestada",
                vigente_desde="1993-01-01",
            ),
        )

        row = conn.execute(
            text(
                "SELECT codigo, boe_id, tipo_documento, ambito, estado_cobertura FROM norma"
            )
        ).fetchone()

    assert row == ("LIVA", "BOE-A-1992-28740", "ley", "tributario", "ingestada")


def test_ensure_schema_and_upsert_norma_write_classification_fields():
    engine = create_engine("sqlite:///:memory:", future=True)
    payload = {
        "data": [
            {
                "titulo": "Ley 37/1992, de 28 de diciembre, del Impuesto sobre el Valor Anadido.",
                "fecha_vigencia": "19930101",
                "url_eli": "https://www.boe.es/eli/es/l/1992/12/28/37",
            }
        ]
    }

    with engine.begin() as conn:
        _ensure_schema(conn)
        upsert_norma(conn, parse_metadata("LIVA", "BOE-A-1992-28740", payload))

        row = conn.execute(
            text(
                "SELECT codigo, tipo_documento, ambito, estado_cobertura FROM norma WHERE codigo = 'LIVA'"
            )
        ).fetchone()

    assert row == ("LIVA", "ley", "tributario", "ingestada")


def test_parse_index_returns_blocks():
    payload = {
        "data": [
            {
                "bloque": [
                    {
                        "id": "a91",
                        "titulo": "Artículo 91",
                        "fecha_actualizacion": "20241221",
                    },
                    {
                        "id": "ti",
                        "titulo": "Título I",
                        "fecha_actualizacion": "19921229",
                    },
                ]
            }
        ]
    }

    blocks = parse_index(payload)

    assert blocks[0].id == "a91"
    assert blocks[0].titulo == "Artículo 91"


def test_parse_block_xml_extracts_real_text_shape():
    xml_text = """
    <response>
      <data>
        <bloque id="a91" tipo="precepto" titulo="Artículo 91">
          <version id_norma="BOE-A-1992-28740" fecha_publicacion="19921229" fecha_vigencia="19930101">
            <p class="articulo">Artículo 91. Tipos impositivos reducidos.</p>
            <p class="parrafo">Uno. Se aplicará el tipo del 6 por 100 a las operaciones siguientes:</p>
          </version>
        </bloque>
      </data>
    </response>
    """

    block = parse_block_xml("a91", xml_text)

    assert block == BloqueTexto(
        bloque_id="a91",
        tipo_bloque="precepto",
        numero="91",
        titulo="Artículo 91",
        tipo_articulo="articulo",
        texto="Artículo 91. Tipos impositivos reducidos.\nUno. Se aplicará el tipo del 6 por 100 a las operaciones siguientes:",
        vigente_desde="1993-01-01",
    )


def test_upsert_articulo_inserts_article_and_version():
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
                    tipo_documento TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    estado_cobertura TEXT NOT NULL,
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
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL,
                    vigente_hasta TEXT,
                    boe_bloque_id TEXT
                )
                """
            )
        )

        upsert_norma(
            conn,
            NormaMetadata(
                codigo="LIVA",
                boe_id="BOE-A-1992-28740",
                titulo="Ley 37/1992",
                eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
                jurisdiccion="es",
                tipo_fuente="boe",
                tipo_documento="ley",
                ambito="tributario",
                estado_cobertura="ingestada",
                vigente_desde="1993-01-01",
            ),
        )
        upsert_articulo(
            conn,
            "LIVA",
            BloqueTexto(
                bloque_id="a91",
                tipo_bloque="precepto",
                numero="91",
                titulo="Artículo 91",
                tipo_articulo="articulo",
                texto="Texto real",
                vigente_desde="1993-01-01",
            ),
        )

        articulo = conn.execute(text("SELECT numero, tipo FROM articulo")).fetchone()
        version = conn.execute(
            text("SELECT boe_bloque_id, texto FROM version_articulo")
        ).fetchone()

    assert articulo == ("91", "articulo")
    assert version == ("a91", "Texto real")


def test_upsert_articulo_replaces_seed_same_vigencia():
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
                    tipo_documento TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    estado_cobertura TEXT NOT NULL,
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
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL,
                    vigente_hasta TEXT,
                    boe_bloque_id TEXT
                )
                """
            )
        )

        upsert_norma(
            conn,
            NormaMetadata(
                codigo="LIVA",
                boe_id="BOE-A-1992-28740",
                titulo="Ley 37/1992",
                eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
                jurisdiccion="es",
                tipo_fuente="boe",
                tipo_documento="ley",
                ambito="tributario",
                estado_cobertura="ingestada",
                vigente_desde="1993-01-01",
            ),
        )
        conn.execute(
            text(
                """
                INSERT INTO articulo (norma_id, numero, titulo, tipo)
                SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
                SELECT id, 'Texto seed', '1993-01-01', NULL, 'seed-liva-91'
                FROM articulo WHERE numero = '91'
                """
            )
        )

        upsert_articulo(
            conn,
            "LIVA",
            BloqueTexto(
                bloque_id="a91",
                tipo_bloque="precepto",
                numero="91",
                titulo="Artículo 91",
                tipo_articulo="articulo",
                texto="Texto BOE real",
                vigente_desde="1993-01-01",
            ),
        )

        rows = conn.execute(
            text("SELECT boe_bloque_id, texto FROM version_articulo")
        ).fetchall()

    assert rows == [("a91", "Texto BOE real")]


def test_run_once_flag_accepts_argparse():
    """Verify --run-once flag is accepted by the worker CLI without error."""
    workers_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "boe.py", "--help"],
        capture_output=True,
        text=True,
        cwd=workers_dir,
        env={**__import__("os").environ, "DATABASE_URL": "sqlite:///:memory:"},
    )
    assert result.returncode == 0
    assert "--run-once" in result.stdout
    assert "--interval" in result.stdout


def test_run_sync_returns_dict_with_bloques_and_articulos():
    """Verify run_sync returns a dict with separate bloques and articulos counts."""
    from boe import run_sync
    import inspect

    sig = inspect.signature(run_sync)
    assert sig.return_annotation == dict[str, int]


def _setup_link_test_db():
    """Create tables and seed minimal data for auto-linking tests."""
    eng = create_engine("sqlite:///:memory:", future=True)
    with eng.begin() as c:
        c.execute(
            text("""
            CREATE TABLE norma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL,
                boe_id TEXT UNIQUE NOT NULL, eli_uri TEXT UNIQUE,
                jurisdiccion TEXT NOT NULL, tipo_fuente TEXT NOT NULL,
                tipo_documento TEXT NOT NULL, ambito TEXT NOT NULL,
                estado_cobertura TEXT NOT NULL, vigente_desde TEXT NOT NULL
            )
        """)
        )
        c.execute(
            text("""
            CREATE TABLE articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT, norma_id INTEGER NOT NULL,
                numero TEXT NOT NULL, titulo TEXT, tipo TEXT NOT NULL,
                UNIQUE (norma_id, numero)
            )
        """)
        )
        c.execute(
            text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT, articulo_id INTEGER NOT NULL,
                texto TEXT NOT NULL, vigente_desde TEXT NOT NULL,
                vigente_hasta TEXT, boe_bloque_id TEXT
            )
        """)
        )
        c.execute(
            text("""
            CREATE TABLE materia (
                id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL,
                etiqueta TEXT NOT NULL
            )
        """)
        )
        c.execute(
            text("""
            CREATE TABLE articulo_materia (
                articulo_id INTEGER NOT NULL REFERENCES articulo(id),
                materia_id INTEGER NOT NULL REFERENCES materia(id),
                relevancia INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (articulo_id, materia_id)
            )
        """)
        )
        c.execute(
            text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_documento TEXT NOT NULL,
                organismo_emisor TEXT NOT NULL, jurisdiccion TEXT NOT NULL,
                tipo_fuente TEXT NOT NULL, ambito TEXT NOT NULL,
                referencia TEXT UNIQUE NOT NULL, fecha TEXT NOT NULL,
                titulo TEXT, texto TEXT NOT NULL, url_fuente TEXT
            )
        """)
        )
        c.execute(
            text("""
            CREATE TABLE documento_articulo (
                documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
                articulo_id INTEGER NOT NULL REFERENCES articulo(id),
                metodo_enlace TEXT NOT NULL, confianza_enlace REAL NOT NULL,
                nota TEXT, PRIMARY KEY (documento_id, articulo_id)
            )
        """)
        )
        # Seed norma + article
        c.execute(
            text(
                "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) "
                "VALUES ('LIVA', 'Ley IVA', 'BOE-A-1992-28740', NULL, 'es', 'boe', 'ley', 'tributario', 'ingestada', '1993-01-01')"
            )
        )
        c.execute(
            text(
                "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) "
                "VALUES ('LIS', 'Ley IS', 'BOE-A-2014-12328', NULL, 'es', 'boe', 'ley', 'tributario', 'ingestada', '2015-01-01')"
            )
        )
        c.execute(
            text(
                "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) "
                "VALUES ('LGT', 'Ley General Tributaria', 'BOE-A-2003-23186', NULL, 'es', 'boe', 'ley', 'tributario', 'ingestada', '2004-01-01')"
            )
        )
        c.execute(
            text(
                "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde) "
                "VALUES ('LIRPF', 'Ley IRPF', 'BOE-A-2006-20764', NULL, 'es', 'boe', 'ley', 'tributario', 'ingestada', '2007-01-01')"
            )
        )
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '91', 'Tipos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'"
            )
        )
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '89', 'Rectificacion de cuotas impositivas repercutidas', 'articulo' FROM norma WHERE codigo = 'LIVA'"
            )
        )
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '15', 'Reglas de valoracion', 'articulo' FROM norma WHERE codigo = 'LIS'"
            )
        )
        c.execute(
            text(
                "INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id) "
                "SELECT a.id, :texto, '1993-01-01', NULL, 'a91' "
                "FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'LIVA' AND a.numero = '91'"
            ),
            {
                "texto": "Artículo 91. Tipos impositivos reducidos.\nUno. Se aplicará el tipo del 6 por 100."
            },
        )
        c.execute(
            text(
                "INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id) "
                "SELECT a.id, :texto, '1993-01-01', NULL, 'a89' "
                "FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'LIVA' AND a.numero = '89'"
            ),
            {
                "texto": "Artículo 89. Rectificación de las cuotas impositivas repercutidas."
            },
        )
        c.execute(
            text(
                "INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id) "
                "SELECT a.id, :texto, '2015-01-01', NULL, 'a15' "
                "FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'LIS' AND a.numero = '15'"
            ),
            {"texto": "Artículo 15. Reglas de valoracion en operaciones societarias."},
        )
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '104', 'Exenciones', 'articulo' FROM norma WHERE codigo = 'LIVA'"
            )
        )
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '8', 'Hechos imponibles', 'articulo' FROM norma WHERE codigo = 'LIVA'"
            )
        )
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '111', 'Infracciones tributarias', 'articulo' FROM norma WHERE codigo = 'LGT'"
            )
        )
        c.execute(
            text(
                "INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id) "
                "SELECT a.id, :texto, '2004-01-01', NULL, 'a111' "
                "FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'LGT' AND a.numero = '111'"
            ),
            {"texto": "Artículo 111. Infracciones tributarias."},
        )
    return eng


def test_auto_link_materias_creates_link():
    """Verify auto_link_materias links articles to materias when keywords match."""
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO materia (slug, etiqueta) VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')"
            )
        )
        links = auto_link_materias(c)
        row = c.execute(
            text(
                "SELECT am.relevancia, m.slug FROM articulo_materia am JOIN materia m ON m.id = am.materia_id"
            )
        ).fetchone()

    assert links >= 1
    assert row == (2, "tipo-reducido-iva")


def test_auto_link_doctrina_upgrades_confidence_when_better_match_found():
    """Verify that a better match (1.0 > 0.85) upgrades the existing link.

    This is the production bug: links created at 0.85 were never upgraded
    when explicit 1.0 patterns were added later.
    """
    eng = _setup_link_test_db()
    with eng.begin() as c:
        # Create a document and seed a link at 0.85 (simulating old contextual match)
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('resolucion_teac', 'TEAC', 'es', 'teac', 'fiscal', 'UPGRADE-TEST', '2026-04-12', 'Test', "
                "'Resolucion sobre LIVA 91 en materia de IVA.', NULL)"
            )
        )
        c.execute(
            text(
                "INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota) "
                "SELECT di.id, a.id, 'contextual_fallback', 0.85, 'Old contextual match' "
                "FROM documento_interpretativo di, articulo a JOIN norma n ON n.id = a.norma_id "
                "WHERE di.referencia = 'UPGRADE-TEST' AND n.codigo = 'LIVA' AND a.numero = '91'"
            )
        )
        # Now run auto_link_doctrina which should detect LIVA 91 at 1.0
        auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT da.confianza_enlace, da.metodo_enlace, da.nota "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "JOIN documento_interpretativo di ON di.id = da.documento_id "
                "WHERE di.referencia = 'UPGRADE-TEST' AND n.codigo = 'LIVA' AND a.numero = '91'"
            )
        ).fetchone()

    assert row[0] == 1.0  # confidence upgraded
    assert row[1] == "auto_link_exact"
    assert row[2] == "Referencia auto-detectada: LIVA art. 91"


def test_auto_link_doctrina_creates_strong_links_for_explicit_norma_and_article():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0000-26', '2026-01-15', 'Test', "
                "'Consulta sobre LIVA 91 y sobre el articulo 15 de la LIS.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        rows = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "ORDER BY n.codigo, a.numero"
            )
        ).fetchall()

    assert links == 2
    assert rows == [("LIS", "15", 1.0), ("LIVA", "91", 1.0)]


def test_auto_link_doctrina_uses_single_norma_context_for_article_reference():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0001-26', '2026-01-15', 'Test', "
                "'Consulta sobre el IVA. De acuerdo con el articulo 91, procede aplicar el tipo reducido.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = 'V0001-26')"
            )
        ).fetchone()

    assert links == 1
    assert row == ("LIVA", "91", 0.85)


def test_auto_link_doctrina_skips_ambiguous_article_reference():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0002-26', '2026-01-15', 'Test', "
                "'De acuerdo con el articulo 91, la operacion debe analizarse segun sus hechos.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        count = c.execute(text("SELECT COUNT(*) FROM documento_articulo")).scalar_one()

    assert links == 0
    assert count == 0


def test_auto_link_doctrina_matches_law_reference_with_subarticle_suffix():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('resolucion_teac', 'TEAC', 'es', 'teac', 'fiscal', '00/01362/2024/00/00', '2026-02-27', 'Test', "
                "'El articulo 89.Cinco b) de la Ley 37/1992 permite regularizar la situacion tributaria.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = '00/01362/2024/00/00')"
            )
        ).fetchone()

    assert links == 1
    assert row == ("LIVA", "89", 1.0)


def test_auto_link_doctrina_matches_art_norma_without_de_la():
    """Pattern: art. <numero> <NORMA> should resolve with confidence 1.0.

    Real production case: 'art. 111 LGT' in TEAC resolution 00/05861/2025/00/00.
    """
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('resolucion_teac', 'TEAC', 'es', 'teac', 'fiscal', '00/05861/2025/00/00', '2026-02-27', 'Test', "
                "'Resolucion sobre el art. 111 LGT en materia de sanciones.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = '00/05861/2025/00/00')"
            )
        ).fetchone()

    assert links == 1
    assert row == ("LGT", "111", 1.0)


def test_auto_link_doctrina_art_norma_variants():
    """Verify art. 91 LIVA, Art. 91 LIVA, ART 91 LGT all resolve to 1.0."""
    from boe import _extract_doctrina_refs

    refs = _extract_doctrina_refs("Resolucion sobre art. 91 LIVA en materia de IVA.")
    assert ("LIVA", "91", 1.0, "auto_link_exact") in refs

    refs = _extract_doctrina_refs("Conforme Art. 15 LIS se determina la base.")
    assert ("LIS", "15", 1.0, "auto_link_exact") in refs

    refs = _extract_doctrina_refs("Aplicable el ART 50 LGT al presente caso.")
    assert ("LGT", "50", 1.0, "auto_link_exact") in refs


def test_auto_link_doctrina_matches_articulo_ley_del_iva():
    """Pattern: artículo <numero>.<apartado> de la Ley del IVA -> 1.0.

    Real production case: 'artículo 104.Tres.4º de la Ley del IVA' in
    TEAC resolution 00/01454/2023/00/00.
    """
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('resolucion_teac', 'TEAC', 'es', 'teac', 'fiscal', '00/01454/2023/00/00', '2026-02-27', 'Test', "
                "'Aplicacion del articulo 104.Tres.4º de la Ley del IVA a las operaciones descritas.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = '00/01454/2023/00/00')"
            )
        ).fetchone()

    assert links == 1
    assert row == ("LIVA", "104", 1.0)


def test_auto_link_doctrina_matches_law_reference_with_numeric_subarticle_suffix():
    """Pattern: articulo 45.1.a) de la Ley 35/2006 del IRPF -> article 45.

    Real production case from seeded DGT doctrine V2509-20.
    """
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO articulo (norma_id, numero, titulo, tipo) "
                "SELECT id, '45', 'Exenciones', 'articulo' FROM norma WHERE codigo = 'LIRPF'"
            )
        )
        c.execute(
            text(
                "INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id) "
                "SELECT a.id, :texto, '2007-01-01', NULL, 'a45' "
                "FROM articulo a JOIN norma n ON n.id = a.norma_id WHERE n.codigo = 'LIRPF' AND a.numero = '45'"
            ),
            {"texto": "Artículo 45. Exenciones aplicables en el IRPF."},
        )
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V2509-20', '2021-11-12', 'Test', "
                "'La exencion prevista en el articulo 45.1.a) de la Ley 35/2006 del IRPF requiere reinversion.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = 'V2509-20')"
            )
        ).fetchone()

    assert links == 1
    assert row == ("LIRPF", "45", 1.0)


def test_auto_link_doctrina_matches_ley_del_iva_separate_article():
    """Pattern: Ley del IVA mentioned separately from article reference -> 1.0.

    Real production case: 'a efectos de la Ley del IVA ... artículo 8.Dos.3º'
    in TEAC resolution 00/01454/2023/00/00.
    """
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('resolucion_teac', 'TEAC', 'es', 'teac', 'fiscal', '00/01454/2023/00/01', '2026-02-27', 'Test', "
                "'A efectos de la Ley del IVA, lo dispuesto en el articulo 8.Dos.3º resulta aplicable.', NULL)"
            )
        )
        links = auto_link_doctrina(c)
        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = '00/01454/2023/00/01')"
            )
        ).fetchone()

    assert links == 1
    assert row == ("LIVA", "8", 1.0)


def test_ensure_schema_creates_sync_log_when_missing():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL,
                    vigente_hasta TEXT,
                    boe_bloque_id TEXT
                )
                """
            )
        )

        _ensure_schema(conn)

        row = conn.execute(
            text(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'sync_log'
                """
            )
        ).fetchone()

    assert row == ("sync_log",)


def test_ensure_schema_creates_core_tables_on_empty_db():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _ensure_schema(conn)

        rows = conn.execute(
            text(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            )
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert {"norma", "articulo", "version_articulo", "sync_log"} <= table_names


def test_ensure_schema_upgrades_legacy_norma_before_upsert():
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
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL,
                    vigente_hasta TEXT,
                    boe_bloque_id TEXT
                )
                """
            )
        )

        _ensure_schema(conn)
        upsert_norma(
            conn,
            NormaMetadata(
                codigo="LIVA",
                boe_id="BOE-A-1992-28740",
                titulo="Ley 37/1992",
                eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
                jurisdiccion="es",
                tipo_fuente="boe",
                tipo_documento="ley",
                ambito="tributario",
                estado_cobertura="ingestada",
                vigente_desde="1993-01-01",
            ),
        )

        row = conn.execute(
            text(
                "SELECT codigo, tipo_documento, ambito, estado_cobertura FROM norma WHERE codigo = 'LIVA'"
            )
        ).fetchone()

    assert row == ("LIVA", "ley", "tributario", "ingestada")


def test_ensure_schema_backfills_existing_legacy_norma_rows():
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
                INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
                VALUES ('LGT', 'Ley 58/2003', 'BOE-A-2003-23186', NULL, 'es', 'boe', 'fiscal', '2004-01-01')
                """
            )
        )

        _ensure_schema(conn)

        row = conn.execute(
            text(
                """
                SELECT codigo, tipo_documento, ambito, estado_cobertura
                FROM norma
                WHERE codigo = 'LGT'
                """
            )
        ).fetchone()

    assert row == ("LGT", "ley", "tributario", "ingestada")


def test_ensure_schema_skips_norma_backfill_after_initial_upgrade():
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
                INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
                VALUES ('LGT', 'Ley 58/2003', 'BOE-A-2003-23186', NULL, 'es', 'boe', 'fiscal', '2004-01-01')
                """
            )
        )

        _ensure_schema(conn)

        statements: list[str] = []

        def capture_sql(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture_sql)
        try:
            _ensure_schema(conn)
        finally:
            event.remove(engine, "before_cursor_execute", capture_sql)

    normalized = [statement.lower().strip() for statement in statements]
    assert not any(statement.startswith("update norma") for statement in normalized)


def test_ensure_sync_log_table_creates_log_table_independently():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        _ensure_sync_log_table(conn)
        row = conn.execute(
            text(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'sync_log'
                """
            )
        ).fetchone()

    assert row == ("sync_log",)


def test_run_sync_records_correct_worker_name_for_continuous_vs_cron(monkeypatch):
    """Verify BOE sync_log uses the provided worker_name, not a hardcoded one."""
    from boe import run_sync

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
                CREATE TABLE version_articulo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    articulo_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    vigente_desde TEXT NOT NULL,
                    vigente_hasta TEXT,
                    boe_bloque_id TEXT
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

    def handler(request: httpx.Request) -> httpx.Response:
        if "/metadatos" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "titulo": "Ley 37/1992",
                            "fecha_vigencia": "19930101",
                            "url_eli": "https://www.boe.es/eli/es/l/1992/12/28/37",
                        }
                    ]
                },
            )
        if "/texto/indice" in str(request.url):
            return httpx.Response(200, json={"data": [{"bloque": []}]})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr("boe.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        "boe.httpx.Client",
        lambda *args, **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            base_url="https://www.boe.es",
        ),
    )
    monkeypatch.setattr("boe.DEFAULT_NORMAS", {"LIVA": "BOE-A-1992-28740"})
    monkeypatch.setattr("boe.BOE_API_BASE", "https://www.boe.es")

    run_sync(codigos=["LIVA"])
    run_sync(codigos=["LIVA"], worker_name="cron-boe-daily")

    with engine.begin() as conn:
        workers = conn.execute(
            text("SELECT worker FROM sync_log ORDER BY id")
        ).fetchall()

    assert [w[0] for w in workers] == ["worker-boe", "cron-boe-daily"]


def test_run_sync_touches_heartbeat_during_long_boe_processing(monkeypatch):
    from boe import run_sync

    heartbeat_calls = []

    class FakeConnection:
        def execute(self, *args, **kwargs):
            return type("Result", (), {"scalar": lambda self: 0})()

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConnect(FakeBegin):
        pass

    class FakeDialect:
        name = "sqlite"

    class FakeEngine:
        dialect = FakeDialect()
        url = type("Url", (), {"host": "localhost"})()

        def begin(self):
            return FakeBegin()

        def connect(self):
            return FakeConnect()

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("boe.create_engine", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr("boe.httpx.Client", lambda *args, **kwargs: FakeClient())
    monkeypatch.setattr("boe.DEFAULT_NORMAS", {"LIVA": "BOE-A-1992-28740"})
    monkeypatch.setattr("boe.KNOWN_BOE_CODES", {"LIVA"})
    monkeypatch.setattr(
        "boe.fetch_metadata",
        lambda client, codigo, boe_id: NormaMetadata(
            codigo="LIVA",
            titulo="Ley 37/1992",
            boe_id="BOE-A-1992-28740",
            eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
            jurisdiccion="es",
            tipo_fuente="boe",
            tipo_documento="ley",
            ambito="tributario",
            estado_cobertura="ingestada",
            vigente_desde="1993-01-01",
        ),
    )
    monkeypatch.setattr(
        "boe.fetch_index",
        lambda client, boe_id: [type("Idx", (), {"id": "art1", "titulo": "Artículo 1"})()],
    )
    monkeypatch.setattr(
        "boe.fetch_block",
        lambda client, boe_id, block_id: BloqueTexto(
            bloque_id="art1",
            tipo_bloque="articulo",
            numero="1",
            titulo="Artículo 1",
            tipo_articulo="articulo",
            texto="texto",
            vigente_desde="1993-01-01",
        ),
    )
    monkeypatch.setattr("boe._ensure_schema", lambda conn: None)
    monkeypatch.setattr("boe.upsert_norma", lambda conn, metadata: None)
    monkeypatch.setattr("boe.upsert_articulo", lambda conn, codigo, bloque: None)
    monkeypatch.setattr("boe.auto_link_materias", lambda conn: None)
    monkeypatch.setattr("boe.auto_link_doctrina", lambda conn: None)
    monkeypatch.setattr("boe.log_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr("boe.touch_heartbeat", lambda: heartbeat_calls.append("touch"))
    monkeypatch.setattr("boe.time.sleep", lambda seconds: None)

    run_sync(codigos=["LIVA"])

    assert heartbeat_calls == ["touch"]
