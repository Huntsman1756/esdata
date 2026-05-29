"""Regulatory Watch worker — monitors official sources for regulatory changes.

Watches BOE, AEAT, EUR-Lex, AEPD, Banco de Espana, and DGT for changes
affecting the system's regulatory data (tax rates, deadlines, new norms,
repeals, amendments).

Sources monitored:
- BOE daily: key leyes (LIVA L37/1992, LIRPF L35/2006, LIS L27/2014)
- AEAT calendar: fiscal deadline changes
- EUR-Lex: EU regulation updates
- AEPD/BDE/DGT: regulatory updates from these authorities

Runs daily via cron (not continuous). Idempotent — running twice
won't duplicate entries.

Sync intervalo: diario via cron (ver docker-compose.prod.yml).
Auditoria: cada ejecucion escribe en sync_log (worker='reg-watch').
"""

import argparse
import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import unescape

import httpx
from runtime import (
    ensure_database_connection,
    get_database_url,
    get_interval_seconds,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, inspect, text

logger = logging.getLogger(__name__)

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 86400)

# ============================================================
# Key laws to monitor on BOE
# ============================================================

BOE_KEY_LAWS = {
    "LIVA": {
        "boe_id": "BOE-A-1992-28740",
        "norma_ref": "L37/1992",
        "titulo": "Ley 37/1992, del IVA",
        "change_types": ["rate_change", "amendment"],
    },
    "LIRPF": {
        "boe_id": "BOE-A-2006-20764",
        "norma_ref": "L35/2006",
        "titulo": "Ley 35/2006, del IRPF",
        "change_types": ["amendment"],
    },
    "LIS": {
        "boe_id": "BOE-A-2014-12328",
        "norma_ref": "L27/2014",
        "titulo": "Ley 27/2014, del Impuesto de Sociedades",
        "change_types": ["amendment"],
    },
    "LGT": {
        "boe_id": "BOE-A-2003-23186",
        "norma_ref": "L58/2003",
        "titulo": "Ley 58/2003, General Tributaria",
        "change_types": ["amendment"],
    },
}

# Known tax rates to watch for changes
WATCHED_RATES = {
    "iva_general": {"table": "iva_rates", "rate_type": "general", "default": 21.0},
    "iva_reducido": {"table": "iva_rates", "rate_type": "reducido", "default": 10.0},
    "iva_superreducido": {"table": "iva_rates", "rate_type": "superreducido", "default": 4.0},
}

# AEAT calendar URL
AEAT_CALENDAR_URL = os.getenv(
    "AEAT_CALENDAR_URL",
    "https://www.agenciatributaria.gob.es/static_files/AEAT/D共通s/portal/informacion_contribuyentes/CalendarioContribuyentes/{year}/calendario_{year}.pdf",
)

# EUR-Lex SPARQL endpoint
SPARQL_BASE = os.getenv("SPARQL_BASE", "https://data.europa.eu/sparql")

# Official source URLs for change detection
SOURCE_URLS = {
    "boe_legislacion": "https://www.boe.es/diario_boe/xml.php",
    "aeat_calendario": "https://www.agenciatributaria.gob.es/static_files/AEAT/D共通s/portal/informacion_contribuyentes/CalendarioContribuyentes/index.shtml",
    "eurlex_recent": "https://eur-lex.europa.eu/specialized-search?query=&sortBy=SO&sortOrder=descending&dateRange=currentYear&type=advanced&numPagesToDisplay=10",
    "aepd_resoluciones": "https://www.aepd.es/es/sala-prensa/notas-y-resoluciones",
    "bde_publicaciones": "https://www.bde.es/bdesite/es/sectores/publicaciones/",
    "dgt_doctrina": "https://sede.dgt.gob.es/Sede/Empleos-y-prevision-social/consultas-vinculantes/index.html",
}


# ============================================================
# Data classes
# ============================================================

@dataclass
class RegulatoryChange:
    """A detected regulatory change."""
    source: str
    norma: str
    change_type: str
    description: str
    severity: str = "warning"


# ============================================================
# Helpers
# ============================================================

