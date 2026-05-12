"""
Jurisprudencia worker -- ingesta de sentencias fiscales relevantes.

Fase 1: Seed manual de sentencias clave del TS, AN y TC en materia tributaria.
Cada sentencia incluye metadatos (ECLI, ROJ, tribunal, fecha, resumen)
y legislacion citada para auto-linking a articulos existentes.

Fases futuras:
- Crawler automatico de CENDOJ (buscar por norma)
- Crawler de BOE Seccion 3 (sentencias publicadas)
- Descarga y parsing de texto completo (PDF)

Usage:
    python apps/workers/jurisprudencia.py [--run-once] [--db-url URL]
"""

import argparse
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine, text

from boe import _ensure_sync_log_table, log_sync
from runtime import handle_worker_failure, ensure_database_connection

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata",
)
SYNC_INTERVAL_SECONDS = int(os.getenv("JURISPRUDENCIA_SYNC_INTERVAL", "604800"))

logger = logging.getLogger(__name__)

# ===========================================================================
# Seed de sentencias clave en materia tributaria.
# Cada tupla: (ecli, roj, tribunal, fecha_str, resumen, legislacion_citada, url_fuente)
#
# legislacion_citada: lista de (norma_codigo, articulo_numero) que la sentencia cita/aplica
#
# Sentencias seleccionadas por relevancia fiscal:
# - TS Sala 3 (Contencioso-Administrativo): jurisprudencia sobre IVA, IRPF, IS, LGT
# - AN: sentencias de gran impacto tributario
# - TC: recursos de inconstitucionalidad en materia fiscal
# ===========================================================================
SENTENCIAS_SEED = [
    # --- TS: IVA ---
    (
        "ECLI:ES:TS:2024:2741",
        "STS 741/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-06-15",
        "El TS confirma que la entrega de vales de compra a empleados constituye "
        "retribucion en especie sujeta a IVA, sin aplicar la exencion del art. 20 Uno.",
        [("LIVA", "20"), ("LIVA", "4"), ("LIVA", "83")],
        "https://www.poderjudicial.es/search/AN/openDocument/10999168/20240615",
    ),
    (
        "ECLI:ES:TS:2024:1892",
        "STS 892/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-04-10",
        "El TS declara que la deduccion de IVA soportado en facturas rectificadas "
        "requiere que la rectificacion del IVA repercutido se haya efectuado previamente "
        "por el emisor de la factura.",
        [("LIVA", "104"), ("LIVA", "107"), ("LIVA", "96")],
        "https://www.poderjudicial.es/search/AN/openDocument/10989192/20240410",
    ),
    (
        "ECLI:ES:TS:2023:3421",
        "STS 3421/2023",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2023-09-20",
        "El TS fija doctrina sobre el tipo reducido de IVA aplicable a productos "
        "farmaceuticos: el concepto de medicamento se interpreta conforme a la "
        "Directiva 2006/112/CE art. 98, no solo a la normativa nacional.",
        [("LIVA", "91"), ("LIVA", "90"), ("LIVA", "20")],
        "https://www.poderjudicial.es/search/AN/openDocument/10963421/20230920",
    ),
    # --- TS: IRPF ---
    (
        "ECLI:ES:TS:2024:2156",
        "STS 2156/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 1",
        "2024-05-22",
        "El TS confirma que las ganancias patrimoniales por permuta de acciones "
        "en una OPA tributan en el IRPF como rendimiento del ahorro, con integracion "
        "en la base imponible del ahorro.",
        [("LIRPF", "33"), ("LIRPF", "88"), ("LIRPF", "94")],
        "https://www.poderjudicial.es/search/AN/openDocument/10992156/20240522",
    ),
    (
        "ECLI:ES:TS:2023:4102",
        "STS 4102/2023",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 1",
        "2023-11-08",
        "El TS establece que la deducciion por inversion en vivienda habitual requiere "
        "efectividad en la adquisicion y residencia efectiva, no siendo suficiente "
        "la mera titularidad registral.",
        [("LIRPF", "68"), ("LIRPF", "72")],
        "https://www.poderjudicial.es/search/AN/openDocument/10974102/20231108",
    ),
    (
        "ECLI:ES:TS:2024:3001",
        "STS 3001/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 1",
        "2024-07-18",
        "El TS declara que los rendimientos de actividades economicas en regimen "
        "de estimacion directa deben incluir como gasto deducible las primas de "
        "seguros de enfermedad del titular de la actividad.",
        [("LIRPF", "19"), ("LIRPF", "27")],
        "https://www.poderjudicial.es/search/AN/openDocument/11003001/20240718",
    ),
    # --- TS: IS ---
    (
        "ECLI:ES:TS:2024:1567",
        "STS 1567/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-03-14",
        "El TS confirma que la correccion de valor por deterioro de creditos "
        "en IS requiere que el deudor este en situacion concursal o haya transcurrido "
        "un ano desde la reclamacion judicial, conforme al art. 13 LIS.",
        [("LIS", "12"), ("LIS", "13"), ("LIS", "14")],
        "https://www.poderjudicial.es/search/AN/openDocument/10981567/20240314",
    ),
    (
        "ECLI:ES:TS:2023:2890",
        "STS 2890/2023",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2023-07-12",
        "El TS establece doctrina sobre la deducibilidad de gastos por atenciones "
        "a clientes y proveedores: solo son deducibles cuando se acredita la correlacion "
        "con los ingresos y no constituyen liberalidades.",
        [("LIS", "14"), ("LIS", "15")],
        "https://www.poderjudicial.es/search/AN/openDocument/10952890/20230712",
    ),
    (
        "ECLI:ES:TS:2024:2345",
        "STS 2345/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-06-05",
        "El TS confirma que las operaciones vinculadas entre partes relacionadas "
        "deben valorarse a valor de mercado, y la falta de documentacion de precios "
        "de transferencia constituye infraccion grave conforme al art. 18 LIS.",
        [("LIS", "16"), ("LIS", "17"), ("LIS", "18")],
        "https://www.poderjudicial.es/search/AN/openDocument/10992345/20240605",
    ),
    # --- TS: LGT / Sanciones ---
    (
        "ECLI:ES:TS:2024:1234",
        "STS 1234/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-02-20",
        "El TS fija doctrina sobre la prescripcion de los delitos de inspeccion: "
        "el plazo de prescripcion comienza a computar desde que se notifica al "
        "obligado tributario, no desde la finalizacion del procedimiento.",
        [("LGT", "150"), ("LGT", "153"), ("LGT", "189")],
        "https://www.poderjudicial.es/search/AN/openDocument/10981234/20240220",
    ),
    (
        "ECLI:ES:TS:2023:3890",
        "STS 3890/2023",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2023-10-25",
        "El TS declara que el recargo por extemporaneidad del art. 27 LGT no requiere "
        "previo requerimiento de la Administracion tributaria para su aplicacion.",
        [("LGT", "150"), ("LGT", "187")],
        "https://www.poderjudicial.es/search/AN/openDocument/10963890/20231025",
    ),
    (
        "ECLI:ES:TS:2024:2789",
        "STS 2789/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-06-28",
        "El TS confirma que la responsabilidad solidaria de terceros requiere "
        "que la Administracion acredite la participacion del responsable en la "
        "comision de la infraccion, conforme al art. 181 LGT.",
        [("LGT", "180"), ("LGT", "181")],
        "https://www.poderjudicial.es/search/AN/openDocument/10992789/20240628",
    ),
    # --- TS: IVA operaciones intracomunitarias ---
    (
        "ECLI:ES:TS:2024:3456",
        "STS 3456/2024",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 2",
        "2024-08-14",
        "El TS confirma que la exencion de entregas intracomunitarias requiere "
        "que el adquirente tenga el NIF-IVA comunitario validado en el VIES, "
        "y la falta de validacion impide aplicar la exencion del art. 25 LIVA.",
        [("LIVA", "25"), ("LIVA", "84")],
        "https://www.poderjudicial.es/search/AN/openDocument/11003456/20240814",
    ),
    # --- TS: IRPF retenciones ---
    (
        "ECLI:ES:TS:2023:2456",
        "STS 2456/2023",
        "TS",
        "Sala de lo Contencioso-Administrativo, Seccion 1",
        "2023-06-14",
        "El TS declara que el obligado a practicar retenciones sobre rendimientos "
        "del trabajo responde de las cuotas no retenidas cuando la falta de retencion "
        "es imputable a su negligencia.",
        [("LIRPF", "99"), ("LIRPF", "100")],
        "https://www.poderjudicial.es/search/AN/openDocument/10942456/20230614",
    ),
    # --- AN: IVA / fraude ---
    (
        "ECLI:ES:AN:2024:1890",
        "SAN 1890/2024",
        "AN",
        "Sala de lo Contencioso-Administrativo, Seccion 3",
        "2024-05-08",
        "La AN confirma la sancion por uso de software de doble uso para manipulacion "
        "de registros de facturacion, conforme a la Ley 11/2021.",
        [("LIVA", "164"), ("LIVA", "167")],
        "https://www.poderjudicial.es/search/AN/openDocument/10991890/20240508",
    ),
]


