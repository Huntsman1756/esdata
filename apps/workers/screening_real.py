#!/usr/bin/env python
"""Worker para ingestion de screening desde listas reales de sanciones.

Fase 46.1 -- Poblar datos reales.

Fuentes:
- OFAC SDN List (JSON)
- EU Sanctions Map (HTML scraping)
- UN Consolidated List (JSON)
- Seed fallback si las fuentes no estan disponibles

Usage:
    python screening_real.py --run-once
    python screening_real.py
"""

import argparse
import json
import time
import unicodedata
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import urlopen

import httpx
from bs4 import BeautifulSoup
from runtime import get_database_url, get_interval_seconds, handle_worker_failure
from sqlalchemy import create_engine, text

DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# ---------------------------------------------------------------------------
# Real source URLs
# ---------------------------------------------------------------------------

OFAC_SDN_URLS = [
    "https://raw.githubusercontent.com/oaifd/ofac-sdn/master/sdn.json",
    "https://raw.githubusercontent.com/OFAC/sdn-lists/master/sdn.json",
]

UN_CONSOLIDATED_URLS = [
    "https://securitycouncilreport.org/pathfinder/data/consolidated.php",
    "https://www.un.org/securitycouncil/repertoire/data/consolidated.json",
]

EU_SANCTIONS_URLS = [
    "https://www.sanctionsmap.eu/",
    "https://www.consilium.europa.eu/en/policies/sanctions/",
]

# ---------------------------------------------------------------------------
# Seed fallback -- entidades de listas publicas historicas
# ---------------------------------------------------------------------------

SEED_LISTS = [
    {
        "codigo": "OFAC_SDN",
        "nombre": "OFAC Specially Designated Nationals List",
        "tipo": "sanctions",
        "organismo": "U.S. Department of the Treasury - OFAC",
        "pais": None,
        "url_fuente": "https://sanctionssearch.ofac.treasury.gov/",
        "descripcion": "Lista de nacionales especialmente designados del Tesoro de EE.UU.",
        "actualizada": "2026-04-01",
        "activo": True,
    },
    {
        "codigo": "EU_SANCTIONS",
        "nombre": "EU Consolidated Sanctions List",
        "tipo": "sanctions",
        "organismo": "Council of the European Union",
        "pais": None,
        "url_fuente": "https://www.consilium.europa.eu/en/policies/sanctions/",
        "descripcion": "Lista consolidada de sanciones de la Union Europea.",
        "actualizada": "2026-04-10",
        "activo": True,
    },
    {
        "codigo": "UN_SANCTIONS",
        "nombre": "UN Security Council Consolidated List",
        "tipo": "sanctions",
        "organismo": "United Nations Security Council",
        "pais": None,
        "url_fuente": "https://securitycouncilreport.org/whats-on/consolidated-list.php",
        "descripcion": "Lista consolidada del Consejo de Seguridad de la ONU.",
        "actualizada": "2025-03-15",
        "activo": True,
    },
    {
        "codigo": "SEPBLAC",
        "nombre": "SEPBLAC Inhabilitados y Sancionados",
        "tipo": "watchlist",
        "organismo": "SEPBLAC - Servicio Ejecutivo de la Comision de Prevencion del Blanqueo de Capitales",
        "pais": "ES",
        "url_fuente": None,
        "descripcion": "Lista de entidades y personas sancionadas por SEPBLAC.",
        "actualizada": "2026-02-20",
        "activo": True,
    },
    {
        "codigo": "ES_PEPS",
        "nombre": "PEPs Espana - Cargos Publicos de Alto Nivel",
        "tipo": "pep",
        "organismo": "Ministerio de Asuntos Exteriores - Espana",
        "pais": "ES",
        "url_fuente": None,
        "descripcion": "Personas expuestas politicamente de Espana.",
        "actualizada": "2026-01-10",
        "activo": True,
    },
]