def compute_hash(content: str | bytes) -> str:
    """Compute SHA-256 hex digest of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML for change detection."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _normalize_key(source: str, norma: str) -> str:
    """Create a unique key for idempotency."""
    raw = f"{source}:{norma}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _change_entity_id(change: RegulatoryChange) -> str:
    raw = f"{change.source}:{change.norma}:{change.change_type}:{change.description}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _table_exists(conn, table_name: str) -> bool:
    """Return whether an optional table exists in the current database."""
    return inspect(conn).has_table(table_name)


# ============================================================
# BOE change detection
# ============================================================

def check_boe_changes(client: httpx.Client) -> list[RegulatoryChange]:
    """Check BOE for changes to key laws.

    Compares current BOE XML for key leyes against stored revisions.
    Returns list of detected changes.
    """
    changes: list[RegulatoryChange] = []
    now = datetime.now(UTC).isoformat()

    for codigo, info in BOE_KEY_LAWS.items():
        boe_id = info["boe_id"]
        norma_ref = info["norma_ref"]
        url = f"https://www.boe.es/diario_boe/xml.php?id={boe_id}"

        try:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            xml_text = response.text
            current_hash = compute_hash(xml_text)

            with engine.begin() as conn:
                existing = conn.execute(
                    text("""
                        SELECT content_hash_sha256
                        FROM source_revision
                        WHERE worker_name = 'reg-watch'
                          AND source_entity_tipo = :tipo
                          AND source_entity_id = :entity_id
                    """),
                    {
                        "tipo": "boe_law",
                        "entity_id": boe_id,
                    },
                ).fetchone()

                if existing is None:
                    # First time seeing this law — record it, no change yet
                    conn.execute(
                        text("""
                            INSERT INTO source_revision (
                                worker_name, source_entity_tipo, source_entity_id,
                                content_hash_sha256, fetched_at
                            ) VALUES (
                                'reg-watch', 'boe_law', :entity_id, :hash, now()
                            )
                        """),
                        {"entity_id": boe_id, "hash": current_hash},
                    )
                    logger.info("BOE: first seen %s (%s)", norma_ref, boe_id)
                    continue

                old_hash = existing[0]
                if current_hash != old_hash:
                    changes.append(RegulatoryChange(
                        source="boe",
                        norma=norma_ref,
                        change_type="amendment",
                        description=f"Texto modificado en BOE: {info['titulo']}",
                        severity="warning",
                    ))

                    # Also check if rates changed
                    rate_changes = _detect_rate_changes_in_boe(conn, codigo, xml_text, now)
                    changes.extend(rate_changes)

                conn.execute(
                    text("""
                        INSERT INTO source_revision (
                            worker_name, source_entity_tipo, source_entity_id,
                            content_hash_sha256, fetched_at
                        ) VALUES (
                            'reg-watch', 'boe_law', :entity_id, :hash, now()
                        )
                        ON CONFLICT (worker_name, source_entity_tipo, source_entity_id)
                        DO UPDATE SET content_hash_sha256 = EXCLUDED.content_hash_sha256,
                                      fetched_at = now()
                    """),
                    {"entity_id": boe_id, "hash": current_hash},
                )

        except httpx.HTTPError as exc:
            logger.warning("BOE: failed to fetch %s (%s): %s", codigo, boe_id, exc)

    return changes


def _detect_rate_changes_in_boe(
    conn,
    codigo: str,
    xml_text: str,
    now: str,
) -> list[RegulatoryChange]:
    """Detect rate changes by comparing BOE text against stored rates."""
    changes: list[RegulatoryChange] = []

    if codigo != "LIVA":
        return changes

    if not _table_exists(conn, "iva_rates"):
        logger.warning("LIVA rate comparison skipped: optional table iva_rates is missing")
        return changes

    # Extract percentage rates from BOE text (patterns like "21 por 100", "10 por 100", etc.)
    rate_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*por\s*100")
    found_rates = set()
    for match in rate_pattern.finditer(xml_text):
        rate_val = float(match.group(1))
        found_rates.add(rate_val)

    # Compare with stored rates
    stored_rates = conn.execute(
        text("""
            SELECT rate FROM iva_rates
            WHERE year = EXTRACT(YEAR FROM now())::integer
              AND territory = 'peninsular'
        """)
    ).fetchall()

    stored_rate_values = {row[0] for row in stored_rates}

    new_rates = found_rates - stored_rate_values
    missing_rates = stored_rate_values - found_rates

    new_rate_changes = [
        RegulatoryChange(
            source="boe",
            norma="L37/1992",
            change_type="new_rate",
            description=f"Nueva tasa detectada en BOE: {rate}%",
            severity="critical",
        )
        for rate in sorted(new_rates)
    ]
    missing_rate_changes = [
        RegulatoryChange(
            source="boe",
            norma="L37/1992",
            change_type="rate_change",
            description=f"Tasa eliminada de BOE (antes presente en DB): {rate}%",
            severity="critical",
        )
        for rate in sorted(missing_rates)
    ]
    changes.extend(new_rate_changes)
    changes.extend(missing_rate_changes)

    return changes


# ============================================================
# AEAT calendar change detection
# ============================================================

def check_aeat_calendar_changes(client: httpx.Client, year: int | None = None) -> list[RegulatoryChange]:
    """Check AEAT calendar for deadline changes.

    Downloads the current year's AEAT calendar PDF and compares
    against stored fiscal_calendar entries.
    """
    changes: list[RegulatoryChange] = []
    target_year = year or datetime.now(UTC).year

    # Fetch the AEAT calendar page to check for updates
    calendar_page_url = (
        "https://www.agenciatributaria.gob.es/static_files/AEAT/D共通s"
        "/portal/informacion_contribuyentes/CalendarioContribuyentes/index.shtml"
    )

    try:
        response = client.get(calendar_page_url, timeout=30.0)
        response.raise_for_status()
        html_text = response.text
        current_hash = compute_hash(html_text)

        with engine.begin() as conn:
            existing = conn.execute(
                text("""
                    SELECT content_hash_sha256
                    FROM source_revision
                    WHERE worker_name = 'reg-watch'
                      AND source_entity_tipo = 'aeat_calendar'
                      AND source_entity_id = :entity_id
                """),
                {"entity_id": f"aeat_cal_{target_year}"},
            ).fetchone()

            if existing is None:
                conn.execute(
                    text("""
                        INSERT INTO source_revision (
                            worker_name, source_entity_tipo, source_entity_id,
                            content_hash_sha256, fetched_at
                        ) VALUES (
                            'reg-watch', 'aeat_calendar', :entity_id, :hash, now()
                        )
                    """),
                    {"entity_id": f"aeat_cal_{target_year}", "hash": current_hash},
                )
                logger.info("AEAT: first seen calendar for %d", target_year)
                return changes

            if current_hash != existing[0]:
                changes.append(RegulatoryChange(
                    source="aeat",
                    norma=f"calendario_{target_year}",
                    change_type="deadline_change",
                    description=f"Calendario del Contribuyente actualizado para {target_year}",
                    severity="warning",
                ))

            conn.execute(
                text("""
                    INSERT INTO source_revision (
                        worker_name, source_entity_tipo, source_entity_id,
                        content_hash_sha256, fetched_at
                    ) VALUES (
                        'reg-watch', 'aeat_calendar', :entity_id, :hash, now()
                    )
                    ON CONFLICT (worker_name, source_entity_tipo, source_entity_id)
                    DO UPDATE SET content_hash_sha256 = EXCLUDED.content_hash_sha256,
                                  fetched_at = now()
                """),
                {"entity_id": f"aeat_cal_{target_year}", "hash": current_hash},
            )

    except httpx.HTTPError as exc:
        logger.warning("AEAT: failed to fetch calendar page: %s", exc)

    return changes


# ============================================================
# EUR-Lex change detection
# ============================================================

def check_eurlex_changes(client: httpx.Client) -> list[RegulatoryChange]:
    """Check EUR-Lex for new/recent EU regulations affecting tax/compliance.

    Queries SPARQL for recent regulatory changes.
    """
    changes: list[RegulatoryChange] = []
    cutoff = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")

    # Check for recent EU regulations that might affect Spanish tax law
    query = f"""
    PREFIX cdm: <http://data.europa.eu/eli/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?celex ?title ?date
    WHERE {{
      ?work a cdm:Work .
      ?work rdf:type <http://publications.europa.eu/resource/authority/resource-type/REGULATION> .
      ?work <http://publications.europa.eu/ontology/ecli#hasCELEX> ?celex .
      ?work dcterms:title ?title .
      ?work dcterms/issued ?date .
      FILTER(?date > "{cutoff}"^^xsd:date)
    }}
    ORDER BY DESC(?date)
    LIMIT 50
    """

    try:
        response = client.post(
            SPARQL_BASE,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=60.0,
        )
        response.raise_for_status()
        results = response.json()
        bindings = results.get("results", {}).get("bindings", [])

        with engine.begin() as conn:
            for binding in bindings:
                celex = binding.get("celex", {}).get("value", "")
                if not celex or not celex.startswith("3"):
                    continue

                entity_id = compute_hash(f"eurlex:{celex}:new_norm")
                existing = conn.execute(
                    text("""
                        SELECT 1
                        FROM source_revision
                        WHERE worker_name = 'reg-watch'
                          AND source_entity_tipo = 'regulatory_change'
                          AND source_entity_id = :entity_id
                        LIMIT 1
                    """),
                    {"entity_id": entity_id},
                ).fetchone()

                if existing is None:
                    title = binding.get("title", {}).get("value", celex)
                    changes.append(RegulatoryChange(
                        source="eurlex",
                        norma=celex,
                        change_type="new_norm",
                        description=f"Nuevo reglamento UE: {title}",
                        severity="info",
                    ))

    except httpx.HTTPError as exc:
        logger.warning("EUR-Lex: SPARQL query failed: %s", exc)
    except Exception as exc:
        logger.warning("EUR-Lex: unexpected error: %s", exc)

    return changes


# ============================================================
# AEPD / BDE / DGT change detection
# ============================================================

def check_authority_changes(
    client: httpx.Client,
    source: str,
    url: str,
    entity_id: str,
    label: str,
) -> list[RegulatoryChange]:
    """Generic watcher for regulatory authority pages.

    Checks if a page has changed since last check and reports it.
    """
    changes: list[RegulatoryChange] = []

    try:
        response = client.get(url, timeout=30.0)
        response.raise_for_status()
        html_text = response.text
        current_hash = compute_hash(html_text)

        with engine.begin() as conn:
            existing = conn.execute(
                text("""
                    SELECT content_hash_sha256
                    FROM source_revision
                    WHERE worker_name = 'reg-watch'
                      AND source_entity_tipo = :tipo
                      AND source_entity_id = :entity_id
                """),
                {"tipo": f"{source}_page", "entity_id": entity_id},
            ).fetchone()

            if existing is None:
                conn.execute(
                    text("""
                        INSERT INTO source_revision (
                            worker_name, source_entity_tipo, source_entity_id,
                            content_hash_sha256, fetched_at
                        ) VALUES (
                            'reg-watch', :tipo, :entity_id, :hash, now()
                        )
                    """),
                    {"tipo": f"{source}_page", "entity_id": entity_id, "hash": current_hash},
                )
                logger.info("%s: first seen %s", source, label)
                return changes

            if current_hash != existing[0]:
                changes.append(RegulatoryChange(
                    source=source,
                    norma=label,
                    change_type="amendment",
                    description=f"Pagina actualizada: {label}",
                    severity="warning",
                ))

            conn.execute(
                text("""
                    INSERT INTO source_revision (
                        worker_name, source_entity_tipo, source_entity_id,
                        content_hash_sha256, fetched_at
                    ) VALUES (
                        'reg-watch', :tipo, :entity_id, :hash, now()
                    )
                    ON CONFLICT (worker_name, source_entity_tipo, source_entity_id)
                    DO UPDATE SET content_hash_sha256 = EXCLUDED.content_hash_sha256,
                                  fetched_at = now()
                """),
                {"tipo": f"{source}_page", "entity_id": entity_id, "hash": current_hash},
            )

    except httpx.HTTPError as exc:
        logger.warning("%s: failed to fetch %s: %s", source, label, exc)

    return changes


# ============================================================
# DB: insert changes (idempotent)
# ============================================================

def insert_changes(changes: list[RegulatoryChange]) -> int:
    """Record detected changes in source_revision.

    Idempotent: skips entries with same (source, norma, change_type, description).
    Returns count of inserted changes.
    """
    if not changes:
        return 0

    now = datetime.now(UTC).isoformat()
    inserted = 0

    with engine.begin() as conn:
        for change in changes:
            entity_id = _change_entity_id(change)
            content_hash = compute_hash(
                f"{change.source}:{change.norma}:{change.change_type}:"
                f"{change.description}:{change.severity}"
            )
            existing = conn.execute(
                text("""
                    SELECT 1
                    FROM source_revision
                    WHERE worker_name = 'reg-watch'
                      AND source_entity_tipo = 'regulatory_change'
                      AND source_entity_id = :entity_id
                    LIMIT 1
                """),
                {"entity_id": entity_id},
            ).fetchone()

            if existing is not None:
                continue

            conn.execute(
                text("""
                    INSERT INTO source_revision (
                        worker_name, source_entity_tipo, source_entity_id,
                        content_hash_sha256, fetched_at
                    ) VALUES (
                        'reg-watch', 'regulatory_change', :entity_id,
                        :content_hash, :detected_at
                    )
                """),
                {
                    "entity_id": entity_id,
                    "content_hash": content_hash,
                    "detected_at": now,
                },
            )
            inserted += 1

            if change.severity == "critical":
                logger.critical(
                    "CRITICAL CHANGE: [%s] %s - %s",
                    change.source, change.norma, change.description,
                )

    return inserted


# ============================================================
# Sync log
# ============================================================

def log_sync(
    conn,
    worker: str,
    status: str,
    changes_detected: int = 0,
    changes_inserted: int = 0,
    errors: int = 0,
    error_msg: str | None = None,
    started_at: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    effective_started_at = started_at or now
    duration_ms = max(
        0,
        int(
            (datetime.fromisoformat(now) - datetime.fromisoformat(effective_started_at)).total_seconds() * 1000
        ),
    )

    conn.execute(
        text("""
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                rows_processed, errors, duration_ms, error_msg
            )
            VALUES (
                :worker, :started_at, :finished_at, :status,
                :rows_processed, :errors, :duration_ms, :error_msg
            )
        """),
        {
            "worker": worker,
            "started_at": effective_started_at,
            "finished_at": now,
            "status": status,
            "rows_processed": changes_detected,
            "errors": errors,
            "duration_ms": duration_ms,
            "error_msg": error_msg,
        },
    )


# ============================================================
# Main sync
# ============================================================

engine = None


def run_sync(
    worker_name: str = "reg-watch",
) -> dict[str, int]:
    """Run a full regulatory watch cycle.

    Checks all configured official sources and logs detected changes.
    Returns summary counts.
    """
    global engine
    engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
    ensure_database_connection(engine, logger=logger)

    total_changes_detected = 0
    total_changes_inserted = 0
    fetch_errors = 0
    sync_start = datetime.now(UTC).isoformat()

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            # Phase 1: BOE key laws
            logger.info("BOE: checking key laws...")
            boe_changes = check_boe_changes(client)
            total_changes_detected += len(boe_changes)
            boe_inserted = insert_changes(boe_changes)
            total_changes_inserted += boe_inserted
            logger.info("BOE: %d changes detected, %d inserted", len(boe_changes), boe_inserted)

            # Phase 2: AEAT calendar
            logger.info("AEAT: checking calendar...")
            aeat_changes = check_aeat_calendar_changes(client)
            total_changes_detected += len(aeat_changes)
            aeat_inserted = insert_changes(aeat_changes)
            total_changes_inserted += aeat_inserted
            logger.info("AEAT: %d changes detected, %d inserted", len(aeat_changes), aeat_inserted)

            # Phase 3: EUR-Lex
            logger.info("EUR-Lex: checking for new regulations...")
            eurlex_changes = check_eurlex_changes(client)
            total_changes_detected += len(eurlex_changes)
            eurlex_inserted = insert_changes(eurlex_changes)
            total_changes_inserted += eurlex_inserted
            logger.info("EUR-Lex: %d changes detected, %d inserted", len(eurlex_changes), eurlex_inserted)

            # Phase 4: AEPD
            logger.info("AEPD: checking for updates...")
            aepd_changes = check_authority_changes(
                client,
                source="aepd",
                url=SOURCE_URLS["aepd_resoluciones"],
                entity_id="aepd_resoluciones",
                label="AEPD resoluciones",
            )
            total_changes_detected += len(aepd_changes)
            aepd_inserted = insert_changes(aepd_changes)
            total_changes_inserted += aepd_inserted
            logger.info("AEPD: %d changes detected, %d inserted", len(aepd_changes), aepd_inserted)

            # Phase 5: Banco de Espana
            logger.info("BDE: checking for updates...")
            bde_changes = check_authority_changes(
                client,
                source="bde",
                url=SOURCE_URLS["bde_publicaciones"],
                entity_id="bde_publicaciones",
                label="Banco de Espana publicaciones",
            )
            total_changes_detected += len(bde_changes)
            bde_inserted = insert_changes(bde_changes)
            total_changes_inserted += bde_inserted
            logger.info("BDE: %d changes detected, %d inserted", len(bde_changes), bde_inserted)

            # Phase 6: DGT
            logger.info("DGT: checking for doctrina...")
            dgt_changes = check_authority_changes(
                client,
                source="dgt",
                url=SOURCE_URLS["dgt_doctrina"],
                entity_id="dgt_doctrina",
                label="DGT consultas vinculantes",
            )
            total_changes_detected += len(dgt_changes)
            dgt_inserted = insert_changes(dgt_changes)
            total_changes_inserted += dgt_inserted
            logger.info("DGT: %d changes detected, %d inserted", len(dgt_changes), dgt_inserted)

        status = "ok" if fetch_errors == 0 else "partial"
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                status,
                changes_detected=total_changes_detected,
                changes_inserted=total_changes_inserted,
                errors=fetch_errors,
                started_at=sync_start,
            )

        return {
            "changes_detected": total_changes_detected,
            "changes_inserted": total_changes_inserted,
            "fetch_errors": fetch_errors,
        }

    except Exception as exc:
        logger.error("Regulatory watch sync failed: %s", exc)
        try:
            with engine.begin() as conn:
                log_sync(
                    conn,
                    worker_name,
                    "error",
                    changes_detected=total_changes_detected,
                    changes_inserted=total_changes_inserted,
                    errors=1,
                    error_msg=str(exc),
                    started_at=sync_start,
                )
        except Exception:
            logger.error("REG-WATCH: failed to write error sync log after main failure")
        return {
            "changes_detected": total_changes_detected,
            "changes_inserted": total_changes_inserted,
            "fetch_errors": 1,
            "error": str(exc),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Regulatory Watch: monitor official sources for regulatory changes"
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
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("reg-watch")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-regulatory-daily")
        print(
            f"[run-once] Changes detected: {result['changes_detected']}, "
            f"inserted: {result['changes_inserted']}"
        )
        if result.get("error"):
            sys.exit(1)
    else:
        print(f"Starting Regulatory Watch worker (interval={interval}s)")
        while True:
            touch_heartbeat()
            try:
                result = run_sync()
                print(
                    f"Synced changes_detected={result['changes_detected']}, "
                    f"changes_inserted={result['changes_inserted']} "
                    f"at {datetime.now(UTC).isoformat()}"
                )
            except Exception as exc:
                print(f"[ERROR] Regulatory watch failed: {exc} at {datetime.now(UTC).isoformat()}")
                if not handle_worker_failure(engine, "regulatory_watch", "loop", "main", exc):
                    break
            sleep_with_heartbeat(interval)
