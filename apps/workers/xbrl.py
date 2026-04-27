import argparse
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import create_engine, text

if __package__:
    from .runtime import get_database_url
else:
    from runtime import get_database_url


XBRLI_NS = "http://www.xbrl.org/2003/instance"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_decimal(value: str | None):
    if value is None:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _bind_numeric_value(value, *, dialect_name: str):
    if value is None:
        return None

    if isinstance(value, Decimal) and dialect_name == "sqlite":
        return str(value)

    return value


def _insert_do_nothing_sql(table_name: str, columns: tuple[str, ...], conflict_target: tuple[str, ...], *, dialect_name: str) -> str:
    column_list = ", ".join(columns)
    value_list = ", ".join(f":{column}" for column in columns)

    if dialect_name == "sqlite":
        return f"INSERT OR IGNORE INTO {table_name} ({column_list}) VALUES ({value_list})"

    conflict_list = ", ".join(conflict_target)
    return (
        f"INSERT INTO {table_name} ({column_list}) VALUES ({value_list}) "
        f"ON CONFLICT ({conflict_list}) DO NOTHING"
    )


def parse_xbrl_fixture(fixture_path: str) -> dict:
    fixture = Path(fixture_path).resolve()
    root = ET.parse(fixture).getroot()

    contexts = {}
    units = {}

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
            units[child.attrib.get("id")] = child.findtext(f".//{{{XBRLI_NS}}}measure")

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
                "unit": units.get(child.attrib.get("unitRef")),
                "context_ref": context_ref,
                "period_start": context.get("period_start"),
                "period_end": context.get("period_end"),
                "entity_identifier": context.get("entity_identifier"),
                "decimals": child.attrib.get("decimals"),
            }
        )

    filing = {
        "source_name": fixture.name,
        "source_path": str(fixture),
        "entity_identifier": entity_identifier,
        "period_start": filing_period_start,
        "period_end": filing_period_end,
        "filing_type": "xbrl",
    }

    return {"filing": filing, "facts": facts}


def parse_ixbrl_fixture(fixture_path: str) -> dict:
    fixture = Path(fixture_path).resolve()

    try:
        root = ET.parse(fixture).getroot()
        return _parse_xbrl_root(root, fixture_path=str(fixture))
    except ET.ParseError:
        pass

    html = fixture.read_text(encoding="utf-8")

    match = _extract_xbrl_fragment(html)
    if not match:
        return {"filing": {
            "source_name": fixture.name,
            "source_path": str(fixture),
            "entity_identifier": None,
            "period_start": None,
            "period_end": None,
            "filing_type": "ixbrl",
        }, "facts": []}

    try:
        root = ET.fromstring(match)
        return _parse_xbrl_root(root, fixture_path=str(fixture))
    except ET.ParseError:
        return {"filing": {
            "source_name": fixture.name,
            "source_path": str(fixture),
            "entity_identifier": None,
            "period_start": None,
            "period_end": None,
            "filing_type": "ixbrl",
        }, "facts": []}


def _extract_xbrl_fragment(html: str):
    start_tag = "<xbrli:xbrl"
    start_idx = html.find(start_tag)
    if start_idx == -1:
        return None

    end_tag = "</xbrli:xbrl>"
    search_from = start_idx + len(start_tag)
    end_idx = html.find(end_tag, search_from)
    if end_idx == -1:
        return None

    end_idx += len(end_tag)

    depth = 0
    pos = start_idx
    while pos < end_idx:
        open_tag = html.find("<xbrli:", pos)
        close_tag = html.find("</xbrli:", pos)

        if close_tag == -1 or (open_tag != -1 and open_tag < close_tag):
            if open_tag == -1:
                break
            if html[open_tag + 1:open_tag + 2] in ("/", "!", "?"):
                pos = open_tag + 1
                continue
            tag_end = html.find(">", open_tag)
            if tag_end == -1:
                break
            if not html[tag_end - 1].isspace():
                depth += 1
            else:
                depth -= 1
            pos = tag_end + 1
        else:
            depth -= 1
            pos = close_tag + len(end_tag)
            if depth <= 0:
                break

    return html[start_idx:pos] if pos > start_idx else None


def _parse_xbrl_root(root, *, fixture_path: str = "") -> dict:
    contexts = {}
    units = {}

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
            units[child.attrib.get("id")] = child.findtext(f".//{{{XBRLI_NS}}}measure")

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
                "unit": units.get(child.attrib.get("unitRef")),
                "context_ref": context_ref,
                "period_start": context.get("period_start"),
                "period_end": context.get("period_end"),
                "entity_identifier": context.get("entity_identifier"),
                "decimals": child.attrib.get("decimals"),
            }
        )

    filing = {
        "source_name": "ixbrl",
        "source_path": "",
        "entity_identifier": entity_identifier,
        "period_start": filing_period_start,
        "period_end": filing_period_end,
        "filing_type": "ixbrl",
    }

    return {"filing": filing, "facts": facts}