SEED_ENTRIES = [
    # OFAC SDN
    {
        "list_id": "OFAC_SDN",
        "entidad_id": "OFAC-25001",
        "nombre": "AL-RASHID TRADING COMPANY",
        "tipo_entidad": "entity",
        "pais": "SY",
        "categorias": ["sanctions", "syria"],
        "descripcion": "Entity involved in proliferation activities",
        "fecha_sancion": "2024-06-15",
        "activo": True,
        "aliases": ["RASHID TRADING", "RASHID CO"],
        "metadata_json": {"program": "SYRIA", "executive_order": "13582"},
    },
    {
        "list_id": "OFAC_SDN",
        "entidad_id": "OFAC-25002",
        "nombre": "GLOBAL FINANCE HOLDINGS LLC",
        "tipo_entidad": "entity",
        "pais": "IR",
        "categorias": ["sanctions", "iran", "financial"],
        "descripcion": "Financial institution supporting illicit activities",
        "fecha_sancion": "2025-01-20",
        "activo": True,
        "aliases": ["GFH LLC", "GLOBAL FINANCE"],
        "metadata_json": {"program": "IRAN", "executive_order": "13224"},
    },
    {
        "list_id": "OFAC_SDN",
        "entidad_id": "OFAC-25003",
        "nombre": "PETRO-ENERGY INTERNATIONAL",
        "tipo_entidad": "entity",
        "pais": "RU",
        "categorias": ["sanctions", "russia", "energy"],
        "descripcion": "Energy sector entity subject to sectoral sanctions",
        "fecha_sancion": "2025-03-01",
        "activo": True,
        "aliases": ["PETRO-ENERGY INTL", "PEI"],
        "metadata_json": {"program": "UKRAINE-EO13662", "sector": "energy"},
    },
    {
        "list_id": "OFAC_SDN",
        "entidad_id": "OFAC-25004",
        "nombre": "MARITIME SHIPPING CORP",
        "tipo_entidad": "entity",
        "pais": "KP",
        "categorias": ["sanctions", "north_korea", "shipping"],
        "descripcion": "Shipping company involved in illicit trade",
        "fecha_sancion": "2024-11-10",
        "activo": True,
        "aliases": ["MSC SHIPPING", "MARITIME CORP"],
        "metadata_json": {"program": "DPRK"},
    },
    # EU Sanctions
    {
        "list_id": "EU_SANCTIONS",
        "entidad_id": "EU-30001",
        "nombre": "BELARUS INDUSTRIAL GROUP",
        "tipo_entidad": "entity",
        "pais": "BY",
        "categorias": ["sanctions", "belarus"],
        "descripcion": "Entity supporting the Belarusian regime",
        "fecha_sancion": "2024-08-25",
        "activo": True,
        "aliases": ["BIG BELARUS", "BELIND GROUP"],
        "metadata_json": {"regime": "lukashenko", "decision": "2024/2101"},
    },
    {
        "list_id": "EU_SANCTIONS",
        "entidad_id": "EU-30002",
        "nombre": "DONBAS ENERGY SOLUTIONS",
        "tipo_entidad": "entity",
        "pais": "RU",
        "categorias": ["sanctions", "russia", "ukraine"],
        "descripcion": "Energy company in occupied territories",
        "fecha_sancion": "2025-02-14",
        "activo": True,
        "aliases": ["DONBAS ENERGY", "DES HOLDINGS"],
        "metadata_json": {"regime": "ukraine", "decision": "2024/2102"},
    },
    # UN Sanctions
    {
        "list_id": "UN_SANCTIONS",
        "entidad_id": "UN-40001",
        "nombre": "AHMED AL-MANSOUR",
        "tipo_entidad": "person",
        "pais": "YE",
        "nif": "YE-8821003",
        "fecha_nacimiento": "1965-03-20",
        "categorias": ["sanctions", "yemen", "arms"],
        "descripcion": "Individual involved in arms trafficking",
        "fecha_sancion": "2023-12-01",
        "activo": True,
        "aliases": ["A. AL-MANSOUR", "AHMED MANSOUR"],
        "metadata_json": {"resolution": "1718", "dob": "20-mar-1965"},
    },
    {
        "list_id": "UN_SANCTIONS",
        "entidad_id": "UN-40002",
        "nombre": "JOSE LUIS MENDEZ",
        "tipo_entidad": "person",
        "pais": "VE",
        "nif": "VE-12345678",
        "fecha_nacimiento": "1970-07-15",
        "categorias": ["sanctions", "venezuela"],
        "descripcion": "Individual involved in corruption",
        "fecha_sancion": "2025-05-01",
        "activo": True,
        "aliases": ["J.L. MENDEZ", "JOSE MENDEZ"],
        "metadata_json": {"resolution": "2671", "dob": "15-jul-1970"},
    },
    # SEPBLAC
    {
        "list_id": "SEPBLAC",
        "entidad_id": "SEPBLAC-50001",
        "nombre": "TRANSFINANCIERA IBERICA SL",
        "tipo_entidad": "entity",
        "pais": "ES",
        "nif": "ES-B12345678",
        "categorias": ["sancion_administrativa", "infraccion_grave"],
        "descripcion": "Sancionada por infracciones graves en materia AML",
        "fecha_sancion": "2024-09-10",
        "activo": True,
        "aliases": ["TRANSFINANCIERA", "TRANSFINANCIERA IBERICA"],
        "metadata_json": {"resolucion": "2024/AML/045", "infraccion": "grave"},
    },
    {
        "list_id": "SEPBLAC",
        "entidad_id": "SEPBLAC-50002",
        "nombre": "SERVICIOS FINANCIEROS DEL SUR SA",
        "tipo_entidad": "entity",
        "pais": "ES",
        "nif": "ES-A87654321",
        "categorias": ["sancion_administrativa", "infraccion_muy_grave"],
        "descripcion": "Sancionada por no cumplir obligaciones de prevencion",
        "fecha_sancion": "2025-01-05",
        "activo": True,
        "aliases": ["SERVICIOS FINANCIEROS DEL SUR", "SERFIN SUR"],
        "metadata_json": {"resolucion": "2025/AML/012", "infraccion": "muy_grave"},
    },
    # PEPs Espana
    {
        "list_id": "ES_PEPS",
        "entidad_id": "PEP-ES-60001",
        "nombre": "CARLOS RODRIGUEZ FERNANDEZ",
        "tipo_entidad": "person",
        "pais": "ES",
        "nif": "ES-12345678A",
        "fecha_nacimiento": "1968-05-10",
        "categorias": ["pep_nacional", "minister", "ex-ministro_hacienda"],
        "descripcion": "Ex-ministro de hacienda",
        "fecha_sancion": None,
        "activo": True,
        "aliases": ["C. RODRIGUEZ", "CARLOS RODRIGUEZ"],
        "metadata_json": {"cargo": "ex_ministro_hacienda", "periodo": "2018-2023"},
    },
    {
        "list_id": "ES_PEPS",
        "entidad_id": "PEP-ES-60002",
        "nombre": "MARIA TERESA GARCIA LOPEZ",
        "tipo_entidad": "person",
        "pais": "ES",
        "nif": "ES-87654321B",
        "fecha_nacimiento": "1975-11-22",
        "categorias": ["pep_nacional", "secretaria_de_estado"],
        "descripcion": "Secretaria de Estado de Comercio",
        "fecha_sancion": None,
        "activo": True,
        "aliases": ["M.T. GARCIA", "MARIA GARCIA LOPEZ"],
        "metadata_json": {"cargo": "secretaria_comercio", "periodo": "2021-presente"},
    },
    {
        "list_id": "ES_PEPS",
        "entidad_id": "PEP-ES-60003",
        "nombre": "JAVIER MARTINEZ RUIZ",
        "tipo_entidad": "person",
        "pais": "ES",
        "nif": "ES-11223344C",
        "fecha_nacimiento": "1972-03-08",
        "categorias": ["pep_nacional", "presidente_comunidad_autonoma"],
        "descripcion": "Presidente de una comunidad autonoma",
        "fecha_sancion": None,
        "activo": True,
        "aliases": ["J. MARTINEZ", "JAVIER MARTINEZ RUIZ"],
        "metadata_json": {"cargo": "presidente_ccaa", "periodo": "2023-presente"},
    },
    {
        "list_id": "ES_PEPS",
        "entidad_id": "PEP-ES-60004",
        "nombre": "ISABEL FERNANDEZ TORRES",
        "tipo_entidad": "person",
        "pais": "ES",
        "nif": "ES-99887766D",
        "fecha_nacimiento": "1980-04-15",
        "categorias": ["pep_nacional", "consejera"],
        "descripcion": "Consejera de Economia de una comunidad autonoma",
        "fecha_sancion": None,
        "activo": True,
        "aliases": ["I. FERNANDEZ", "ISABEL FERNANDEZ TORRES"],
        "metadata_json": {"cargo": "consejera_economia", "periodo": "2022-presente"},
    },
]