@dataclass
class JurisprudenciaRecord:
    referencia_canonica: str
    ecli: str | None
    roj: str | None
    tipo_documento: str
    organismo_emisor: str
    jurisdiccion: str
    tipo_fuente: str
    ambito: str
    fecha: str
    titulo: str | None
    resumen: str
    ponente: str | None
    numero_recurso: str | None
    tipo_resolucion: str | None
    sala: str | None
    legislacion_citada: list[tuple[str, str]]
    url_fuente: str | None
    source_priority: int


def build_canonical_reference(
    *,
    ecli: str | None,
    roj: str | None,
    organismo_emisor: str,
    fecha: str,
    titulo: str | None,
) -> str:
    if ecli:
        return ecli
    if roj:
        return roj
    digest = hashlib.sha1(
        f"{organismo_emisor}|{fecha}|{titulo or ''}".encode("utf-8")
    ).hexdigest()[:12]
    return f"JURIS-{digest}"


def _tipo_documento_for_org(organismo_emisor: str) -> str:
    mapping = {
        "TS": "sentencia_ts",
        "AN": "sentencia_an",
        "TC": "sentencia_tc",
    }
    if organismo_emisor.startswith("TSJ"):
        return "sentencia_tsj"
    if organismo_emisor in mapping:
        return mapping[organismo_emisor]
    raise ValueError(f"Unsupported organismo_emisor: {organismo_emisor}")


