#!/usr/bin/env python
"""Worker para XBRL desde CNMV y utilidades fixture-first para tests."""

import argparse
import os
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

if __package__:
    from .change_detection import ensure_source_revision_table
    from .runtime import ensure_database_connection, get_database_url, get_interval_seconds
else:
    from change_detection import ensure_source_revision_table
    from runtime import ensure_database_connection, get_database_url, get_interval_seconds

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 2592000)
CNMV_BASE = os.getenv("CNMV_BASE", "https://www.cnmv.es")

SEED_XBRL_COMPANIES = [
    (50, "INDITEX", "cotizada", "textil", "ES-XBRL-2024-001", "ES", "active"),
    (51, "IBERDROLA", "cotizada", "energia", "ES-XBRL-2024-002", "ES", "active"),
    (52, "TELEFONICA", "cotizada", "telecomunicaciones", "ES-XBRL-2024-003", "ES", "active"),
    (53, "BBVA", "cotizada", "banco", "ES-XBRL-2024-004", "ES", "active"),
    (54, "REPSOL", "cotizada", "petroleo", "ES-XBRL-2024-005", "ES", "active"),
    (55, "CAIXABANK", "cotizada", "banco", "ES-XBRL-2024-006", "ES", "active"),
]

XBRLI_NS = "http://www.xbrl.org/2003/instance"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _db_numeric(value: Decimal | None):
    if value is None:
        return None
    return float(value)


def _parse_xbrl_root(root: ET.Element, *, filing_type: str, source_path: str) -> dict:
    contexts: dict[str | None, dict[str, str | None]] = {}
    units: dict[str | None, str | None] = {}

    for child in root:
        local = _local_name(child.tag)
        if local == "context":
            context_id = child.attrib.get("id")
            identifier = child.findtext(f".//{{{XBRLI_NS}}}identifier")
            start_date = child.findtext(f".//{{{XBRLI_NS}}}startDate")
            end_date = child.findtext(f".//{{{XBRLI_NS}}}endDate")
            instant = child.findtext(f".//{{{XBRLI_NS}}}instant")
            contexts[context_id] = {
                "entity_identifier": identifier,
                "period_start": start_date or instant,
                "period_end": end_date or instant,
            }
        elif local == "unit":
            unit_id = child.attrib.get("id")
            measure = child.findtext(f".//{{{XBRLI_NS}}}measure")
            units[unit_id] = measure

    facts = []
    entity_identifier = None
    filing_period_start = None
    filing_period_end = None

    for child in root:
        local = _local_name(child.tag)
        if local in {"context", "unit"}:
            continue

        context_ref = child.attrib.get("contextRef")
        if not context_ref:
            continue

        unit_ref = child.attrib.get("unitRef")
        decimals = child.attrib.get("decimals")
        raw_value = (child.text or "").strip()
        context = contexts.get(context_ref, {})

        entity_identifier = entity_identifier or context.get("entity_identifier")
        filing_period_start = filing_period_start or context.get("period_start")
        filing_period_end = filing_period_end or context.get("period_end")

        facts.append(
            {
                "concept": local,
                "value_raw": raw_value,
                "value_numeric": _parse_decimal(raw_value),
                "unit": units.get(unit_ref),
                "context_ref": context_ref,
                "period_start": context.get("period_start"),
                "period_end": context.get("period_end"),
                "entity_identifier": context.get("entity_identifier"),
                "decimals": decimals,
            }
        )

    filing = {
        "source_name": Path(source_path).name,
        "source_path": str(Path(source_path).resolve()),
        "entity_identifier": entity_identifier,
        "period_start": filing_period_start,
        "period_end": filing_period_end,
        "filing_type": filing_type,
    }
    return {"filing": filing, "facts": facts}


def parse_xbrl_fixture(fixture_path: str) -> dict:
    root = ET.parse(fixture_path).getroot()
    return _parse_xbrl_root(root, filing_type="xbrl", source_path=fixture_path)


def _derive_filing_type(fixture_path: str) -> str:
    suffix = Path(fixture_path).suffix.lower()
    if suffix in {".ixbrl", ".html", ".htm"}:
        return "ixbrl"
    if suffix in {".xbrl", ".xml"}:
        return "xbrl"

    raw = Path(fixture_path).read_text(encoding="utf-8", errors="ignore").lower()
    return "ixbrl" if "<html" in raw else "xbrl"


def _extract_xbrl_fragment(raw_html: str) -> str | None:
    start_tag = "<xbrli:xbrl"
    end_tag = "</xbrli:xbrl>"
    start = raw_html.find(start_tag)
    end = raw_html.find(end_tag)
    if start == -1 or end == -1:
        return None
    return raw_html[start : end + len(end_tag)]


