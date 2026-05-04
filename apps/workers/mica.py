"""Worker para MiCA (Reglamento UE 2023/1114) y crypto-asset services.

Ingesta el registro de CASP (Crypto-Asset Service Providers) de ESMA,
parsea y almacena los proveedores de servicios de criptoactivos
en la tabla casp.

Uso:
    python -m workers.mica --run-once
    python -m workers.mica --interval 3600
"""

import argparse
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime import configure_logging, ensure_database_connection, get_database_url, get_interval_seconds

logger = configure_logging("workers.mica")

ESMA_CASP_API = "https://www.esma.europa.eu/sites/default/files/library/2023/12/registries/crypto-assets_registries_data.json"
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("MICA_SYNC_INTERVAL_SECONDS", 604800)


def fetch_esma_casp() -> list[dict]:
    """Obtener CASP del registro ESMA."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(ESMA_CASP_API)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error("Error fetching ESMA CASP registry: %s", e)
        return []

    # ESMA returns a dict with key 'casp' containing list of CASP entries
    casps = data.get("casp", [])
    logger.info("ESMA returned %d CASP entries", len(casps))
    return casps


def normalize_casp(raw: dict) -> dict:
    """Normalizar un CASP crudo de ESMA al esquema de la tabla."""
    services = []
    for svc in ["custody", "exchange", "execution", "payment"]:
        key = svc.lower()
        val = raw.get(key, raw.get(key.replace("_", ""), raw.get(f"is_{key}")))
        if val in (True, "true", "yes", 1, "Y"):
            services.append(svc)

    passport_active = False
    pp = raw.get("passport_active", raw.get("passport", raw.get("has_passport")))
    if pp in (True, "true", "yes", 1, "Y"):
        passport_active = True

    return {
        "name": raw.get("name", raw.get("provider_name", "")),
        "registration_number": raw.get("registration_number", raw.get("reg_number", raw.get("id"))),
        "home_member_state": raw.get("home_member_state", raw.get("country", raw.get("jurisdiction"))),
        "passport_active": passport_active,
        "services_offered": services,
        "status": "active",
    }


def upsert_casp(db, casp: dict) -> None:
    """Insertar o actualizar un CASP en la BD."""
    services_json = json.dumps(casp["services_offered"])
    casp_columns = {column["name"] for column in inspect(db).get_columns("casp")}
    existing = db.execute(
        text(
            "SELECT id FROM casp WHERE registration_number = :reg AND home_member_state = :state"
        ),
        {
            "reg": casp["registration_number"],
            "state": casp["home_member_state"],
        },
    ).mappings().first()

    if existing:
        update_parts = [
            "name = :name",
            "passport_active = :passport_active",
            "services_offered = :services_offered",
            "status = :status",
        ]
        if "updated_at" in casp_columns:
            update_parts.append("updated_at = CURRENT_TIMESTAMP")
        db.execute(
            text(
                f"UPDATE casp SET {', '.join(update_parts)} WHERE id = :id"
            ),
            {
                "id": existing["id"],
                "name": casp["name"],
                "passport_active": casp["passport_active"],
                "services_offered": services_json,
                "status": casp["status"],
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO casp (name, registration_number, home_member_state,
                                  passport_active, services_offered, status)
                VALUES (:name, :registration_number, :home_member_state,
                        :passport_active, :services_offered, :status)
                """
            ),
            {**casp, "services_offered": services_json},
        )


def run_once() -> None:
    """Ejecutar una ingestion completa desde ESMA."""
    logger.info("Starting MiCA CASP sync from ESMA")
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine, logger=logger)

    casps_raw = fetch_esma_casp()
    if not casps_raw:
        logger.warning("No CASP data received from ESMA, skipping")
        return

    synced = 0
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for raw in casps_raw:
                normalized = normalize_casp(raw)
                if not normalized["name"]:
                    logger.warning("Skipping CASP entry with empty name: %s", raw)
                    continue
                upsert_casp(conn, normalized)
                synced += 1
            trans.commit()
        except Exception:
            trans.rollback()
            raise

    logger.info("MiCA CASP sync complete: %d CASPs synced", synced)


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker MiCA CASP sync from ESMA")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=None, help="Sync interval in seconds")
    args = parser.parse_args()

    interval = args.interval or SYNC_INTERVAL_SECONDS

    if args.run_once:
        run_once()
        return

    logger.info("MiCA CASP worker starting, interval=%ds", interval)
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Error in MiCA CASP sync cycle")
        logger.info("Next sync in %ds", interval)
        import time
        time.sleep(interval)


if __name__ == "__main__":
    main()