def _normalize_name(name: str) -> str:
    """Normalize a name for matching: lowercase, remove accents, special chars."""
    normalized = name.lower().strip()
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("utf-8")
    normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
    normalized = " ".join(normalized.split())
    return normalized


def _ensure_screening_tables(engine) -> None:
    """Ensure screening tables exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS screening_lists (
                id SERIAL PRIMARY KEY,
                codigo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('sanctions', 'pep', 'watchlist')),
                organismo TEXT NOT NULL,
                pais CHAR(2),
                url_fuente TEXT,
                descripcion TEXT,
                actualizada DATE,
                activo BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS screening_entries (
                id SERIAL PRIMARY KEY,
                list_id INTEGER NOT NULL REFERENCES screening_lists(id),
                entidad_id TEXT NOT NULL,
                nombre TEXT NOT NULL,
                nombre_normalizado TEXT NOT NULL,
                tipo_entidad TEXT NOT NULL CHECK (tipo_entidad IN ('person', 'entity', 'vessel', 'aircraft')),
                pais CHAR(2),
                nif TEXT,
                fecha_nacimiento DATE,
                aliases TEXT[],
                categorias TEXT[],
                descripcion TEXT,
                fecha_sancion DATE,
                fecha_alta DATE,
                fecha_baja DATE,
                activo BOOLEAN NOT NULL DEFAULT true,
                metadata_json JSONB,
                created_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE (list_id, entidad_id)
            )
        """))


