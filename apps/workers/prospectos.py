"""Worker para Prospectos ETI, AIFMD y UCITS (Reglamentos y Directivas UE).

Ingesta normativa desde EUR-Lex/BOE, parsea articulos y los almacena en las
tablas norma/articulo/version_articulo con regulacion_relacionada adecuada:
- prospectos_eti: Reglamento (UE) 2017/1129
- aifmd: Directiva 2011/61/UE
- ucits: Directiva 2009/65/CE

Usage:
    python prospectos.py --run-once --domain prospectos
    python prospectos.py --run-once --domain aifmd
    python prospectos.py --run-once --domain ucits
    python prospectos.py --run-once --domain all
"""

import argparse
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

EURLEX_BASE = os.getenv(
    "EURLEX_BASE",
    "https://eur-lex.europa.eu",
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# Reglamento (UE) 2017/1129 de prospectos — CELEX:32017R1129
PROSPECTOS_NORMA = {
    "codigo": "PROSPECTOS_2017_1129",
    "boe_id": "EUR-CELEX-32017R1129",
    "titulo": "Reglamento (UE) 2017/1129 sobre el prospecto de informacion que se debe publicar cuando se haga una oferta publica o se admitan valores a negociacion",
    "eli_uri": "https://eur-lex.europa.eu/eli/reg/2017/1129/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "reglamento",
    "ambito": "mercados_financieros_ue",
    "estado_cobertura": "ingestada",
}

# Directiva 2011/61/UE — AIFMD (Alternative Investment Fund Managers Directive)
AIFMD_NORMA = {
    "codigo": "AIFMD_2011_0061",
    "boe_id": "EUR-CELEX-32011L0061",
    "titulo": "Directiva 2011/61/UE sobre gestores de fondos de inversion alternativos (AIFMD)",
    "eli_uri": "https://eur-lex.europa.eu/eli/dir/2011/61/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "directiva",
    "ambito": "fondos_inversion_ue",
    "estado_cobertura": "ingestada",
}

# Directiva 2009/65/CE — UCITS (Undertakings for Collective Investment in Transferable Securities)
UCITS_NORMA = {
    "codigo": "UCITS_2009_0065",
    "boe_id": "EUR-CELEX-32009L0065",
    "titulo": "Directiva 2009/65/CE sobre la coordinacion de disposiciones legales, reglamentarias y administrativas relativas a ciertos organismos de inversion colectiva en valores (UCITS)",
    "eli_uri": "https://eur-lex.europa.eu/eli/dir/2009/65/oj",
    "jurisdiccion": "ue",
    "tipo_fuente": "eurlex",
    "tipo_documento": "directiva",
    "ambito": "fondos_inversion_ue",
    "estado_cobertura": "ingestada",
}

DOMAIN_NORMAS = {
    "prospectos": PROSPECTOS_NORMA,
    "aifmd": AIFMD_NORMA,
    "ucits": UCITS_NORMA,
}

DOMAIN_CELEX = {
    "prospectos": "32017R1129",
    "aifmd": "32011L0061",
    "ucits": "32009L0065",
}

DOMAIN_TIPO = {
    "prospectos": "prospectos_eti",
    "aifmd": "aifmd",
    "ucits": "ucits",
}


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


def fetch_index(client: httpx.Client, celex: str) -> list[BloqueIndex]:
    """Fetch index from EUR-Lex consolidated text API."""
    response = client.get(
        f"{EURLEX_BASE}/rest.tx.legal-acts-index/32017R1129",
        headers={"Accept": "application/json"},
    )
    if response.status_code == 404:
        print("  [WARN] 32017R1129 not found in EUR-Lex API, skipping")
        return []
    response.raise_for_status()
    return parse_index(response.json())


def fetch_block(client: httpx.Client, block_id: str) -> BloqueTexto:
    """Fetch a single block from EUR-Lex."""
    response = client.get(
        f"{EURLEX_BASE}/rest.tx.legal-acts-index/32017R1129/{block_id}",
        headers={"Accept": "application/xml"},
    )
    response.raise_for_status()
    return parse_block_xml(block_id, response.text)


def parse_block_xml(block_id: str, xml_text: str) -> BloqueTexto:
    from xml.etree import ElementTree as ET

    root = ET.fromstring(xml_text)
    bloque = root.find(".//bloque")
    version = root.find(".//version")
    if bloque is None or version is None:
        raise ValueError(f"Invalid EUR-Lex block payload for {block_id}")

    titulo = bloque.attrib.get("titulo", "").strip()
    tipo_articulo, numero = _infer_tipo_y_numero(titulo)
    parts = []
    for p in bloque.findall(".//p"):
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
    dialect = conn.engine.dialect.name
    if dialect == "sqlite":
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(sync_log)")).fetchall()}
        for col in ("rows_processed", "errors", "duration_ms"):
            if col not in columns:
                conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {col} INTEGER"))
    else:
        cursor = conn.execute(text("""SELECT column_name FROM information_schema.columns WHERE table_name = 'sync_log'""")).fetchall()
        existing = {row[0] for row in cursor}
        for col, typ in (("rows_processed", "INTEGER"), ("errors", "INTEGER"), ("duration_ms", "INTEGER")):
            if col not in existing:
                conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {col} {typ}"))


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
    now = datetime.now(UTC).isoformat()
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


def upsert_norma(conn, norma: dict, vigente_desde: str) -> None:
    """Upsert a norma record (prospectos, AIFMD or UCITS)."""
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
        {**norma, "vigente_desde": vigente_desde},
    )


