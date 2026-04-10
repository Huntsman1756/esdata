import argparse
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import create_engine, text

BOE_API_BASE = os.getenv(
    "BOE_API_BASE",
    "https://www.boe.es/datosabiertos/api/legislacion-consolidada",
)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata",
)
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "3600"))

DEFAULT_NORMAS = {
    "LIVA": "BOE-A-1992-28740",
    "LIRPF": "BOE-A-2006-20764",
    "LIS": "BOE-A-2014-12328",
    "LGT": "BOE-A-2003-23186",
}


@dataclass
class NormaMetadata:
    codigo: str
    boe_id: str
    titulo: str
    eli_uri: str | None
    jurisdiccion: str
    tipo_fuente: str
    ambito: str
    vigente_desde: str


@dataclass
class BloqueIndex:
    id: str
    titulo: str
    fecha_actualizacion: str


@dataclass
class BloqueTexto:
    bloque_id: str
    tipo_bloque: str
    numero: str
    titulo: str
    tipo_articulo: str
    texto: str
    vigente_desde: str


def parse_metadata(codigo: str, boe_id: str, payload: dict) -> NormaMetadata:
    item = payload["data"][0]
    return NormaMetadata(
        codigo=codigo,
        boe_id=boe_id,
        titulo=item["titulo"],
        eli_uri=item.get("url_eli"),
        jurisdiccion="es",
        tipo_fuente="boe",
        ambito="fiscal",
        vigente_desde=_yyyymmdd_to_iso(item["fecha_vigencia"]),
    )


def parse_index(payload: dict) -> list[BloqueIndex]:
    return [
        BloqueIndex(
            id=item["id"],
            titulo=item.get("titulo", "").strip(),
            fecha_actualizacion=item.get("fecha_actualizacion", ""),
        )
        for item in payload["data"][0]["bloque"]
        if item.get("titulo")
    ]


def fetch_index(client: httpx.Client, boe_id: str) -> list[BloqueIndex]:
    response = client.get(f"{BOE_API_BASE}/id/{boe_id}/texto/indice", headers={"Accept": "application/json"})
    response.raise_for_status()
    return parse_index(response.json())


def parse_block_xml(block_id: str, xml_text: str) -> BloqueTexto:
    root = ET.fromstring(xml_text)
    bloque = root.find(".//bloque")
    version = root.find(".//version")
    if bloque is None or version is None:
        raise ValueError(f"Invalid BOE block payload for {block_id}")

    titulo = bloque.attrib.get("titulo", "").strip()
    tipo_articulo, numero = _infer_tipo_y_numero(titulo)
    parts = []
    for p in version.findall("p"):
        text_value = "".join(p.itertext()).strip()
        if text_value:
            parts.append(text_value)

    return BloqueTexto(
        bloque_id=block_id,
        tipo_bloque=bloque.attrib.get("tipo", ""),
        numero=numero,
        titulo=titulo,
        tipo_articulo=tipo_articulo,
        texto="\n".join(parts),
        vigente_desde=_yyyymmdd_to_iso(version.attrib["fecha_vigencia"]),
    )


def fetch_block(client: httpx.Client, boe_id: str, block_id: str) -> BloqueTexto:
    response = client.get(
        f"{BOE_API_BASE}/id/{boe_id}/texto/bloque/{block_id}",
        headers={"Accept": "application/xml"},
    )
    response.raise_for_status()
    return parse_block_xml(block_id, response.text)


def fetch_metadata(client: httpx.Client, codigo: str, boe_id: str) -> NormaMetadata:
    response = client.get(f"{BOE_API_BASE}/id/{boe_id}/metadatos", headers={"Accept": "application/json"})
    response.raise_for_status()
    return parse_metadata(codigo, boe_id, response.json())


def upsert_norma(conn, metadata: NormaMetadata) -> None:
    conn.execute(
        text(
            """
            INSERT INTO norma (codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, ambito, vigente_desde)
            VALUES (:codigo, :titulo, :boe_id, :eli_uri, :jurisdiccion, :tipo_fuente, :ambito, :vigente_desde)
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                boe_id = EXCLUDED.boe_id,
                eli_uri = EXCLUDED.eli_uri,
                jurisdiccion = EXCLUDED.jurisdiccion,
                tipo_fuente = EXCLUDED.tipo_fuente,
                ambito = EXCLUDED.ambito,
                vigente_desde = EXCLUDED.vigente_desde
            """
        ),
        metadata.__dict__,
    )


def upsert_articulo(conn, codigo: str, bloque: BloqueTexto) -> None:
    conn.execute(
        text(
            """
            INSERT INTO articulo (norma_id, numero, titulo, tipo)
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
        {"codigo": codigo, "numero": bloque.numero, "vigente_desde": bloque.vigente_desde},
    )

    updated = conn.execute(
        text(
            """
            UPDATE version_articulo
            SET texto = :texto,
                boe_bloque_id = :boe_bloque_id
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
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
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


def log_sync(conn, status: str, items_processed: int, error_msg: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        text(
            """
            INSERT INTO sync_log (worker, started_at, finished_at, status, items_processed, error_msg)
            VALUES (:worker, :started_at, :finished_at, :status, :items_processed, :error_msg)
            """
        ),
        {
            "worker": "worker-boe",
            "started_at": now,
            "finished_at": now,
            "status": status,
            "items_processed": items_processed,
            "error_msg": error_msg,
        },
    )


def run_sync(codigos: list[str] | None = None) -> int:
    target_codes = codigos or [code.strip() for code in os.getenv("BOE_LEGISLACION_NORMAS", "LIVA").split(",") if code.strip()]
    only_block_ids = [item.strip() for item in os.getenv("BOE_ONLY_BLOCK_IDS", "").split(",") if item.strip()]
    engine = create_engine(DATABASE_URL, future=True)
    processed = 0

    try:
        with httpx.Client(timeout=30.0) as client:
            with engine.begin() as conn:
                for codigo in target_codes:
                    boe_id = DEFAULT_NORMAS[codigo]
                    metadata = fetch_metadata(client, codigo, boe_id)
                    upsert_norma(conn, metadata)
                    for item in fetch_index(client, boe_id):
                        if not _is_supported_block(item.titulo):
                            continue
                        if only_block_ids and item.id not in only_block_ids:
                            continue
                        bloque = fetch_block(client, boe_id, item.id)
                        upsert_articulo(conn, codigo, bloque)
                        processed += 1
                log_sync(conn, "ok", processed)
        return processed
    except Exception as exc:
        with engine.begin() as conn:
            log_sync(conn, "error", processed, str(exc))
        raise


def _yyyymmdd_to_iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _infer_tipo_y_numero(titulo: str) -> tuple[str, str]:
    title = titulo.strip()
    if title.startswith("Artículo "):
        numero = title.replace("Artículo ", "", 1).split(".")[0].strip()
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
    return "otro", title


def _is_supported_block(titulo: str) -> bool:
    prefixes = (
        "Artículo ",
        "Disposición adicional ",
        "Disposición transitoria ",
        "Disposición final ",
        "Disposición derogatoria ",
    )
    return titulo.startswith(prefixes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BOE worker: sync consolidated legislation from BOE API")
    parser.add_argument("--run-once", action="store_true", help="Run a single sync cycle and exit")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles in continuous mode (default: {SYNC_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        total = run_sync()
        print(f"[run-once] Synced {total} bloques from BOE")
    else:
        print(f"Starting BOE worker in continuous mode (interval={interval}s)")
        while True:
            total = run_sync()
            print(f"Synced {total} bloques from BOE at {datetime.now(timezone.utc).isoformat()}")
            time.sleep(interval)