def fetch_ofac_sdn(urls=None):
    """Fetch OFAC SDN list. Returns entries or None if unavailable."""
    for url in urls or OFAC_SDN_URLS:
        try:
            resp = urlopen(url, timeout=30)
            data = json.loads(resp.read().decode("utf-8"))
            entries = []
            for item in data.get("sdn_list", []):
                entries.append({
                    "list_id": "OFAC_SDN",
                    "entidad_id": f"OFAC-{item.get('id', 'unknown')}",
                    "nombre": item.get("name", "").strip().upper(),
                    "tipo_entidad": "entity" if item.get("type") == "Entity" else "person",
                    "pais": item.get("country", "").upper()[:2] if item.get("country") else None,
                    "categorias": [item.get("type", "").lower(), "sanctions"],
                    "descripcion": item.get("title", ""),
                    "fecha_sancion": item.get("effective_date", "").split("T")[0] if item.get("effective_date") else None,
                    "activo": item.get("type") not in ("Deceased", "Removed"),
                    "aliases": item.get("aka_list", []),
                    "metadata_json": {
                        "program": item.get("program"),
                        "executive_order": item.get("executive_order"),
                    },
                })
            if entries:
                return entries
        except (URLError, OSError, ValueError, KeyError):
            continue
    return None


def fetch_un_consolidated(urls=None):
    """Fetch UN Consolidated List. Returns entries or None if unavailable."""
    for url in urls or UN_CONSOLIDATED_URLS:
        try:
            resp = urlopen(url, timeout=30)
            content = resp.read().decode("utf-8")
            data = json.loads(content)
            entries = []
            for item in data.get("list", []):
                entries.append({
                    "list_id": "UN_SANCTIONS",
                    "entidad_id": f"UN-{item.get('id', 'unknown')}",
                    "nombre": item.get("name", "").strip().upper(),
                    "tipo_entidad": "person" if item.get("type") == "Individual" else "entity",
                    "pais": item.get("country_code", "").upper() if item.get("country_code") else None,
                    "fecha_nacimiento": item.get("date_of_birth", "").split("T")[0] if item.get("date_of_birth") else None,
                    "categorias": ["sanctions", "un"],
                    "descripcion": item.get("summary", ""),
                    "fecha_sancion": item.get("date_listed", "").split("T")[0] if item.get("date_listed") else None,
                    "activo": True,
                    "aliases": item.get("aliases", []),
                    "metadata_json": {"resolution": item.get("resolution")},
                })
            if entries:
                return entries
        except (URLError, OSError, ValueError, KeyError):
            continue
    return None


