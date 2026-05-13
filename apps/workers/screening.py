"""Static screening datasets for testing sanctions and PEPs screening.

These are fictitious entries designed solely for development and testing.
They do not represent real sanctioned entities or PEPs.

Usage:
    python -m workers.screening --run-once
    python -m workers.screening --interval 86400
"""

import os
import sys
import time
import argparse
from datetime import datetime, date, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from runtime import assert_table_exists, get_database_url, ensure_database_connection
except ModuleNotFoundError:  # pragma: no cover - package import path in API tests
    from .runtime import assert_table_exists, get_database_url, ensure_database_connection


# ---------------------------------------------------------------------------
# Screening lists catalog
# ---------------------------------------------------------------------------

SCREENING_LISTS = [
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
        "actualizada": "2026-03-15",
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


# ---------------------------------------------------------------------------
# Screening entries — fictitious test data
# ---------------------------------------------------------------------------

SCREENING_ENTRIES = [
    # OFAC SDN — entities
    {
        "list_id": "OFAC_SDN",
        "entidad_id": "OFAC-25001",
        "nombre": "AL-RASHID TRADING COMPANY",
        "tipo_entidad": "entity",
        "pais": "SY",
        "nif": None,
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
        "nif": None,
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
        "nif": None,
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
        "nif": None,
        "categorias": ["sanctions", "north_korea", "shipping"],
        "descripcion": "Shipping company involved in illicit trade",
        "fecha_sancion": "2024-11-10",
        "activo": True,
        "aliases": ["MSC SHIPPING", "MARITIME CORP"],
        "metadata_json": {"program": "DPRK"},
    },
    # EU Sanctions — entities
    {
        "list_id": "EU_SANCTIONS",
        "entidad_id": "EU-30001",
        "nombre": "BELARUS INDUSTRIAL GROUP",
        "tipo_entidad": "entity",
        "pais": "BY",
        "nif": None,
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
        "nif": None,
        "categorias": ["sanctions", "russia", "ukraine"],
        "descripcion": "Energy company in occupied territories",
        "fecha_sancion": "2025-02-14",
        "activo": True,
        "aliases": ["DONBAS ENERGY", "DES HOLDINGS"],
        "metadata_json": {"regime": "ukraine", "decision": "2024/2102"},
    },
    # UN Sanctions — individuals
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
        "descripcion": "Individual involved in corruption (fictitious test data)",
        "fecha_sancion": "2025-05-01",
        "activo": True,
        "aliases": ["J.L. MENDEZ", "JOSE MENDEZ"],
        "metadata_json": {"resolution": "2671", "dob": "15-jul-1970"},
    },
    # SEPBLAC — watchlist (fictitious)
    {
        "list_id": "SEPBLAC",
        "entidad_id": "SEPBLAC-50001",
        "nombre": "TRANSFINANCIERA IBERICA SL",
        "tipo_entidad": "entity",
        "pais": "ES",
        "nif": "ES-B12345678",
        "categorias": ["sancion_administrativa", "infraccion_grave"],
        "descripcion": "Sancionada por infracciones graves en materia AML (dato ficticio)",
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
        "descripcion": "Sancionada por no cumplir obligaciones de prevencion (dato ficticio)",
        "fecha_sancion": "2025-01-05",
        "activo": True,
        "aliases": ["SERVICIOS FINANCIEROS DEL SUR", "SERFIN SUR"],
        "metadata_json": {"resolucion": "2025/AML/012", "infraccion": "muy_grave"},
    },
    # PEPs Espana — individuals (fictitious test data)
    {
        "list_id": "ES_PEPS",
        "entidad_id": "PEP-ES-60001",
        "nombre": "CARLOS RODRIGUEZ FERNANDEZ",
        "tipo_entidad": "person",
        "pais": "ES",
        "nif": "ES-12345678A",
        "fecha_nacimiento": "1968-05-10",
        "categorias": ["pep_nacional", "minister", "ex-ministro_hacienda"],
        "descripcion": "Ex-ministro de hacienda (dato ficticio para testing)",
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
        "descripcion": "Secretaria de Estado de Comercio (dato ficticio para testing)",
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
        "descripcion": "Presidente de una comunidad autonoma (dato ficticio para testing)",
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
        "descripcion": "Consejera de Economia de una comunidad autonoma (dato ficticio para testing)",
        "fecha_sancion": None,
        "activo": True,
        "aliases": ["I. FERNANDEZ", "ISABEL FERNANDEZ TORRES"],
        "metadata_json": {"cargo": "consejera_economia", "periodo": "2022-presente"},
    },
]


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Normalize a name for matching: lowercase, remove accents, special chars."""
    import unicodedata
    normalized = name.lower().strip()
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("utf-8")
    normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
    normalized = " ".join(normalized.split())
    return normalized


def _ensure_screening_tables(engine) -> None:
    """Assert screening tables exist; schema is Alembic-owned."""
    with engine.begin() as conn:
        assert_table_exists(conn, "screening_lists", required_columns=("codigo", "nombre", "tipo"))
        assert_table_exists(conn, "screening_entries", required_columns=("list_id", "entidad_id", "nombre"))
        assert_table_exists(conn, "screening_matches", required_columns=("empresa_id", "entry_id", "list_id"))


def _upsert_lists(conn) -> dict:
    """Upsert screening lists catalog. Returns counts."""
    inserted = 0
    updated = 0
    for list_data in SCREENING_LISTS:
        codigo = list_data["codigo"]
        # Check if exists
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
                        nombre = :nombre,
                        tipo = :tipo,
                        organismo = :organismo,
                        pais = :pais,
                        url_fuente = :url_fuente,
                        descripcion = :descripcion,
                        actualizada = :actualizada,
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


def _upsert_entries(conn) -> dict:
    """Upsert screening entries. Returns counts."""
    inserted = 0
    updated = 0
    for entry_data in SCREENING_ENTRIES:
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

        if row:
            entry_id = row[0]
            conn.execute(
                text("""
                    UPDATE screening_entries SET
                        nombre = :nombre,
                        nombre_normalizado = :nombre_normalizado,
                        tipo_entidad = :tipo_entidad,
                        pais = :pais,
                        nif = :nif,
                        fecha_nacimiento = :fecha_nacimiento,
                        aliases = :aliases,
                        categorias = :categorias,
                        descripcion = :descripcion,
                        fecha_sancion = :fecha_sancion,
                        activo = :activo,
                        metadata_json = :metadata_json
                    WHERE id = :entry_id
                """),
                {
                    "entry_id": entry_id,
                    "nombre": entry_data["nombre"],
                    "nombre_normalizado": nombre_normalizado,
                    "tipo_entidad": entry_data["tipo_entidad"],
                    "pais": entry_data["pais"],
                    "nif": entry_data["nif"],
                    "fecha_nacimiento": entry_data["fecha_nacimiento"],
                    "aliases": entry_data["aliases"],
                    "categorias": entry_data["categorias"],
                    "descripcion": entry_data["descripcion"],
                    "fecha_sancion": entry_data["fecha_sancion"],
                    "activo": entry_data["activo"],
                    "metadata_json": entry_data["metadata_json"],
                },
            )
            updated += 1
        else:
            result = conn.execute(
                text("""
                    INSERT INTO screening_entries
                        (list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais, nif,
                         fecha_nacimiento, aliases, categorias, descripcion, fecha_sancion, activo, metadata_json)
                    VALUES
                        (:list_id, :entidad_id, :nombre, :nombre_normalizado, :tipo_entidad, :pais, :nif,
                         :fecha_nacimiento, :aliases, :categorias, :descripcion, :fecha_sancion, :activo, :metadata_json)
                    RETURNING id
                """),
                {
                    "list_id": list_id,
                    "entidad_id": entry_data["entidad_id"],
                    "nombre": entry_data["nombre"],
                    "nombre_normalizado": nombre_normalizado,
                    "tipo_entidad": entry_data["tipo_entidad"],
                    "pais": entry_data["pais"],
                    "nif": entry_data["nif"],
                    "fecha_nacimiento": entry_data["fecha_nacimiento"],
                    "aliases": entry_data["aliases"],
                    "categorias": entry_data["categorias"],
                    "descripcion": entry_data["descripcion"],
                    "fecha_sancion": entry_data["fecha_sancion"],
                    "activo": entry_data["activo"],
                    "metadata_json": entry_data["metadata_json"],
                },
            )
            entry_id = result.scalar()
            inserted += 1

    return {"inserted": inserted, "updated": updated}


def run_once() -> dict:
    """Run a one-time ingestion of screening datasets. Returns summary."""
    database_url = get_database_url()
    engine = create_engine(database_url)
    ensure_database_connection(engine)
    _ensure_screening_tables(engine)

    with engine.begin() as conn:
        lists_result = _upsert_lists(conn)
        entries_result = _upsert_entries(conn)

    # Count totals
    with engine.connect() as conn:
        list_count = conn.execute(text("SELECT COUNT(*) FROM screening_lists")).scalar()
        entry_count = conn.execute(text("SELECT COUNT(*) FROM screening_entries")).scalar()

    print(f"[screening] Lists: {list_count} total ({lists_result['inserted']} inserted, {lists_result['updated']} updated)")
    print(f"[screening] Entries: {entry_count} total ({entries_result['inserted']} inserted, {entries_result['updated']} updated)")

    return {
        "lists_inserted": lists_result["inserted"],
        "lists_updated": lists_result["updated"],
        "entries_inserted": entries_result["inserted"],
        "entries_updated": entries_result["updated"],
        "lists_total": list_count,
        "entries_total": entry_count,
    }


def main() -> None:
    """CLI entry point for screening dataset ingestion."""
    parser = argparse.ArgumentParser(description="Screening dataset ingestion worker")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=86400, help="Sync interval in seconds (default: 86400)")
    args = parser.parse_args()

    if args.run_once:
        run_once()
        return

    from runtime import handle_worker_failure
    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")
    engine = create_engine(db_url)
    ensure_database_connection(engine)

    print(f"[screening] Running every {args.interval} seconds...")
    while True:
        try:
            run_once()
        except Exception as exc:
            print(f"[screening] Error: {exc}", exc_info=True)
            if not handle_worker_failure(engine, "screening", "loop", "main", exc):
                raise
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
