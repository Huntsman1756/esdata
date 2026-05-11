"""Worker para Ley 22/2014 de Entidades de Capital Riesgo (LECR).

Ingesta la normativa LECR desde BOE API, parsea articulos y
los almacena en las tablas norma/articulo/version_articulo con
regulacion_relacionada='lecr'.
"""

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime import get_database_url, get_interval_seconds, handle_worker_failure, ensure_database_connection

logger = logging.getLogger(__name__)

BOE_API_BASE = os.getenv(
    "BOE_API_BASE",
    "https://www.boe.es/datosabiertos/api/legislacion-consolidada",
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

LECR_NORMA = {
    "codigo": "LECR_222014",
    "boe_id": "BOE-A-2014-11230",
    "titulo": "Ley 22/2014, de 12 de noviembre, de Entidades de Capital Riesgo",
    "eli_uri": "https://www.boe.es/eli/es/ley/2014/11/12/22",
    "jurisdiccion": "es",
    "tipo_fuente": "boe",
    "tipo_documento": "ley",
    "ambito": "capital_riesgo",
    "estado_cobertura": "ingestada",
}


@dataclass
class BloqueTexto:
    bloque_id: str
    tipo_bloque: str
    numero: str
    titulo: str
    tipo_articulo: str
    texto: str
    vigente_desde: str


def parse_boe_chunk(chunk_text: str) -> BloqueTexto:
    """Parse a BOE XML chunk into a BloqueTexto."""
    from xml.etree import ElementTree as ET

    root = ET.fromstring(chunk_text)
    lines = []
    for p in root.findall(".//p"):
        text_value = "".join(p.itertext()).strip()
        if text_value:
            lines.append(text_value)

    titulo = root.attrib.get("titulo", "").strip()
    tipo_articulo, numero = _infer_tipo_y_numero(titulo)

    fecha = root.attrib.get("vigencia", "")
    if fecha:
        vigente_desde = fecha
    else:
        vigente_desde = "2014-11-13"

    return BloqueTexto(
        bloque_id=root.attrib.get("id", ""),
        tipo_bloque=root.attrib.get("tipo", ""),
        numero=numero,
        titulo=titulo,
        tipo_articulo=tipo_articulo,
        texto="\n".join(lines),
        vigente_desde=vigente_desde,
    )


def _infer_tipo_y_numero(titulo: str) -> tuple[str, str]:
    title = titulo.strip()
    if title.startswith("Artículo "):
        numero = title.replace("Artículo ", "", 1).split(".")[0].strip()
        return "articulo", numero
    if title.startswith("Articulo "):
        numero = title.replace("Articulo ", "", 1).split(".")[0].strip()
        return "articulo", numero
    if title.startswith("Disposición adicional "):
        numero = title.replace("Disposición adicional ", "", 1).split(".")[0].strip()
        return "disposicion_adicional", numero
    if title.startswith("Disposición transitoria "):
        numero = title.replace("Disposición transitoria ", "", 1).split(".")[0].strip()
        return "disposicion_transitoria", numero
    if title.startswith("Disposición final "):
        numero = title.replace("Disposición final ", "", 1).split(".")[0].strip()
        return "disposicion_final", numero
    if title.startswith("Disposición derogatoria "):
        numero = title.replace("Disposición derogatoria ", "", 1).split(".")[0].strip()
        return "disposicion_derogatoria", numero
    if title.startswith("Disposición inicial "):
        numero = title.replace("Disposición inicial ", "", 1).split(".")[0].strip()
        return "disposicion_inicial", numero
    if title.startswith("Sección "):
        return "seccion", titulo
    if title.startswith("Capítulo "):
        return "capitulo", titulo
    return "otro", titulo


def _is_supported_block(titulo: str) -> bool:
    prefixes = (
        "Artículo ",
        "Articulo ",
        "Disposición adicional ",
        "Disposición transitoria ",
        "Disposición final ",
        "Disposición derogatoria ",
        "Disposición inicial ",
        "Sección ",
        "Capítulo ",
    )
    return titulo.startswith(prefixes)


def _ensure_sync_log_table(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS sync_log (
                id SERIAL PRIMARY KEY,
                worker TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ,
                status TEXT NOT NULL,
                bloques_processed INTEGER,
                articulos_upserted INTEGER,
                documentos_processed INTEGER,
                documentos_upserted INTEGER,
                error_msg TEXT,
                rows_processed INTEGER,
                errors INTEGER DEFAULT 0,
                duration_ms INTEGER
            )
            """
        )
    )


def log_sync(
    conn,
    worker: str,
    status: str,
    bloques: int = 0,
    articulos: int = 0,
    documentos_processed: int = 0,
    documentos_upserted: int = 0,
    error_msg: str | None = None,
    started_at: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    effective_started_at = started_at or now
    duration_ms = max(0, int((datetime.fromisoformat(now) - datetime.fromisoformat(effective_started_at)).total_seconds() * 1000))
    _ensure_sync_log_table(conn)
    conn.execute(
        text(
            """
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted,
                error_msg, rows_processed, errors, duration_ms
            )
            VALUES (
                :worker, :started_at, :finished_at, :status,
                :bloques_processed, :articulos_upserted,
                :documentos_processed, :documentos_upserted,
                :error_msg, :rows_processed, :errors, :duration_ms
            )
            """
        ),
        {
            "worker": worker,
            "started_at": effective_started_at,
            "finished_at": now,
            "status": status,
            "bloques_processed": bloques,
            "articulos_upserted": articulos,
            "documentos_processed": documentos_processed,
            "documentos_upserted": documentos_upserted,
            "error_msg": error_msg,
            "rows_processed": max(bloques, articulos, documentos_processed, documentos_upserted),
            "errors": 0 if not error_msg else 1,
            "duration_ms": duration_ms,
        },
    )


def upsert_lecr_norma(conn) -> None:
    """Upsert the LECR norma record."""
    conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion,
                tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde
            )
            VALUES (
                :codigo, :titulo, :boe_id, :eli_uri, :jurisdiccion,
                :tipo_fuente, :tipo_documento, :ambito, :estado_cobertura, :vigente_desde
            )
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                boe_id = EXCLUDED.boe_id,
                eli_uri = EXCLUDED.eli_uri,
                jurisdiccion = EXCLUDED.jurisdiccion,
                tipo_fuente = EXCLUDED.tipo_fuente,
                tipo_documento = EXCLUDED.tipo_documento,
                ambito = EXCLUDED.ambito,
                estado_cobertura = EXCLUDED.estado_cobertura,
                vigente_desde = EXCLUDED.vigente_desde
            """
        ),
        {**LECR_NORMA, "vigente_desde": "2014-11-13"},
    )


