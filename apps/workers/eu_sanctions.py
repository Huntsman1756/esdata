#!/usr/bin/env python
"""Ingest the official EU consolidated financial sanctions XML list."""

from __future__ import annotations

import argparse
import json
import os
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
EU_SANCTIONS_XML_URL = os.getenv("EU_SANCTIONS_XML_URL") or (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
)
EU_SANCTIONS_SOURCE_PAGE = (
    "https://finance.ec.europa.eu/eu-and-world/sanctions-restrictive-measures/"
    "overview-sanctions-and-related-resources_en"
)
logger = configure_logging("worker-eu-sanctions")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _children(node: ET.Element, local_name: str) -> list[ET.Element]:
    return [child for child in list(node) if _local_name(child.tag) == local_name]


def _descendants(node: ET.Element, local_name: str) -> list[ET.Element]:
    return [child for child in node.iter() if _local_name(child.tag) == local_name]


def _first_attr(node: ET.Element, *names: str) -> str:
    for name in names:
        value = node.get(name)
        if value:
            return value.strip()
    return ""


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.lower().strip())
    normalized = normalized.encode("ascii", "ignore").decode("utf-8")
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
    return " ".join(normalized.split())


def _tipo_entidad(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"person", "p", "individual", "natural person"}:
        return "person"
    if normalized in {"vessel", "ship"}:
        return "vessel"
    if normalized in {"aircraft"}:
        return "aircraft"
    return "entity"


def _name_from_alias(alias: ET.Element) -> str:
    whole_name = _first_attr(alias, "wholeName", "nameAliasWholeName")
    if whole_name:
        return whole_name
    parts = [
        _first_attr(alias, "firstName"),
        _first_attr(alias, "middleName"),
        _first_attr(alias, "lastName"),
    ]
    joined = " ".join(part for part in parts if part)
    return joined or _text(alias)


def _subject_type(entity: ET.Element) -> str:
    subject = next(iter(_children(entity, "subjectType")), None)
    if subject is None:
        return ""
    return _first_attr(subject, "classificationCode", "code") or _text(subject)


def _programmes(entity: ET.Element) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for regulation in _descendants(entity, "regulation"):
        for value in (
            _first_attr(regulation, "programme", "programmeCode"),
            _first_attr(regulation, "numberTitle"),
        ):
            if value and value not in seen:
                seen.add(value)
                values.append(value)
    return values


def _countries(entity: ET.Element) -> list[str]:
    values: set[str] = set()
    for address in _descendants(entity, "address"):
        for value in (
            _first_attr(address, "countryDescription", "countryIso2Code", "countryCode"),
            _text(next(iter(_children(address, "country")), None)),
        ):
            if value:
                values.add(value)
    return sorted(values)


def _id_documents(entity: ET.Element) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for identification in _descendants(entity, "identification"):
        id_type = _first_attr(
            identification,
            "identificationTypeCode",
            "identificationTypeDescription",
            "documentType",
        )
        number = _first_attr(identification, "number", "passportNumber", "identityNumber")
        if id_type or number:
            documents.append({"type": id_type, "number": number})
    return documents


def _published_date(root: ET.Element) -> str:
    for node in root.iter():
        if _local_name(node.tag) in {"exportGenerationDate", "generationDate", "publicationDate"}:
            value = _text(node)
            if value:
                return value
        value = _first_attr(node, "generationDate", "exportGenerationDate")
        if value:
            return value
    return ""