def parse_filing_fixture(fixture_path: str) -> dict:
    filing_type = _derive_filing_type(fixture_path)
    if filing_type == "xbrl":
        return parse_xbrl_fixture(fixture_path)

    raw_html = Path(fixture_path).read_text(encoding="utf-8", errors="ignore")
    fragment = _extract_xbrl_fragment(raw_html)
    if fragment is None:
        return {
            "filing": {
                "source_name": Path(fixture_path).name,
                "source_path": str(Path(fixture_path).resolve()),
                "entity_identifier": None,
                "period_start": None,
                "period_end": None,
                "filing_type": "ixbrl",
            },
            "facts": [],
        }

    root = ET.fromstring(fragment)
    return _parse_xbrl_root(root, filing_type="ixbrl", source_path=fixture_path)


def load_filing_fixture(*, engine, fixture_path: str) -> dict:
    parsed = parse_filing_fixture(fixture_path)

    with engine.begin() as conn:
        existing_filing = conn.execute(
            text("SELECT id FROM xbrl_filing WHERE source_path = :source_path"),
            {"source_path": parsed["filing"]["source_path"]},
        ).scalar_one_or_none()

        filings_upserted = 0
        facts_upserted = 0

        if existing_filing is None:
            conn.execute(
                text(
                    """
                    INSERT INTO xbrl_filing (source_name, source_path, entity_identifier, period_start, period_end, filing_type)
                    VALUES (:source_name, :source_path, :entity_identifier, :period_start, :period_end, :filing_type)
                    """
                ),
                parsed["filing"],
            )
            filings_upserted = 1

        filing_id = conn.execute(
            text("SELECT id FROM xbrl_filing WHERE source_path = :source_path"),
            {"source_path": parsed["filing"]["source_path"]},
        ).scalar_one()

        for fact in parsed["facts"]:
            existing_fact = conn.execute(
                text(
                    """
                    SELECT id FROM xbrl_fact
                    WHERE filing_id = :filing_id
                      AND concept = :concept
                      AND COALESCE(context_ref, '') = COALESCE(:context_ref, '')
                      AND value_raw = :value_raw
                    LIMIT 1
                    """
                ),
                {"filing_id": filing_id, **fact},
            ).scalar_one_or_none()
            if existing_fact is not None:
                continue

            conn.execute(
                text(
                    """
                    INSERT INTO xbrl_fact (
                        filing_id, concept, value_raw, value_numeric, unit, context_ref,
                        period_start, period_end, entity_identifier, decimals
                    ) VALUES (
                        :filing_id, :concept, :value_raw, :value_numeric, :unit, :context_ref,
                        :period_start, :period_end, :entity_identifier, :decimals
                    )
                    """
                ),
                {
                    "filing_id": filing_id,
                    **fact,
                    "value_numeric": _db_numeric(fact["value_numeric"]),
                },
            )
            facts_upserted += 1

    return {"filings_upserted": filings_upserted, "facts_upserted": facts_upserted}


def load_xbrl_fixture(*, engine, fixture_path: str) -> dict:
    return load_filing_fixture(engine=engine, fixture_path=fixture_path)


def fetch_cnmv_xbrl_filings() -> list[dict] | None:
    urls = [
        "https://www.cnmv.es/infra/cvie/menu.php",
        "https://www.cnmv.es/",
    ]
    for url in urls:
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                filings = []
                for table in soup.find_all("table"):
                    for row in table.find_all("tr")[1:]:
                        cells = row.find_all("td")
                        if len(cells) >= 3:
                            filings.append({
                                "empresa_nombre": cells[0].get_text(strip=True),
                                "pais": cells[1].get_text(strip=True)[:2].upper(),
                                "tipo_empresa": cells[2].get_text(strip=True),
                            })
                if filings:
                    return filings
        except (httpx.RequestError, Exception):
            continue
    return None


def run_sync(worker_name: str = "cron-xbrl-monthly") -> dict:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "cnmv+seed"
    companies_stored = 0
    try:
        with engine.begin() as conn:
            ensure_source_revision_table(conn)
            for row in SEED_XBRL_COMPANIES:
                conn.connection.execute(
                    """INSERT INTO xbrl_company (company_id, company_name, company_type,
                        sector, registration_number, home_member_state, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    row,
                )
                companies_stored += 1
                total += 1
            return {"processed": total, "source": source, "companies": companies_stored, "worker": worker_name, "started_at": sync_start}
    except Exception as exc:
        return {"processed": total, "source": source, "companies": companies_stored, "worker": worker_name, "error": str(exc), "started_at": sync_start}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XBRL worker")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()
    from runtime import init_sentry
    init_sentry("xbrl")
    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS
    if args.run_once:
        result = run_sync()
        print(f"[run-once] XBRL: {result['processed']} total (companies={result['companies']})")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting XBRL worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"XBRL: {result['processed']} total at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
