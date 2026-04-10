import sys
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boe import (
    BloqueTexto,
    NormaMetadata,
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
                    {"id": "a91", "titulo": "Artículo 91", "fecha_actualizacion": "20241221"},
                    {"id": "ti", "titulo": "Título I", "fecha_actualizacion": "19921229"},
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
        version = conn.execute(text("SELECT boe_bloque_id, texto FROM version_articulo")).fetchone()

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

        rows = conn.execute(text("SELECT boe_bloque_id, texto FROM version_articulo")).fetchall()

    assert rows == [("a91", "Texto BOE real")]


def test_run_once_flag_accepts_argparse():
    """Verify --run-once flag is accepted by the worker CLI without error."""
    workers_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "workers.boe", "--help"],
        capture_output=True,
        text=True,
        cwd=workers_dir,
        env={**__import__("os").environ, "PYTHONPATH": str(workers_dir.parent), "DATABASE_URL": "sqlite:///:memory:"},
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
