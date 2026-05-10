#!/usr/bin/env python
"""Ingest the official OFAC SDN XML list into screening tables.

This worker is intentionally source-strict: it uses the official U.S. Treasury
OFAC SDN XML export and never falls back to fixtures. The EU/SEPBLAC screening
surfaces remain unavailable until their official parsers are implemented.
"""

from __future__ import annotations

import argparse
import json
import time
import unicodedata
from datetime import UTC, datetime
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from boe import _ensure_sync_log_table, log_sync
from runtime import (
    configure_logging,
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    init_sentry,
)
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)
OFAC_SDN_XML_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
logger = configure_logging("worker-ofac-sdn")


def _child_text(node: ET.Element, tag: str) -> str:
    child = node.find(f"{{*}}{tag}")
    return (child.text or "").strip() if child is not None else ""


def _normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.lower().strip())
    normalized = normalized.encode("ascii", "ignore").decode("utf-8")
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
    return " ".join(normalized.split())


def _entity_name(entry: ET.Element) -> str:
    first_name = _child_text(entry, "firstName")
    last_name = _child_text(entry, "lastName")
    if first_name and last_name:
        return f"{first_name} {last_name}".strip()
    return last_name or first_name


def _alias_name(aka: ET.Element) -> str | None:
    first_name = _child_text(aka, "firstName")
    last_name = _child_text(aka, "lastName")
    if first_name and last_name:
        return f"{first_name} {last_name}".strip()
    return last_name or first_name or None


def _tipo_entidad(sdn_type: str) -> str:
    normalized = sdn_type.strip().lower()
    if normalized == "individual":
        return "person"
    if normalized == "vessel":
        return "vessel"
    if normalized == "aircraft":
        return "aircraft"
    return "entity"


def parse_ofac_sdn_xml(content: bytes) -> tuple[list[dict], dict]:
    """Parse OFAC SDN XML bytes into screening entry dictionaries."""

    root = ET.fromstring(content)
    publish_info = root.find("{*}publshInformation")
    if publish_info is None:
        publish_info = root
    published = _child_text(publish_info, "Publish_Date")
    record_count = _child_text(publish_info, "Record_Count")
    entries: list[dict] = []

    for raw_entry in root.findall("{*}sdnEntry"):
        uid = _child_text(raw_entry, "uid")
        name = _entity_name(raw_entry)
        if not uid or not name:
            continue

        programs = [
            (program.text or "").strip()
            for program in raw_entry.findall("{*}programList/{*}program")
            if (program.text or "").strip()
        ]
        aliases = [
            alias
            for alias in (_alias_name(aka) for aka in raw_entry.findall("{*}akaList/{*}aka"))
            if alias
        ]
        countries = sorted(
            {
                (_child_text(address, "country") or "").strip()
                for address in raw_entry.findall("{*}addressList/{*}address")
                if _child_text(address, "country")
            }
        )
        id_documents = []
        for raw_id in raw_entry.findall("{*}idList/{*}id"):
            id_type = _child_text(raw_id, "idType")
            id_number = _child_text(raw_id, "idNumber")
            if id_type or id_number:
                id_documents.append({"type": id_type, "number": id_number})

        sdn_type = _child_text(raw_entry, "sdnType")
        entries.append(
            {
                "entidad_id": f"OFAC-{uid}",
                "nombre": name,
                "nombre_normalizado": _normalize_name(name),
                "tipo_entidad": _tipo_entidad(sdn_type),
                "aliases": aliases,
                "categorias": ["sanctions", "ofac", *programs],
                "descripcion": _child_text(raw_entry, "remarks") or None,
                "activo": True,
                "metadata_json": {
                    "source_url": OFAC_SDN_XML_URL,
                    "source_family": "OFAC SDN official XML",
                    "publish_date": published or None,
                    "record_count": record_count or None,
                    "sdn_type": sdn_type or None,
                    "programs": programs,
                    "countries": countries,
                    "id_documents": id_documents,
                },
            }
        )

    if not entries:
        raise RuntimeError("OFAC SDN XML produced zero screening entries")

    return entries, {"publish_date": published, "record_count": record_count}


def fetch_ofac_sdn_xml(url: str = OFAC_SDN_XML_URL) -> tuple[list[dict], dict]:
    request = Request(url, headers={"User-Agent": "esdata-ofac-sdn-worker/1.0"})
    with urlopen(request, timeout=120) as response:
        content = response.read()
    return parse_ofac_sdn_xml(content)