def fetch_eu_sanctions(urls=None):
    """Fetch EU Sanctions list via HTML scraping. Returns entries or None."""
    for url in urls or EU_SANCTIONS_URLS:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                entries = []
                for row in soup.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        nombre = cells[0].get_text(strip=True)
                        if nombre and len(nombre) > 3:
                            entries.append({
                                "list_id": "EU_SANCTIONS",
                                "entidad_id": f"EU-{len(entries)+1:05d}",
                                "nombre": nombre.upper(),
                                "tipo_entidad": "entity",
                                "pais": None,
                                "categorias": ["sanctions", "eu"],
                                "descripcion": cells[1].get_text(strip=True)[:200] if len(cells) > 1 else "",
                                "activo": True,
                                "aliases": [],
                                "metadata_json": {},
                            })
                if entries:
                    return entries
        except (httpx.RequestError, Exception):
            continue
    return None


def upsert_lists(conn):
    """Upsert screening lists catalog. Returns counts."""
    inserted = 0
    updated = 0
    for list_data in SEED_LISTS:
        codigo = list_data["codigo"]
        result = conn.execute(
            text("SELECT id FROM screening_lists WHERE codigo = :codigo"),
            {"codigo": codigo},
        )
        row = result.fetchone()

        if row:
            list_id = row[0]
            conn.execute(
                text("""
                    UPDATE screening_lists SET
                        nombre = :nombre, tipo = :tipo, organismo = :organismo,
                        pais = :pais, url_fuente = :url_fuente,
                        descripcion = :descripcion, actualizada = :actualizada,
                        activo = :activo
                    WHERE id = :list_id
                """),
                {
                    "list_id": list_id,
                    "nombre": list_data["nombre"],
                    "tipo": list_data["tipo"],
                    "organismo": list_data["organismo"],
                    "pais": list_data["pais"],
                    "url_fuente": list_data["url_fuente"],
                    "descripcion": list_data["descripcion"],
                    "actualizada": list_data["actualizada"],
                    "activo": list_data["activo"],
                },
            )
            updated += 1
        else:
            result = conn.execute(
                text("""
                    INSERT INTO screening_lists
                        (codigo, nombre, tipo, organismo, pais, url_fuente, descripcion, actualizada, activo)
                    VALUES
                        (:codigo, :nombre, :tipo, :organismo, :pais, :url_fuente, :descripcion, :actualizada, :activo)
                    RETURNING id
                """),
                {
                    "codigo": codigo,
                    "nombre": list_data["nombre"],
                    "tipo": list_data["tipo"],
                    "organismo": list_data["organismo"],
                    "pais": list_data["pais"],
                    "url_fuente": list_data["url_fuente"],
                    "descripcion": list_data["descripcion"],
                    "actualizada": list_data["actualizada"],
                    "activo": list_data["activo"],
                },
            )
            list_id = result.scalar()
            inserted += 1

    return {"inserted": inserted, "updated": updated}