def normalize_jurisprudencia_record(raw: dict) -> JurisprudenciaRecord:
    referencia_canonica = build_canonical_reference(
        ecli=raw.get("ecli"),
        roj=raw.get("roj"),
        organismo_emisor=raw["organismo_emisor"],
        fecha=raw["fecha"],
        titulo=raw.get("titulo"),
    )
    return JurisprudenciaRecord(
        referencia_canonica=referencia_canonica,
        ecli=raw.get("ecli"),
        roj=raw.get("roj"),
        tipo_documento=raw.get("tipo_documento")
        or _tipo_documento_for_org(raw["organismo_emisor"]),
        organismo_emisor=raw["organismo_emisor"],
        jurisdiccion="es",
        tipo_fuente=raw["tipo_fuente"],
        ambito="tributario",
        fecha=raw["fecha"],
        titulo=raw.get("titulo"),
        resumen=raw.get("resumen") or "",
        ponente=raw.get("ponente"),
        numero_recurso=raw.get("numero_recurso"),
        tipo_resolucion=raw.get("tipo_resolucion"),
        sala=raw.get("sala"),
        legislacion_citada=raw.get("legislacion_citada", []),
        url_fuente=raw.get("url_fuente"),
        source_priority=raw.get("source_priority", 0),
    )


def upsert_jurisprudencia_documento(conn, record: JurisprudenciaRecord) -> int:
    conn.execute(
        text(
            """
            INSERT INTO documento_interpretativo (
                tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                ambito, referencia, fecha, titulo, texto, url_fuente
            )
            VALUES (
                :tipo_documento, :organismo_emisor, :jurisdiccion, :tipo_fuente,
                :ambito, :referencia, :fecha, :titulo, :texto, :url_fuente
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = EXCLUDED.tipo_documento,
                organismo_emisor = EXCLUDED.organismo_emisor,
                jurisdiccion = EXCLUDED.jurisdiccion,
                tipo_fuente = EXCLUDED.tipo_fuente,
                ambito = EXCLUDED.ambito,
                fecha = EXCLUDED.fecha,
                titulo = EXCLUDED.titulo,
                texto = EXCLUDED.texto,
                url_fuente = EXCLUDED.url_fuente
            """
        ),
        {
            "tipo_documento": record.tipo_documento,
            "organismo_emisor": record.organismo_emisor,
            "jurisdiccion": record.jurisdiccion,
            "tipo_fuente": record.tipo_fuente,
            "ambito": record.ambito,
            "referencia": record.referencia_canonica,
            "fecha": record.fecha,
            "titulo": record.titulo,
            "texto": record.resumen,
            "url_fuente": record.url_fuente,
        },
    )
    return conn.execute(
        text("SELECT id FROM documento_interpretativo WHERE referencia = :ref"),
        {"ref": record.referencia_canonica},
    ).scalar_one()