def upsert_articulo(conn, codigo: str, bloque: BloqueTexto) -> None:
    conn.execute(
        text(
            """
            INSERT INTO articulo(norma_id, numero, titulo, tipo)
            SELECT id, :numero, :titulo, :tipo
            FROM norma
            WHERE codigo = :codigo
            ON CONFLICT (norma_id, numero) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "titulo": bloque.titulo,
            "tipo": bloque.tipo_articulo,
        },
    )

    conn.execute(
        text(
            """
            UPDATE version_articulo
            SET vigente_hasta = CASE
                WHEN vigente_hasta IS NULL AND vigente_desde < :vigente_desde THEN :vigente_desde
                ELSE vigente_hasta
            END
            WHERE articulo_id = (
                SELECT a.id
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo AND a.numero = :numero
            )
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "vigente_desde": bloque.vigente_desde,
        },
    )

    updated = conn.execute(
        text(
            """
            UPDATE version_articulo
            SET texto = :texto, boe_bloque_id = :boe_bloque_id
            WHERE articulo_id = (
                SELECT a.id
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo AND a.numero = :numero
            )
              AND vigente_desde = :vigente_desde
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "texto": bloque.texto,
            "vigente_desde": bloque.vigente_desde,
            "boe_bloque_id": bloque.bloque_id,
        },
    )

    if updated.rowcount:
        return

    conn.execute(
        text(
            """
            INSERT INTO version_articulo(articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT a.id, :texto, :vigente_desde, NULL, :boe_bloque_id
            FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE n.codigo = :codigo
              AND a.numero = :numero
              AND NOT EXISTS (
                  SELECT 1
                  FROM version_articulo va
                  WHERE va.articulo_id = a.id
                    AND va.vigente_desde = :vigente_desde
                    AND va.boe_bloque_id = :boe_bloque_id
              )
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "texto": bloque.texto,
            "vigente_desde": bloque.vigente_desde,
            "boe_bloque_id": bloque.bloque_id,
        },
    )


def run_sync(
    worker_name: str = "worker-lecr",
) -> dict[str, int]:
    """Run LECR sync: parse BOE XML chunks for Ley 22/2014."""
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    bloques_fetched = 0
    articulos_upserted = 0
    sync_start = datetime.now(timezone.utc).isoformat()

    try:
        with httpx.Client(timeout=30.0) as client:
            with engine.begin() as conn:
                upsert_lecr_norma(conn)

                # Fetch BOE consolidated text for Ley 22/2014
                boe_id = "BOE-A-2014-11230"
                url = f"{BOE_API_BASE}/{boe_id}.xml"
                response = client.get(url)
                if response.status_code == 404:
                    print(f"  [WARN] {boe_id} not found in BOE API, skipping")
                    log_sync(
                        conn, worker_name, "skipped",
                        started_at=sync_start,
                    )
                    return {"bloques": 0, "articulos": 0}
                response.raise_for_status()

                # Parse XML and extract chunks
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.text)

                for chunk in root.findall(".//chunk"):
                    titulo = chunk.attrib.get("titulo", "").strip()
                    if not titulo or not _is_supported_block(titulo):
                        continue

                    try:
                        bloque = parse_boe_chunk(ET.tostring(chunk, encoding="unicode"))
                        upsert_articulo(conn, "LECR_222014", bloque)
                        bloques_fetched += 1
                        articulos_upserted += 1
                    except Exception as e:
                        print(f"  [WARN] Error parsing chunk {chunk.attrib.get('id', '?')}: {e}")

                log_sync(
                    conn,
                    worker_name,
                    "ok",
                    bloques=bloques_fetched,
                    articulos=articulos_upserted,
                    started_at=sync_start,
                )
        return {"bloques": bloques_fetched, "articulos": articulos_upserted}
    except Exception as exc:
        entity_id = "ley222014_lecr"
        if not handle_worker_failure(engine, "ley222014_lecr", entity_id, "sync_entity", exc):
            logger.warning("Entity ley222014_lecr moved to dead-letter")
            return {"bloques": 0, "articulos": 0}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                bloques=bloques_fetched,
                articulos=articulos_upserted,
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LECR worker: sync Ley 22/2014 from BOE"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("lecr")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-lecr-weekly")
        print(
            f"[run-once] Bloques: {result['bloques']}, Artículos: {result['articulos']}"
        )
    else:
        print(f"Starting LECR worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(timezone.utc).isoformat()}"
            )
            time.sleep(interval)