def parse_eu_sanctions_xml(content: bytes) -> tuple[list[dict], dict]:
    """Parse EU FSF XML bytes into screening entry dictionaries."""
    root = ET.fromstring(content)
    published = _published_date(root)
    entries: list[dict] = []

    for entity in _descendants(root, "sanctionEntity"):
        entity_id = _first_attr(entity, "euReferenceNumber", "logicalId", "id")
        aliases = [_name_from_alias(alias) for alias in _descendants(entity, "nameAlias")]
        aliases = [alias for alias in aliases if alias]
        name = aliases[0] if aliases else _text(entity)
        if not entity_id or not name:
            continue

        subject_type = _subject_type(entity)
        programmes = _programmes(entity)
        countries = _countries(entity)
        id_documents = _id_documents(entity)
        regulation_urls = sorted(
            {
                _first_attr(regulation, "publicationUrl")
                for regulation in _descendants(entity, "regulation")
                if _first_attr(regulation, "publicationUrl")
            }
        )

        entries.append(
            {
                "entidad_id": f"EU-{entity_id}",
                "nombre": name,
                "nombre_normalizado": _normalize_name(name),
                "tipo_entidad": _tipo_entidad(subject_type),
                "aliases": aliases[1:],
                "categorias": ["sanctions", "eu", *programmes],
                "descripcion": None,
                "activo": True,
                "metadata_json": {
                    "source_url": EU_SANCTIONS_XML_URL,
                    "source_page": EU_SANCTIONS_SOURCE_PAGE,
                    "source_family": "EU consolidated financial sanctions official XML",
                    "generation_date": published or None,
                    "subject_type": subject_type or None,
                    "programmes": programmes,
                    "countries": countries,
                    "id_documents": id_documents,
                    "regulation_urls": regulation_urls,
                },
            }
        )

    if not entries:
        raise RuntimeError("EU sanctions XML produced zero screening entries")

    return entries, {"generation_date": published, "record_count": str(len(entries))}


def fetch_eu_sanctions_xml(url: str = EU_SANCTIONS_XML_URL) -> tuple[list[dict], dict]:
    request = Request(url, headers={"User-Agent": "esdata-eu-sanctions-worker/1.0"})
    with urlopen(request, timeout=180) as response:
        content = response.read()
    return parse_eu_sanctions_xml(content)


def _parse_source_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _upsert_eu_list(conn, source_meta: dict) -> int:
    return conn.execute(
        text(
            """
            INSERT INTO screening_lists (
                codigo, nombre, tipo, organismo, pais, url_fuente,
                descripcion, actualizada, activo
            )
            VALUES (
                'EU_SANCTIONS',
                'EU consolidated financial sanctions list',
                'sanctions',
                'European Commission - DG FISMA',
                NULL,
                :source_url,
                'Official EU consolidated financial sanctions XML. If the direct XML URL requires session configuration, set EU_SANCTIONS_XML_URL to the official export URL from the Commission FSF portal.',
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
        {
            "source_url": EU_SANCTIONS_XML_URL,
            "actualizada": _parse_source_date(source_meta.get("generation_date")),
        },
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


def run_sync(worker_name: str = "cron-eu-sanctions-weekly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)
    started_at = datetime.now(UTC).isoformat()
    processed = 0

    try:
        entries, source_meta = fetch_eu_sanctions_xml()
        with engine.begin() as conn:
            list_id = _upsert_eu_list(conn, source_meta)
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
            "source": "eu_sanctions_xml",
            "source_url": EU_SANCTIONS_XML_URL,
            "started_at": started_at,
        }
    except Exception as exc:
        if not handle_worker_failure(engine, "eu_sanctions", "EU_SANCTIONS", "sync_list", exc):
            logger.warning("EU sanctions sync moved to dead-letter")
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
            logger.warning("Failed to write EU sanctions sync error log: %s", log_exc)
        return {
            "worker": worker_name,
            "processed": processed,
            "source": "eu_sanctions_xml",
            "source_url": EU_SANCTIONS_XML_URL,
            "started_at": started_at,
            "error": str(exc),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EU consolidated sanctions official XML worker")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()

    init_sentry("eu_sanctions")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync()
        print(f"[run-once] EU sanctions: {result['processed']} entries from {result['source']}")
        print(f"  Source: {result['source_url']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting EU sanctions worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"EU sanctions: {result['processed']} entries from {result['source']} "
                f"at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