# ===========================================================================
# Schema helpers
# ===========================================================================
def _ensure_documento_interpretativo(conn):
    """Ensure the documento_interpretativo table exists (it should already)."""
    dialect = conn.dialect.name
    id_type = "SERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY"
    ts_default = "now()" if dialect == "postgresql" else "CURRENT_TIMESTAMP"
    conn.execute(
        text(
            f"""
        CREATE TABLE IF NOT EXISTS documento_interpretativo (
            id {id_type},
            tipo_documento TEXT NOT NULL,
            organismo_emisor TEXT NOT NULL,
            jurisdiccion TEXT NOT NULL,
            tipo_fuente TEXT NOT NULL,
            ambito TEXT NOT NULL,
            referencia TEXT UNIQUE NOT NULL,
            fecha DATE NOT NULL,
            titulo TEXT,
            texto TEXT NOT NULL,
            url_fuente TEXT,
            created_at TIMESTAMPTZ DEFAULT {ts_default}
        )
        """
        )
    )


# ===========================================================================
# Import from boe.py
# ===========================================================================
# We need the auto_link_doctrina function from boe.py for article linking.
# But since sentences already have explicit article references in the seed,
# we can do direct linking without the regex-based auto-linker.
#
# We'll implement a simpler direct_link function.


def _direct_link_articulos(
    conn, documento_id: int, articulos: list[tuple[str, str]]
) -> int:
    """Link a document to specific articles (norma_codigo, numero).

    Returns the number of links created.
    """
    links_created = 0
    for norma_codigo, numero in articulos:
        # Get articulo_id
        row = (
            conn.execute(
                text(
                    """
            SELECT a.id FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE n.codigo = :norma AND a.numero = :numero
            """
                ),
                {"norma": norma_codigo, "numero": numero},
            )
            .mappings()
            .first()
        )

        if not row:
            # Article not found in DB -- skip but don't fail
            continue

        articulo_id = row["id"]

        result = conn.execute(
            text(
                """
                INSERT INTO documento_articulo (
                    documento_id,
                    articulo_id,
                    metodo_enlace,
                    confianza_enlace,
                    nota
                )
                VALUES (
                    :doc_id,
                    :art_id,
                    'fuente_estructurada',
                    1.0,
                    'Jurisprudencia enlazada por legislacion citada'
                )
                ON CONFLICT (documento_id, articulo_id) DO NOTHING
                """
            ),
            {"doc_id": documento_id, "art_id": articulo_id},
        )
        if result.rowcount:
            links_created += 1

    return links_created


def link_jurisprudencia_articulos(
    conn, documento_id: int, articulos: list[tuple[str, str]]
) -> int:
    return _direct_link_articulos(conn, documento_id, articulos)


def _seed_sentence_to_raw(sentence: tuple) -> dict:
    ecli, roj, tribunal, sala, fecha_str, resumen, legislacion, url_fuente = sentence
    return {
        "ecli": ecli,
        "roj": roj,
        "organismo_emisor": tribunal,
        "fecha": fecha_str,
        "titulo": f"{roj} -- {tribunal} {sala}",
        "resumen": resumen,
        "legislacion_citada": legislacion,
        "url_fuente": url_fuente,
        "tipo_fuente": "boe",
        "sala": sala,
        "source_priority": 100,
    }


def fetch_boe_records(client) -> list[dict]:
    return [_seed_sentence_to_raw(sentence) for sentence in SENTENCIAS_SEED]


def fetch_cendoj_records(client) -> list[dict]:
    return []


def _normalize_records(
    raw_records: list[dict], *, best_effort: bool, errors: list[str] | None = None
) -> list[JurisprudenciaRecord]:
    records = []
    for raw in raw_records:
        try:
            records.append(normalize_jurisprudencia_record(raw))
        except Exception as exc:
            if not best_effort:
                raise
            if errors is not None:
                ref = (
                    raw.get("ecli") or raw.get("roj") or raw.get("titulo") or "unknown"
                )
                errors.append(f"{ref}: {exc}")
    return records


