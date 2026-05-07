"""Worker para lookup y sincronización de LEI via GLEIF API.

Ingesta identificadores de entidad (LEI, nombre legal, pais, estado, vigencia)
desde GLEIF API publica y los persiste en entity_identifiers + entity_aliases.

Uso:
    python -m apps.workers.entity_identity --run-once
    python -m apps.workers.entity_identity --interval 3600
"""

import argparse
import hashlib
import os
import re
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import create_engine, text

from runtime import get_database_url, get_interval_seconds


GLEIF_API_BASE = "https://api.gleif.io/api/v1"
GLEIF_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "esdata/1.0 (https://esdata.dev)",
}
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 86400)
DATABASE_URL = get_database_url()


def _normalize_name(name: str) -> str:
    """Normaliza nombre para matching: minusculas, sin acentos, espacios multiples."""
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"[ááàâä]", "a", name)
    name = re.sub(r"[éèêë]", "e", name)
    name = re.sub(r"[íìîï]", "i", name)
    name = re.sub(r"[óòôö]", "o", name)
    name = re.sub(r"[úùûü]", "u", name)
    name = re.sub(r"[ñ]", "n", name)
    name = re.sub(r"[¡¿!@#$%^&*()\-_=+\[\]{}|;:,.<>?/\\~`]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _ensure_entity_tables(engine) -> None:
    """Asegura que las tablas existen (idempotente, para workers sin alembic)."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS entity_identifiers (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresa(id),
                lei TEXT,
                nombre_legal TEXT,
                pais CHAR(2),
                estado TEXT NOT NULL DEFAULT 'active',
                vigencia_desde DATE,
                vigencia_hasta DATE,
                vlei_status TEXT,
                vlei_cred_url TEXT,
                fuente_ref TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE (empresa_id, lei)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS entity_aliases (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresa(id),
                alias TEXT NOT NULL,
                alias_normalizado TEXT NOT NULL,
                fuente TEXT NOT NULL,
                confianza NUMERIC(3,2) NOT NULL DEFAULT 0.0,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))


def _get_empresas_sin_lei(engine) -> list[dict]:
    """Devuelve empresas que no tienen LEI registrado."""
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, nombre, nif
            FROM empresa e
            WHERE NOT EXISTS (
                SELECT 1 FROM entity_identifiers ei WHERE ei.empresa_id = e.id
            )
            LIMIT 100
        """)).mappings().fetchall()
        return [dict(r) for r in rows]


