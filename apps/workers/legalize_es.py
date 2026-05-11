#!/usr/bin/env python

import argparse
import os
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

_workers_dir = Path(__file__).resolve().parent
if str(_workers_dir) not in sys.path:
    sys.path.insert(0, str(_workers_dir))

from runtime import configure_logging, get_database_url, ensure_database_connection

DATABASE_URL = get_database_url()
logger = configure_logging("worker-legalize-es")


ARTICLE_RE = re.compile(r"^Articulo\s+(\d+)\.\s*$", re.IGNORECASE)


def parse_markdown_norma(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in content.splitlines()]

    title = lines[0].lstrip("# ").strip()
    codigo = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("Codigo:"))
    vigente_desde = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("Fecha version:"))

    articulos: list[dict] = []
    current_numero = None
    current_text: list[str] = []

    for line in lines:
        match = ARTICLE_RE.match(line.strip())
        if match:
            if current_numero is not None:
                articulos.append(
                    {
                        "numero": current_numero,
                        "texto": " ".join(part for part in current_text if part).strip(),
                        "vigente_desde": vigente_desde,
                    }
                )
            current_numero = match.group(1)
            current_text = []
            continue

        if current_numero is not None:
            current_text.append(line.strip())

    if current_numero is not None:
        articulos.append(
            {
                "numero": current_numero,
                "texto": " ".join(part for part in current_text if part).strip(),
                "vigente_desde": vigente_desde,
            }
        )

    return {
        "codigo": codigo,
        "titulo": title,
        "tipo_fuente": "legalize_es",
        "tipo_documento": "ley",
        "ambito": "civil",
        "estado_cobertura": "ingestada",
        "vigente_desde": vigente_desde,
        "source_path": str(path),
        "articulos": articulos,
    }


def _upsert_norma(conn, parsed: dict) -> tuple[int, int]:
    row = conn.execute(
        text("SELECT id FROM norma WHERE codigo = :codigo"),
        {"codigo": parsed["codigo"]},
    ).first()
    if row:
        return row[0], 0

    result = conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
                tipo_documento, ambito, estado_cobertura, vigente_desde
            )
            VALUES (
                :codigo, :titulo, :boe_id, :eli_uri, 'es', :tipo_fuente,
                :tipo_documento, :ambito, :estado_cobertura, :vigente_desde
            )
            """
        ),
        {
            "codigo": parsed["codigo"],
            "titulo": parsed["titulo"],
            "boe_id": parsed["source_path"],
            "eli_uri": parsed["source_path"],
            "tipo_fuente": parsed["tipo_fuente"],
            "tipo_documento": parsed["tipo_documento"],
            "ambito": parsed["ambito"],
            "estado_cobertura": parsed["estado_cobertura"],
            "vigente_desde": parsed["vigente_desde"],
        },
    )
    norma_id = result.lastrowid
    return norma_id, 1


def _upsert_articulo(conn, norma_id: int, numero: str) -> tuple[int, int]:
    row = conn.execute(
        text("SELECT id FROM articulo WHERE norma_id = :norma_id AND numero = :numero"),
        {"norma_id": norma_id, "numero": numero},
    ).first()
    if row:
        return row[0], 0

    result = conn.execute(
        text(
            """
            INSERT INTO articulo (norma_id, numero, titulo, tipo)
            VALUES (:norma_id, :numero, NULL, 'articulo')
            """
        ),
        {"norma_id": norma_id, "numero": numero},
    )
    return result.lastrowid, 1


def _upsert_version_articulo(conn, articulo_id: int, texto_articulo: str, vigente_desde: str) -> int:
    row = conn.execute(
        text(
            """
            SELECT id FROM version_articulo
            WHERE articulo_id = :articulo_id AND vigente_desde = :vigente_desde
            """
        ),
        {"articulo_id": articulo_id, "vigente_desde": vigente_desde},
    ).first()
    if row:
        return 0

    conn.execute(
        text(
            """
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            VALUES (:articulo_id, :texto, :vigente_desde, NULL, NULL)
            """
        ),
        {"articulo_id": articulo_id, "texto": texto_articulo, "vigente_desde": vigente_desde},
    )
    return 1


def run_sync(engine, fixture_paths: list[Path]):
    normas_upserted = 0
    articulos_upserted = 0
    versiones_upserted = 0

    with engine.begin() as conn:
        for path in fixture_paths:
            parsed = parse_markdown_norma(Path(path))
            norma_id, norma_inserted = _upsert_norma(conn, parsed)
            normas_upserted += norma_inserted

            for articulo in parsed["articulos"]:
                articulo_id, articulo_inserted = _upsert_articulo(conn, norma_id, articulo["numero"])
                articulos_upserted += articulo_inserted
                versiones_upserted += _upsert_version_articulo(
                    conn,
                    articulo_id,
                    articulo["texto"],
                    articulo["vigente_desde"],
                )

    logger.info(
        "legalize-es sync complete: %s normas, %s articulos, %s versiones",
        normas_upserted,
        articulos_upserted,
        versiones_upserted,
    )
    return {
        "normas_upserted": normas_upserted,
        "articulos_upserted": articulos_upserted,
        "versiones_upserted": versiones_upserted,
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest local legalize-es markdown fixtures")
    parser.add_argument("--db-url", help="Database URL")
    parser.add_argument("--fixture", action="append", default=[], help="Path to markdown fixture")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL", DATABASE_URL)
    fixture_paths = [Path(item) for item in args.fixture]
    engine = create_engine(db_url)
    ensure_database_connection(engine)
    run_sync(engine, fixture_paths=fixture_paths)


if __name__ == "__main__":
    main()