def _upsert_ofac_list(conn, source_meta: dict) -> int:
    actualizada = None
    publish_date = source_meta.get("publish_date")
    if publish_date:
        try:
            actualizada = datetime.strptime(publish_date, "%m/%d/%Y").date()
        except ValueError:
            actualizada = None

    return conn.execute(
        text(
            """
            INSERT INTO screening_lists (
                codigo, nombre, tipo, organismo, pais, url_fuente,
                descripcion, actualizada, activo
            )
            VALUES (
                'OFAC_SDN',
                'OFAC Specially Designated Nationals and Blocked Persons List',
                'sanctions',
                'U.S. Department of the Treasury - Office of Foreign Assets Control',
                NULL,
                :source_url,
                'Official OFAC SDN XML export ingested without fixture fallback.',
                :actualizada,
                TRUE
            )
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                tipo = EXCLUDED.tipo,
                organismo = EXCLUDED.organismo,
                url_fuente = EXCLUDED.url_fuente,
                descripcion = EXCLUDED.descripcion,
                actualizada = EXCLUDED.actualizada,
                activo = TRUE
            RETURNING id
            """
        ),
        {"source_url": OFAC_SDN_XML_URL, "actualizada": actualizada},
    ).scalar_one()


def _upsert_entry(conn, list_id: int, entry: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO screening_entries (
                list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad,
                pais, nif, fecha_nacimiento, aliases, categorias, descripcion,
                fecha_sancion, fecha_alta, fecha_baja, activo, metadata_json
            )
            VALUES (
                :list_id, :entidad_id, :nombre, :nombre_normalizado, :tipo_entidad,
                NULL, NULL, NULL, :aliases, :categorias, :descripcion,
                NULL, NULL, NULL, TRUE, CAST(:metadata_json AS JSONB)
            )
            ON CONFLICT (list_id, entidad_id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                nombre_normalizado = EXCLUDED.nombre_normalizado,
                tipo_entidad = EXCLUDED.tipo_entidad,
                aliases = EXCLUDED.aliases,
                categorias = EXCLUDED.categorias,
                descripcion = EXCLUDED.descripcion,
                activo = TRUE,
                metadata_json = EXCLUDED.metadata_json
            """
        ),
        {
            "list_id": list_id,
            "entidad_id": entry["entidad_id"],
            "nombre": entry["nombre"],
            "nombre_normalizado": entry["nombre_normalizado"],
            "tipo_entidad": entry["tipo_entidad"],
            "aliases": entry["aliases"],
            "categorias": entry["categorias"],
            "descripcion": entry["descripcion"],
            "metadata_json": json.dumps(entry["metadata_json"], ensure_ascii=False),
        },
    )


def run_sync(worker_name: str = "cron-ofac-sdn-weekly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    started_at = datetime.now(UTC).isoformat()
    processed = 0

    try:
        entries, source_meta = fetch_ofac_sdn_xml()
        with engine.begin() as conn:
            list_id = _upsert_ofac_list(conn, source_meta)
            conn.execute(
                text("UPDATE screening_entries SET activo = FALSE WHERE list_id = :list_id"),
                {"list_id": list_id},
            )
            for entry in entries:
                _upsert_entry(conn, list_id, entry)
                processed += 1
            _ensure_sync_log_table(conn)
            log_sync(
                conn,
                worker_name,
                "ok",
                documentos_processed=len(entries),
                documentos_upserted=processed,
                started_at=started_at,
            )
        return {
            "worker": worker_name,
            "processed": processed,
            "source": "ofac_sdn_xml",
            "source_url": OFAC_SDN_XML_URL,
            "started_at": started_at,
        }
    except Exception as exc:
        if not handle_worker_failure(engine, "ofac_sdn", "OFAC_SDN", "sync_list", exc):
            logger.warning("OFAC SDN sync moved to dead-letter")
        try:
            with engine.begin() as conn:
                _ensure_sync_log_table(conn)
                log_sync(
                    conn,
                    worker_name,
                    "error",
                    error_msg=str(exc)[:500],
                    started_at=started_at,
                )
        except Exception as log_exc:
            logger.warning("Failed to write OFAC sync error log: %s", log_exc)
        return {
            "worker": worker_name,
            "processed": processed,
            "source": "ofac_sdn_xml",
            "source_url": OFAC_SDN_XML_URL,
            "started_at": started_at,
            "error": str(exc),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OFAC SDN official XML worker")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()

    init_sentry("ofac_sdn")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync()
        print(f"[run-once] OFAC SDN: {result['processed']} entries from {result['source']}")
        print(f"  Source: {result['source_url']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting OFAC SDN worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"OFAC SDN: {result['processed']} entries from {result['source']} "
                f"at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