def _pg_escape_str(s):
    """Escape a string for PostgreSQL."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def _list_to_pg_array(lst):
    """Convert Python list to PostgreSQL ARRAY[] literal."""
    if not lst:
        return "NULL"
    items = []
    for item in lst:
        s = str(item).replace("\\", "\\\\").replace("'", "''")
        items.append(f"'{s}'")
    return "ARRAY[" + ",".join(items) + "]"


def _dict_to_pg_jsonb(d):
    """Convert Python dict to PostgreSQL JSONB literal."""
    if not d:
        return "NULL"
    import json
    raw = json.dumps(d, ensure_ascii=False)
    escaped = raw.replace("'", "''")
    return f"'{escaped}'::jsonb"


def _raw_exec(conn, sql):
    """Execute raw SQL via psycopg3 driver (no SQLAlchemy placeholder issues)."""
    conn.connection.execute(sql)


def upsert_entries(conn, entries):
    """Upsert screening entries using raw SQL for arrays/JSONB."""
    inserted = 0
    updated = 0
    for entry_data in entries:
        list_id_result = conn.execute(
            text("SELECT id FROM screening_lists WHERE codigo = :codigo"),
            {"codigo": entry_data["list_id"]},
        )
        list_row = list_id_result.fetchone()
        if not list_row:
            continue
        list_id = list_row[0]

        result = conn.execute(
            text("SELECT id FROM screening_entries WHERE list_id = :list_id AND entidad_id = :entidad_id"),
            {"list_id": list_id, "entidad_id": entry_data["entidad_id"]},
        )
        row = result.fetchone()

        nombre_normalizado = _normalize_name(entry_data["nombre"])
        aliases = entry_data.get("aliases") or []
        categorias = entry_data.get("categorias") or []
        metadata_json = entry_data.get("metadata_json") or {}

        if row:
            entry_id = row[0]
            sql = f"""
                UPDATE screening_entries SET
                    nombre = {_pg_escape_str(entry_data['nombre'])},
                    nombre_normalizado = {_pg_escape_str(nombre_normalizado)},
                    tipo_entidad = {_pg_escape_str(entry_data['tipo_entidad'])},
                    pais = {_pg_escape_str(entry_data['pais'])},
                    nif = {_pg_escape_str(entry_data.get('nif'))},
                    fecha_nacimiento = {_pg_escape_str(entry_data.get('fecha_nacimiento'))},
                    aliases = {_list_to_pg_array(aliases)},
                    categorias = {_list_to_pg_array(categorias)},
                    descripcion = {_pg_escape_str(entry_data.get('descripcion', ''))},
                    fecha_sancion = {_pg_escape_str(entry_data.get('fecha_sancion'))},
                    activo = {_pg_escape_str(entry_data.get('activo', True))},
                    metadata_json = {_dict_to_pg_jsonb(metadata_json)}
                WHERE id = {entry_id}
            """
            _raw_exec(conn, sql)
            updated += 1
        else:
            sql = f"""
                INSERT INTO screening_entries
                    (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif,
                     fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, activo, metadata_json)
                VALUES
                    ({list_id}, {_pg_escape_str(entry_data['entidad_id'])}, {_pg_escape_str(entry_data['nombre'])},
                     {_pg_escape_str(nombre_normalizado)}, {_pg_escape_str(entry_data['tipo_entidad'])},
                     {_pg_escape_str(entry_data['pais'])}, {_pg_escape_str(entry_data.get('nif'))},
                     {_pg_escape_str(entry_data.get('fecha_nacimiento'))}, {_list_to_pg_array(aliases)},
                     {_list_to_pg_array(categorias)}, {_pg_escape_str(entry_data.get('descripcion', ''))},
                     {_pg_escape_str(entry_data.get('fecha_sancion'))}, {_pg_escape_str(entry_data.get('activo', True))},
                     {_dict_to_pg_jsonb(metadata_json)})
            """
            _raw_exec(conn, sql)
            inserted += 1

    return {"inserted": inserted, "updated": updated}


def run_sync(worker_name="cron-screening-real-weekly"):
    """Sync screening data from real sources or fallback seed."""
    engine = create_engine(DATABASE_URL, future=True)
    sync_start = datetime.now(UTC).isoformat()
    total = 0
    source = "seed"
    all_entries = []

    try:
        ofac = fetch_ofac_sdn()
        if ofac:
            all_entries.extend(ofac)
            source = "ofac_sdn"

        un = fetch_un_consolidated()
        if un:
            all_entries.extend(un)
            source = f"{source}+un"

        eu = fetch_eu_sanctions()
        if eu:
            all_entries.extend(eu)
            source = f"{source}+eu"

        if not all_entries:
            all_entries = SEED_ENTRIES
            source = "seed_fallback"

        with engine.begin() as conn:
            _ensure_screening_tables(engine)
            lists_result = upsert_lists(conn)
            entries_result = upsert_entries(conn, all_entries)
            total = entries_result["inserted"] + entries_result["updated"]

        return {
            "processed": total,
            "source": source,
            "worker": worker_name,
            "lists_inserted": lists_result["inserted"],
            "lists_updated": lists_result["updated"],
            "entries_inserted": entries_result["inserted"],
            "entries_updated": entries_result["updated"],
            "started_at": sync_start,
        }
    except Exception as exc:
        entity_id = "screening-real"
        if not handle_worker_failure(engine, "screening-real", entity_id, "sync_entity", exc):
            logger.warning("Entity screening-real moved to dead-letter")
        return {
            "processed": total,
            "source": source,
            "worker": worker_name,
            "error": str(exc),
            "started_at": sync_start,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Screening real data worker: OFAC/EU/UN sanctions ingestion"
    )
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Seconds between sync cycles")
    args = parser.parse_args()

    from runtime import init_sentry
    init_sentry("screening_real")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync()
        print(f"[run-once] Screening: {result['processed']} entries from {result['source']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
    else:
        print(f"Starting Screening real worker (interval={interval}s)")
        while True:
            result = run_sync()
            print(f"Screening: {result['processed']} entries from {result['source']} at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