def load_xbrl_fixture(*, engine, fixture_path: str) -> dict:
    parsed = parse_xbrl_fixture(fixture_path)
    filing_columns = (
        "source_name",
        "source_path",
        "entity_identifier",
        "period_start",
        "period_end",
        "filing_type",
    )
    fact_columns = (
        "filing_id",
        "concept",
        "value_raw",
        "value_numeric",
        "unit",
        "context_ref",
        "period_start",
        "period_end",
        "entity_identifier",
        "decimals",
    )

    with engine.begin() as conn:
        dialect_name = conn.dialect.name
        filing_insert = text(
            _insert_do_nothing_sql(
                "xbrl_filing",
                filing_columns,
                ("source_path",),
                dialect_name=dialect_name,
            )
        )
        fact_insert = text(
            _insert_do_nothing_sql(
                "xbrl_fact",
                fact_columns,
                ("filing_id", "concept", "context_ref", "value_raw"),
                dialect_name=dialect_name,
            )
        )
        filings_upserted = 0
        facts_upserted = 0

        filing_result = conn.execute(filing_insert, parsed["filing"])
        filings_upserted = filing_result.rowcount or 0
        filing_id = conn.execute(
            text("SELECT id FROM xbrl_filing WHERE source_path = :source_path"),
            {"source_path": parsed["filing"]["source_path"]},
        ).scalar_one()

        for fact in parsed["facts"]:
            db_fact = {
                **fact,
                "value_numeric": _bind_numeric_value(fact["value_numeric"], dialect_name=dialect_name),
            }
            fact_result = conn.execute(fact_insert, {"filing_id": filing_id, **db_fact})
            facts_upserted += fact_result.rowcount or 0

    return {"filings_upserted": filings_upserted, "facts_upserted": facts_upserted}


def _derive_filing_type(fixture_path: str) -> str:
    fixture = Path(fixture_path).resolve()
    suffix = fixture.suffix.lower()
    if suffix in (".html", ".htm"):
        return "ixbrl"
    if suffix in (".xbrl", ".xml"):
        return "xbrl"
    text_content = fixture.read_text(encoding="utf-8", errors="ignore")[:4096]
    if "<html" in text_content.lower() or "<!doctype html" in text_content.lower():
        return "ixbrl"
    return "xbrl"


def parse_filing_fixture(fixture_path: str) -> dict:
    filing_type = _derive_filing_type(fixture_path)
    if filing_type == "ixbrl":
        return parse_ixbrl_fixture(fixture_path)
    return parse_xbrl_fixture(fixture_path)


def load_filing_fixture(*, engine, fixture_path: str) -> dict:
    parsed = parse_filing_fixture(fixture_path)
    filing_columns = (
        "source_name",
        "source_path",
        "entity_identifier",
        "period_start",
        "period_end",
        "filing_type",
    )
    fact_columns = (
        "filing_id",
        "concept",
        "value_raw",
        "value_numeric",
        "unit",
        "context_ref",
        "period_start",
        "period_end",
        "entity_identifier",
        "decimals",
    )

    with engine.begin() as conn:
        dialect_name = conn.dialect.name
        filing_insert = text(
            _insert_do_nothing_sql(
                "xbrl_filing",
                filing_columns,
                ("source_path", "filing_type"),
                dialect_name=dialect_name,
            )
        )
        fact_insert = text(
            _insert_do_nothing_sql(
                "xbrl_fact",
                fact_columns,
                ("filing_id", "concept", "context_ref", "value_raw"),
                dialect_name=dialect_name,
            )
        )
        filings_upserted = 0
        facts_upserted = 0

        filing_result = conn.execute(filing_insert, parsed["filing"])
        filings_upserted = filing_result.rowcount or 0
        filing_id = conn.execute(
            text("SELECT id FROM xbrl_filing WHERE source_path = :source_path AND filing_type = :filing_type"),
            {
                "source_path": parsed["filing"]["source_path"],
                "filing_type": parsed["filing"]["filing_type"],
            },
        ).scalar_one()

        for fact in parsed["facts"]:
            db_fact = {
                **fact,
                "value_numeric": _bind_numeric_value(fact["value_numeric"], dialect_name=dialect_name),
            }
            fact_result = conn.execute(fact_insert, {"filing_id": filing_id, **db_fact})
            facts_upserted += fact_result.rowcount or 0

    return {"filings_upserted": filings_upserted, "facts_upserted": facts_upserted}


def run_sync(*, fixture_path: str, engine=None):
    engine = engine or create_engine(get_database_url(), future=True)
    return load_filing_fixture(engine=engine, fixture_path=fixture_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-path", required=True)
    args = parser.parse_args()
    run_sync(fixture_path=args.fixture_path)


if __name__ == "__main__":
    main()