def upsert_articulo(conn, codigo: str, bloque: BloqueTexto, regulacion_relacionada: str) -> None:
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
        "Sección ",
        "Capítulo ",
    )
    return titulo.startswith(prefixes)


def _yyyymmdd_to_iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def run_sync(
    worker_name: str = "worker-prospectos",
    domain: str = "prospectos",
) -> dict[str, int]:
    engine = create_engine(DATABASE_URL, future=True)
    bloques_fetched = 0
    articulos_upserted = 0
    sync_start = datetime.now(UTC).isoformat()
    norma = DOMAIN_NORMAS[domain]
    celex = DOMAIN_CELEX[domain]
    tipo = DOMAIN_TIPO[domain]
    vigente_desde_map = {
        "prospectos": "2017-06-07",
        "aifmd": "2013-07-01",
        "ucits": "2009-08-01",
    }
    vigente_desde = vigente_desde_map.get(domain, "2017-06-07")

    try:
        with httpx.Client(timeout=30.0) as client, engine.begin() as conn:
            upsert_norma(conn, norma, vigente_desde)
            ensure_source_revision_table(conn)

            for item in fetch_index(client, celex):
                if not _is_supported_block(item.titulo):
                    continue
                bloque = fetch_block(client, item.id)

                change = check_content_changed(
                    conn, worker_name, "bloque", bloque.bloque_id, bloque.texto
                )

                if not change.changed and destination_row_exists(
                    conn,
                    "version_articulo",
                    "boe_bloque_id",
                    bloque.bloque_id,
                ):
                    bloques_fetched += 1
                    continue

                invalidated = invalidate_old_embeddings(conn, bloque.bloque_id)
                if invalidated:
                    print(
                        f"  [INVALIDATE] {invalidated} old embeddings for {bloque.bloque_id}"
                    )

                upsert_articulo(conn, norma["codigo"], bloque, tipo)
                record_revision(
                    conn,
                    worker_name,
                    "bloque",
                    bloque.bloque_id,
                    bloque.texto,
                )
                bloques_fetched += 1
                articulos_upserted += 1

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
        description="Prospectos/AIFMD/UCITS worker: sync EU regulations from EUR-Lex"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run a single sync cycle and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between sync cycles in continuous mode (default: {SYNC_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--domain",
        choices=["prospectos", "aifmd", "ucits", "all"],
        default="prospectos",
        help="Regulation domain to sync (default: prospectos)",
    )
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("prospectos")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        domains = ["prospectos", "aifmd", "ucits"] if args.domain == "all" else [args.domain]
        for d in domains:
            result = run_sync(worker_name=f"cron-{d}-weekly", domain=d)
            print(
                f"[{d}] Bloques: {result['bloques']}, Articulos: {result['articulos']}"
            )
    else:
        domain = args.domain
        if domain == "all":
            domain = "prospectos"
        print(f"Starting {domain} worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync(domain=domain)
            print(
                f"Synced {domain}: bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