def _lookup_lei_by_name(engine, empresa_nombre: str) -> dict | None:
    """Busca LEI en GLEIF API por nombre de empresa."""
    try:
        with httpx.Client(headers=GLEIF_HEADERS, timeout=15.0) as client:
            response = client.get(
                f"{GLEIF_API_BASE}/leis",
                params={
                    "filter[name]": empresa_nombre,
                    "limit": 5,
                },
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("leis", [])

            if not results:
                return None

            # Buscar coincidencia exacta o aproximada por nombre legal
            normalized_target = _normalize_name(empresa_nombre)
            best_match = None
            best_score = 0.0

            for lei_record in results:
                legal_name = lei_record.get("legalName", "")
                normalized_legal = _normalize_name(legal_name)

                if normalized_legal == normalized_target:
                    return lei_record
                elif normalized_target in normalized_legal or normalized_legal in normalized_target:
                    score = _jaccard_similarity(normalized_target, normalized_legal)
                    if score > best_score:
                        best_score = score
                        best_match = lei_record

            if best_match and best_score >= 0.4:
                return best_match

            return None
    except httpx.HTTPError:
        return None


def _lookup_lei_by_lei(lei: str) -> dict | None:
    """Busca LEI especifico en GLEIF API."""
    lei_clean = lei.upper().strip().replace(" ", "")
    try:
        with httpx.Client(headers=GLEIF_HEADERS, timeout=10.0) as client:
            response = client.get(
                f"{GLEIF_API_BASE}/leis",
                params={"filter[leiCode]": lei_clean},
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("leis", [])
            return results[0] if results else None
    except httpx.HTTPError:
        return None


def _jaccard_similarity(a: str, b: str) -> float:
    """Calcula similitud Jaccard entre dos strings."""
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _parse_gleif_record(record: dict) -> dict:
    """Convierte registro GLEIF al formato entity_identifiers."""
    return {
        "lei": record.get("lei", "").upper().strip(),
        "nombre_legal": record.get("legalName"),
        "pais": record.get("legalAddress", {}).get("country", "").upper() if record.get("legalAddress") else None,
        "estado": record.get("entityStatus", "active"),
        "vigencia_desde": record.get("issueDate"),
        "vigencia_hasta": record.get("expirationDate"),
        "fuente_ref": f"GLEIF:{record.get('lei', '')}",
    }


def _upsert_entity_identifier(engine: any, empresa_id: int, data: dict) -> int:
    """Inserta o actualiza entity_identifier para una empresa."""
    with engine.begin() as conn:
        # Verificar si ya existe
        existing = conn.execute(text("""
            SELECT id FROM entity_identifiers
            WHERE empresa_id = :empresa_id AND lei = :lei
        """), {"empresa_id": empresa_id, "lei": data["lei"]}).mappings().first()

        if existing:
            conn.execute(text("""
                UPDATE entity_identifiers
                SET nombre_legal = :nombre_legal,
                    pais = :pais,
                    estado = :estado,
                    vigencia_desde = :vigencia_desde,
                    vigencia_hasta = :vigencia_hasta,
                    fuente_ref = :fuente_ref,
                    created_at = now()
                WHERE id = :id
            """), {
                "id": existing["id"],
                "nombre_legal": data["nombre_legal"],
                "pais": data["pais"],
                "estado": data["estado"],
                "vigencia_desde": data["vigencia_desde"],
                "vigencia_hasta": data["vigencia_hasta"],
                "fuente_ref": data["fuente_ref"],
            })
            return existing["id"]
        else:
            result = conn.execute(text("""
                INSERT INTO entity_identifiers
                    (empresa_id, lei, nombre_legal, pais, estado, vigencia_desde, vigencia_hasta, fuente_ref, created_at)
                VALUES
                    (:empresa_id, :lei, :nombre_legal, :pais, :estado, :vigencia_desde, :vigencia_hasta, :fuente_ref, now())
                RETURNING id
            """), {
                "empresa_id": empresa_id,
                "lei": data["lei"],
                "nombre_legal": data["nombre_legal"],
                "pais": data["pais"],
                "estado": data["estado"],
                "vigencia_desde": data["vigencia_desde"],
                "vigencia_hasta": data["vigencia_hasta"],
                "fuente_ref": data["fuente_ref"],
            })
            return result.scalar()


def _upsert_aliases(engine: any, empresa_id: int, aliases: list[dict]) -> int:
    """Inserta aliases normalizados para una empresa."""
    count = 0
    with engine.begin() as conn:
        for alias_data in aliases:
            normalized = _normalize_name(alias_data["alias"])
            if not normalized:
                continue

            conn.execute(text("""
                INSERT INTO entity_aliases (empresa_id, alias, alias_normalizado, fuente, confianza, created_at)
                VALUES (:empresa_id, :alias, :alias_normalizado, :fuente, :confianza, now())
                ON CONFLICT DO NOTHING
            """), {
                "empresa_id": empresa_id,
                "alias": alias_data["alias"],
                "alias_normalizado": normalized,
                "fuente": alias_data.get("fuente", "GLEIF"),
                "confianza": alias_data.get("confianza", 0.8),
            })
            count += 1
    return count


def _extract_aliases_from_gleif(record: dict) -> list[dict]:
    """Extrae aliases del registro GLEIF."""
    aliases = []

    legal_name = record.get("legalName")
    if legal_name:
        aliases.append({"alias": legal_name, "fuente": "GLEIF", "confianza": 1.0})

    # Extraer nombre corto si existe
    short_name = record.get("shortName") or record.get("businessName")
    if short_name:
        aliases.append({"alias": short_name, "fuente": "GLEIF", "confianza": 0.7})

    # Extraer aliases del registro
    for alias in record.get("aliases", []):
        alias_name = alias.get("name", "") if isinstance(alias, dict) else str(alias)
        if alias_name:
            aliases.append({
                "alias": alias_name,
                "fuente": "GLEIF",
                "confianza": alias.get("confidence", 0.5) if isinstance(alias, dict) else 0.5,
            })

    return aliases


def run_once() -> dict:
    """Ejecuta una pasada de sincronización LEI."""
    engine = create_engine(DATABASE_URL)
    _ensure_entity_tables(engine)

    empresas = _get_empresas_sin_lei(engine)
    if not empresas:
        return {"status": "ok", "empresas_procesadas": 0, "leis_encontrados": 0, "aliases_creados": 0}

    leis_encontrados = 0
    aliases_creados = 0

    for empresa in empresas:
        lei_record = _lookup_lei_by_name(engine, empresa["nombre"])
        if lei_record:
            parsed = _parse_gleif_record(lei_record)
            entity_id = _upsert_entity_identifier(engine, empresa["id"], parsed)
            aliases = _extract_aliases_from_gleif(lei_record)
            if aliases:
                aliases_creados += _upsert_aliases(engine, empresa["id"], aliases)
            leis_encontrados += 1

    return {
        "status": "ok",
        "empresas_procesadas": len(empresas),
        "leis_encontrados": leis_encontrados,
        "aliases_creados": aliases_creados,
    }


def main():
    parser = argparse.ArgumentParser(description="Worker de sincronización LEI via GLEIF API")
    parser.add_argument("--run-once", action="store_true", help="Ejecutar una vez y salir")
    parser.add_argument("--interval", type=int, default=None, help="Intervalo en segundos")
    args = parser.parse_args()

    interval = args.interval or SYNC_INTERVAL_SECONDS

    from runtime import handle_worker_failure
    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")
    engine = create_engine(db_url)

    while True:
        try:
            result = run_once()
            print(f"[entity_identity] {result}")
        except Exception as exc:
            print(f"[entity_identity] Error: {type(exc).__name__}: {exc}", exc_info=True)
            if not handle_worker_failure(engine, "entity_identity", "loop", "main", exc):
                raise

        if args.run_once:
            break

        time.sleep(interval)


if __name__ == "__main__":
    main()