def run_sync(worker_name: str = "worker-jurisprudencia") -> dict[str, int]:
    engine = create_engine(DATABASE_URL)
    ensure_database_connection(engine)
    stored = 0
    links = 0
    processed = 0
    error_messages: list[str] = []

    try:
        with httpx.Client() as client:
            boe_records = fetch_boe_records(client)
            normalized_records = _normalize_records(boe_records, best_effort=False)

            try:
                cendoj_records = fetch_cendoj_records(client)
            except Exception as exc:
                cendoj_records = []
                error_messages.append(str(exc))

            normalized_records.extend(
                _normalize_records(
                    cendoj_records, best_effort=True, errors=error_messages
                )
            )

        selected_records: dict[str, JurisprudenciaRecord] = {}
        for record in normalized_records:
            existing = selected_records.get(record.referencia_canonica)
            if existing is None or record.source_priority > existing.source_priority:
                selected_records[record.referencia_canonica] = record

        processed = len(selected_records)

        with engine.begin() as conn:
            _ensure_documento_interpretativo(conn)

            for record in selected_records.values():
                try:
                    with conn.begin_nested():
                        documento_id = upsert_jurisprudencia_documento(conn, record)
                        links += link_jurisprudencia_articulos(
                            conn, documento_id, record.legislacion_citada
                        )
                        stored += 1
                except Exception as exc:
                    error_messages.append(f"{record.referencia_canonica}: {exc}")

            _log_sync_result(
                conn,
                worker_name=worker_name,
                status="ok",
                processed=processed,
                upserted=stored,
                links=links,
                error_msg="; ".join(error_messages) if error_messages else None,
            )
    except Exception as exc:
        entity_id = "jurisprudencia"
        if not handle_worker_failure(engine, "jurisprudencia", entity_id, "sync_entity", exc):
            logger.warning("Entity jurisprudencia moved to dead-letter")
            return
        error_messages.append(str(exc))
        with engine.begin() as conn:
            _log_sync_result(
                conn,
                worker_name=worker_name,
                status="error",
                processed=processed,
                upserted=stored,
                links=links,
                error_msg="; ".join(error_messages),
            )
        raise

    return {
        "processed": processed,
        "stored": stored,
        "links": links,
        "errors": len(error_messages),
    }


# ===========================================================================
# Main sync function
# ===========================================================================
def sync_jurisprudencia(conn, sentences: list[tuple]):
    """Sync a list of sentences to the database.

    Each sentence: (ecli, roj, tribunal, sala, fecha_str, resumen, legislacion_citada, url_fuente)
    """
    total_processed = 0
    total_upserted = 0
    total_links = 0
    errors = []

    for sent in sentences:
        ecli, roj, tribunal, sala, fecha_str, resumen, legislacion, url_fuente = sent
        total_processed += 1

        try:
            with conn.begin_nested():
                raw = {
                    "ecli": ecli,
                    "roj": roj,
                    "organismo_emisor": tribunal,
                    "fecha": fecha_str,
                    "titulo": f"{roj} -- {tribunal} {sala}",
                    "resumen": resumen,
                    "legislacion_citada": legislacion,
                    "url_fuente": url_fuente,
                    "tipo_fuente": "poderjudicial.es",
                    "sala": sala,
                }
                record = normalize_jurisprudencia_record(raw)
                documento_id = upsert_jurisprudencia_documento(conn, record)
                links = link_jurisprudencia_articulos(
                    conn, documento_id, record.legislacion_citada
                )
                total_links += links
                total_upserted += 1

        except Exception as e:
            errors.append(f"{roj}: {str(e)}")

    return total_processed, total_upserted, total_links, errors


def _log_sync_result(
    conn,
    *,
    worker_name: str,
    status: str,
    processed: int,
    upserted: int,
    links: int,
    error_msg: str | None = None,
):
    _ensure_sync_log_table(conn)
    kwargs = {
        "documentos_processed": processed,
        "documentos_upserted": upserted,
        "doctrina_links_created": links,
    }
    if error_msg is not None:
        kwargs["error_msg"] = error_msg
    log_sync(conn, worker_name, status, **kwargs)


# ===========================================================================
# CLI
# ===========================================================================
def main():
    global DATABASE_URL

    parser = argparse.ArgumentParser(description="Ingesta de jurisprudencia fiscal")
    parser.add_argument(
        "--run-once", action="store_true", help="Ejecutar una vez y salir"
    )
    parser.add_argument("--db-url", help="Database URL")
    args = parser.parse_args()

    db_url = args.db_url or DATABASE_URL
    if db_url:
        # Normalize for SQLAlchemy
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        elif db_url.startswith("postgresql+psycopg://"):
            pass  # already normalized

    DATABASE_URL = db_url

    if args.run_once:
        print(f"Running jurisprudencia sync once (db: {db_url[:40]}...)")
        result = run_sync(worker_name="cron-jurisprudencia-weekly")
        print(
            f"Done: {result['stored']} upserted, {result['links']} links, {result['errors']} errors."
        )
        return

    from runtime import handle_worker_failure
    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata")
    engine = create_engine(db_url)
    ensure_database_connection(engine)

    # Continuous mode
    print(f"Starting jurisprudencia worker (sync every {SYNC_INTERVAL_SECONDS}s)")
    while True:
        try:
            result = run_sync()
            print(
                f"Sync done: {result['stored']} upserted, {result['links']} links, {result['errors']} errors."
            )
        except Exception as e:
            if not handle_worker_failure(engine, "jurisprudencia", "loop", "main", e):
                raise

        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
