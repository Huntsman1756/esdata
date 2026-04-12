import sys
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boe import (
    BloqueTexto,
    NormaMetadata,
    _ensure_sync_log_table,
    _ensure_schema,
    _schema_statements,
    auto_link_doctrina,
    auto_link_materias,
    parse_block_xml,
    parse_index,
    parse_metadata,
    upsert_articulo,
    upsert_norma,
)


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
        ambito="fiscal",
        vigente_desde="1993-01-01",
    )


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
                    ambito TEXT NOT NULL,
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
                ambito="fiscal",
                vigente_desde="1993-01-01",
            ),
        )

        row = conn.execute(text("SELECT codigo, boe_id, ambito FROM norma")).fetchone()

    assert row == ("LIVA", "BOE-A-1992-28740", "fiscal")


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

        upsert_norma(
            conn,
            NormaMetadata(
                codigo="LIVA",
                boe_id="BOE-A-1992-28740",
                titulo="Ley 37/1992",
                eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
                jurisdiccion="es",
                tipo_fuente="boe",
                ambito="fiscal",
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

        upsert_norma(
            conn,
            NormaMetadata(
                codigo="LIVA",
                boe_id="BOE-A-1992-28740",
                titulo="Ley 37/1992",
                eli_uri="https://www.boe.es/eli/es/l/1992/12/28/37",
                jurisdiccion="es",
                tipo_fuente="boe",
                ambito="fiscal",
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
                ambito TEXT NOT NULL, vigente_desde TEXT NOT NULL
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
                "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde) "
                "VALUES ('LIVA', 'Ley IVA', 'BOE-A-1992-28740', NULL, 'es', 'boe', 'fiscal', '1993-01-01')"
            )
        )
        c.execute(
            text(
                "INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde) "
                "VALUES ('LIS', 'Ley IS', 'BOE-A-2014-12328', NULL, 'es', 'boe', 'fiscal', '2015-01-01')"
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


def test_schema_statements_use_serial_ids_on_postgres():
    statements = _schema_statements("postgresql")
    assert "id SERIAL PRIMARY KEY" in statements[0]
    assert "id SERIAL PRIMARY KEY" in statements[-1]


def test_schema_statements_use_integer_ids_on_sqlite():
    statements = _schema_statements("sqlite")
    assert "id INTEGER PRIMARY KEY" in statements[0]
    assert "id INTEGER PRIMARY KEY" in statements[-1]


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
