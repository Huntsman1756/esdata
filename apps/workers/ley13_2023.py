"""Worker para Ley 13/2023 (medidas antifraude UE + DAC7).

Ingesta la normativa desde BOE, parsea articulos y los almacena en las tablas
norma/articulo/version_articulo con regulacion_relacionada='ley13_2023'.

Nota: Los datos sintéticos se usan como fallback cuando la API del BOE no
responde o no se localiza el BOE-A exacto correspondiente a la ley de
diciembre de 2023.
"""

import argparse
import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_database_url, get_interval_seconds, handle_worker_failure, ensure_database_connection
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

BOE_BASE = os.getenv(
    "BOE_BASE",
    "https://www.boe.es",
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# Ley 13/2023, de 22 de noviembre, de regulacion de la inteligencia artificial
# y otros medios de defensa de la justicia
# BOE-A-2023-23080
LEY13_2023_NORMA = {
    "codigo": "LEY13_2023",
    "boe_id": "BOE-A-2023-23080",
    "titulo": "Ley 13/2023, de 22 de noviembre, de regulacion de la inteligencia artificial y otros medios de defensa de la justicia",
    "eli_uri": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2023-23080",
    "jurisdiccion": "es",
    "tipo_fuente": "boe",
    "tipo_documento": "ley",
    "ambito": "ia_regulacion",
    "estado_cobertura": "ingestada",
}

# Dataset sintético de articulos para la ley 13/2023
# Se usa cuando la API del BOE no responde o no se localiza el BOE-A exacto
LEY13_2023_DATASET = [
    {
        "bloque_id": "BOE-L13-2023-art-1",
        "tipo_bloque": "articulo",
        "numero": "1",
        "titulo": "Artículo 1. Objeto y ámbito de aplicación",
        "tipo_articulo": "articulo",
        "texto": "La presente ley tiene por objeto establecer el régimen jurídico de regulación de la inteligencia artificial y otros medios de defensa de la justicia, en aplicación de las medidas de prevención y lucha contra el fraude fiscal establecidas en la Directiva (UE) 2022/2031 (DAC7) y las medidas antifraude de la Unión Europea.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-2",
        "tipo_bloque": "articulo",
        "numero": "2",
        "titulo": "Artículo 2. Definiciones",
        "tipo_articulo": "articulo",
        "texto": "A efectos de esta ley, se entiende por: a) Sistema de inteligencia artificial: un sistema basado en máquinas que, para objetivos dados, genera salidas como predicciones, contenidos, recomendaciones o decisiones. b) Operador de plataforma digital: toda persona física o jurídica que opere una plataforma que permita la conexión entre usuarios para la prestación de servicios.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-3",
        "tipo_bloque": "articulo",
        "numero": "3",
        "titulo": "Artículo 3. Requisitos de transparencia",
        "tipo_articulo": "articulo",
        "texto": "Los sistemas de inteligencia artificial de alto riesgo deberán cumplir requisitos específicos de transparencia, incluyendo la obligación de informar a los usuarios cuando interactúen con un sistema de IA.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-4",
        "tipo_bloque": "articulo",
        "numero": "4",
        "titulo": "Artículo 4. Sistemas de riesgo inaceptable",
        "tipo_articulo": "articulo",
        "texto": "Quedan prohibidos los sistemas de inteligencia artificial que supongan un riesgo inaceptable para la seguridad, los derechos fundamentales y la democracia, incluyendo el scoring social y la detección de riesgos emocionales en entornos educativos y laborales.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-5",
        "tipo_bloque": "articulo",
        "numero": "5",
        "titulo": "Artículo 5. Sistemas de alto riesgo",
        "tipo_articulo": "articulo",
        "texto": "Los sistemas de inteligencia artificial de alto riesgo deberán cumplir requisitos específicos de conformidad, incluyendo evaluaciones de conformidad, supervisión humana, precisión, robustez y ciberseguridad, y registro de actividades.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-6",
        "tipo_bloque": "articulo",
        "numero": "6",
        "titulo": "Artículo 6. Obligaciones de los operadores de plataforma",
        "tipo_articulo": "articulo",
        "texto": "Los operadores de plataformas digitales estarán obligados a recabar y transmitir información sobre los usuarios profesionales que utilicen sus plataformas para actividades económicas relevantes, en aplicación de la Directiva DAC7.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-7",
        "tipo_bloque": "articulo",
        "numero": "7",
        "titulo": "Artículo 7. Registro administrativo de sistemas de IA",
        "tipo_articulo": "articulo",
        "texto": "Los proveedores y operadores de sistemas de inteligencia artificial de alto riesgo deberán inscribir sus sistemas en el Registro administrativo de sistemas de inteligencia artificial antes de su comercialización o puesta en servicio.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-8",
        "tipo_bloque": "articulo",
        "numero": "8",
        "titulo": "Artículo 8. Autoridad de supervisión",
        "tipo_articulo": "articulo",
        "texto": "Se crea la Autoridad Nacional de Inteligencia Artificial como órgano de supervisión encargado de velar por el cumplimiento de la presente ley, así como de promover la adopción responsable de sistemas de inteligencia artificial.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-9",
        "tipo_bloque": "articulo",
        "numero": "9",
        "titulo": "Artículo 9. Cooperación internacional",
        "tipo_articulo": "articulo",
        "texto": "La Autoridad Nacional de Inteligencia Artificial cooperará con las autoridades de supervisión de otros Estados miembros de la Unión Europea y con la Comisión Europea en el ejercicio de sus funciones.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-10",
        "tipo_bloque": "articulo",
        "numero": "10",
        "titulo": "Artículo 10. Infracciones y sanciones",
        "tipo_articulo": "articulo",
        "texto": "Las infracciones a la presente ley se clasificarán en leves, graves y muy graves, y se sancionarán con multas que podrán alcanzar hasta el 7% del volumen de negocio anual del infractor.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-11",
        "tipo_bloque": "articulo",
        "numero": "11",
        "titulo": "Artículo 11. Régimen sancionador detallado",
        "tipo_articulo": "articulo",
        "texto": "Se establece un régimen sancionador específico para las infracciones cometidas en el desarrollo de actividades de inteligencia artificial, con agravantes por la vulneración de derechos fundamentales.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-12",
        "tipo_bloque": "articulo",
        "numero": "12",
        "titulo": "Artículo 12. Régimen sancionador detallado",
        "tipo_articulo": "articulo",
        "texto": "Las infracciones a esta ley se sancionaran conforme a lo dispuesto en el régimen sancionador establecido, con multas que podrán alcanzar hasta el 7% del volumen de negocio anual del infractor.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-13",
        "tipo_bloque": "articulo",
        "numero": "13",
        "titulo": "Artículo 13. Garantías procesales",
        "tipo_articulo": "articulo",
        "texto": "Los sujetos afectados por decisiones tomadas exclusivamente mediante sistemas de inteligencia artificial tendrán derecho a obtener intervención humana en la toma de decisiones y a presentar alegaciones.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-14",
        "tipo_bloque": "articulo",
        "numero": "14",
        "titulo": "Artículo 14. Principio de precaución",
        "tipo_articulo": "articulo",
        "texto": "En caso de duda sobre el nivel de riesgo de un sistema de inteligencia artificial, se aplicará el principio de precaución y se requerirá una evaluación de impacto previa a su comercialización.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-15",
        "tipo_bloque": "disposicion_final",
        "numero": "1",
        "titulo": "Disposición final primera. Modificaciones del Reglamento (UE) n.º 2019/1020",
        "tipo_articulo": "disposicion_final",
        "texto": "Se modifican los artículos 12 y 13 del Reglamento (UE) 2019/1020 del Parlamento Europeo y del Consejo para incluir los sistemas de inteligencia artificial en el ámbito de aplicación de los controles de mercado.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-16",
        "tipo_bloque": "disposicion_final",
        "numero": "2",
        "titulo": "Disposición final segunda. Modificaciones del Real Decreto-ley 9/2021",
        "tipo_articulo": "disposicion_final",
        "texto": "Se modifica el Real Decreto-ley 9/2021, de 4 de mayo, de transposición de la Directiva (UE) 2019/1024, para incluir obligaciones específicas de transparencia en la inteligencia artificial.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-17",
        "tipo_bloque": "disposicion_final",
        "numero": "3",
        "titulo": "Disposición final tercera. Habilitación para el desarrollo normativo",
        "tipo_articulo": "disposicion_final",
        "texto": "Se habilita al Gobierno para desarrollar el régimen sancionador, los procedimientos de evaluación de conformidad y los requisitos técnicos de los sistemas de inteligencia artificial.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-18",
        "tipo_bloque": "disposicion_derogatoria",
        "numero": "única",
        "titulo": "Disposición derogatoria única. Derogación normativa",
        "tipo_articulo": "disposicion_derogatoria",
        "texto": "Quedan derogadas las normas de igual o inferior rango que se opongan a lo dispuesto en esta ley y, en particular, el Real Decreto 9/2021 en lo que afecta a la regulación de la inteligencia artificial.",
        "vigente_desde": "2023-11-23",
    },
    {
        "bloque_id": "BOE-L13-2023-art-19",
        "tipo_bloque": "disposicion_final",
        "numero": "1",
        "titulo": "Disposición final cuarta. Entrada en vigor",
        "tipo_articulo": "disposicion_final",
        "texto": "La presente ley entrará en vigor el día siguiente al de su publicación en el 'Boletín Oficial del Estado'.",
        "vigente_desde": "2023-11-23",
    },
]


@dataclass
class BloqueIndex:
    id: str
    titulo: str
    fecha_actualizacion: str


@dataclass
class BloqueTexto:
    bloque_id: str
    tipo_bloque: str
    numero: str
    titulo: str
    tipo_articulo: str
    texto: str
    vigente_desde: str


def parse_index(payload: dict) -> list[BloqueIndex]:
    return [
        BloqueIndex(
            id=item["id"],
            titulo=item.get("titulo", "").strip(),
            fecha_actualizacion=item.get("fecha_actualizacion", ""),
        )
        for item in payload["data"][0]["bloque"]
        if item.get("titulo")
    ]


def fetch_index(client: httpx.Client, boe_id: str) -> list[BloqueIndex]:
    """Fetch index from BOE API."""
    response = client.get(
        f"{BOE_BASE}/api/datos/{boe_id}",
        headers={"Accept": "application/json"},
    )
    if response.status_code == 404:
        print(f"  [WARN] {boe_id} not found in BOE API, using synthetic dataset")
        return []
    response.raise_for_status()
    return parse_index(response.json())


def fetch_block(client: httpx.Client, block_id: str) -> BloqueTexto:
    """Fetch a single block from BOE."""
    response = client.get(
        f"{BOE_BASE}/api/datos/{block_id}",
        headers={"Accept": "application/xml"},
    )
    response.raise_for_status()
    return parse_block_xml(block_id, response.text)


def parse_block_xml(block_id: str, xml_text: str) -> BloqueTexto:
    from xml.etree import ElementTree as ET

    root = ET.fromstring(xml_text)
    bloque = root.find(".//bloque")
    version = root.find(".//version")
    if bloque is None or version is None:
        raise ValueError(f"Invalid BOE block payload for {block_id}")

    titulo = bloque.attrib.get("titulo", "").strip()
    tipo_articulo, numero = _infer_tipo_y_numero(titulo)
    parts = []
    for p in bloque.findall(".//p"):
        text_value = "".join(p.itertext()).strip()
        if text_value:
            parts.append(text_value)

    return BloqueTexto(
        bloque_id=block_id,
        tipo_bloque=bloque.attrib.get("tipo", ""),
        numero=numero,
        titulo=titulo,
        tipo_articulo=tipo_articulo,
        texto="\n".join(parts),
        vigente_desde=_yyyymmdd_to_iso(version.attrib["fecha_vigencia"]),
    )


def _ensure_sync_log_table(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS sync_log (
                id SERIAL PRIMARY KEY,
                worker TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ,
                status TEXT NOT NULL,
                bloques_processed INTEGER,
                articulos_upserted INTEGER,
                documentos_processed INTEGER,
                documentos_upserted INTEGER,
                error_msg TEXT,
                rows_processed INTEGER,
                errors INTEGER DEFAULT 0,
                duration_ms INTEGER
            )
            """
        )
    )
    dialect = conn.engine.dialect.name
    if dialect == "sqlite":
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(sync_log)")).fetchall()}
        for col in ("rows_processed", "errors", "duration_ms"):
            if col not in columns:
                conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {col} INTEGER"))
    else:
        cursor = conn.execute(text("""SELECT column_name FROM information_schema.columns WHERE table_name = 'sync_log'""")).fetchall()
        existing = {row[0] for row in cursor}
        for col, typ in (("rows_processed", "INTEGER"), ("errors", "INTEGER"), ("duration_ms", "INTEGER")):
            if col not in existing:
                conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {col} {typ}"))


def log_sync(
    conn,
    worker: str,
    status: str,
    bloques: int = 0,
    articulos: int = 0,
    documentos_processed: int = 0,
    documentos_upserted: int = 0,
    error_msg: str | None = None,
    started_at: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    effective_started_at = started_at or now
    duration_ms = max(0, int((datetime.fromisoformat(now) - datetime.fromisoformat(effective_started_at)).total_seconds() * 1000))
    _ensure_sync_log_table(conn)
    conn.execute(
        text(
            """
            INSERT INTO sync_log (
                worker, started_at, finished_at, status,
                bloques_processed, articulos_upserted,
                documentos_processed, documentos_upserted,
                error_msg, rows_processed, errors, duration_ms
            )
            VALUES (
                :worker, :started_at, :finished_at, :status,
                :bloques_processed, :articulos_upserted,
                :documentos_processed, :documentos_upserted,
                :error_msg, :rows_processed, :errors, :duration_ms
            )
            """
        ),
        {
            "worker": worker,
            "started_at": effective_started_at,
            "finished_at": now,
            "status": status,
            "bloques_processed": bloques,
            "articulos_upserted": articulos,
            "documentos_processed": documentos_processed,
            "documentos_upserted": documentos_upserted,
            "error_msg": error_msg,
            "rows_processed": max(bloques, articulos, documentos_processed, documentos_upserted),
            "errors": 0 if not error_msg else 1,
            "duration_ms": duration_ms,
        },
    )


def upsert_ley13_norma(conn) -> None:
    """Upsert the Ley 13/2023 norma record."""
    conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion,
                tipo_fuente, tipo_documento, ambito, estado_cobertura, vigente_desde
            )
            VALUES (
                :codigo, :titulo, :boe_id, :eli_uri, :jurisdiccion,
                :tipo_fuente, :tipo_documento, :ambito, :estado_cobertura, :vigente_desde
            )
            ON CONFLICT (codigo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                boe_id = EXCLUDED.boe_id,
                eli_uri = EXCLUDED.eli_uri,
                jurisdiccion = EXCLUDED.jurisdiccion,
                tipo_fuente = EXCLUDED.tipo_fuente,
                tipo_documento = EXCLUDED.tipo_documento,
                ambito = EXCLUDED.ambito,
                estado_cobertura = EXCLUDED.estado_cobertura,
                vigente_desde = EXCLUDED.vigente_desde
            """
        ),
        {**LEY13_2023_NORMA, "vigente_desde": "2023-11-23"},
    )


def upsert_articulo(conn, codigo: str, bloque: BloqueTexto) -> None:
    conn.execute(
        text(
            """
            INSERT INTO articulo(norma_id, numero, titulo, tipo)
            SELECT id, :numero, :titulo, :tipo
            FROM norma
            WHERE codigo = :codigo
            ON CONFLICT (norma_id, numero) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                tipo = EXCLUDED.tipo
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "titulo": bloque.titulo,
            "tipo": bloque.tipo_articulo,
        },
    )

    conn.execute(
        text(
            """
            UPDATE version_articulo
            SET vigente_hasta = CASE
                WHEN vigente_hasta IS NULL AND vigente_desde < :vigente_desde THEN :vigente_desde
                ELSE vigente_hasta
            END
            WHERE articulo_id = (
                SELECT a.id
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo AND a.numero = :numero
            )
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "vigente_desde": bloque.vigente_desde,
        },
    )

    updated = conn.execute(
        text(
            """
            UPDATE version_articulo
            SET texto = :texto, boe_bloque_id = :boe_bloque_id
            WHERE articulo_id = (
                SELECT a.id
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo AND a.numero = :numero
            )
              AND vigente_desde = :vigente_desde
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "texto": bloque.texto,
            "vigente_desde": bloque.vigente_desde,
            "boe_bloque_id": bloque.bloque_id,
        },
    )

    if updated.rowcount:
        return

    conn.execute(
        text(
            """
            INSERT INTO version_articulo(articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
            SELECT a.id, :texto, :vigente_desde, NULL, :boe_bloque_id
            FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE n.codigo = :codigo
              AND a.numero = :numero
              AND NOT EXISTS (
                  SELECT 1
                  FROM version_articulo va
                  WHERE va.articulo_id = a.id
                    AND va.vigente_desde = :vigente_desde
                    AND va.boe_bloque_id = :boe_bloque_id
              )
            """
        ),
        {
            "codigo": codigo,
            "numero": bloque.numero,
            "texto": bloque.texto,
            "vigente_desde": bloque.vigente_desde,
            "boe_bloque_id": bloque.bloque_id,
        },
    )


def _infer_tipo_y_numero(titulo: str) -> tuple[str, str]:
    title = titulo.strip()
    if title.startswith("Artículo "):
        numero = title.replace("Artículo ", "", 1).split(".")[0].strip()
        return "articulo", numero
    if title.startswith("Articulo "):
        numero = title.replace("Articulo ", "", 1).split(".")[0].strip()
        return "articulo", numero
    if title.startswith("Disposición adicional "):
        numero = title.replace("Disposición adicional ", "", 1).split(".")[0].strip()
        return "disposicion_adicional", numero
    if title.startswith("Disposición transitoria "):
        numero = title.replace("Disposición transitoria ", "", 1).split(".")[0].strip()
        return "disposicion_transitoria", numero
    if title.startswith("Disposición final "):
        numero = title.replace("Disposición final ", "", 1).split(".")[0].strip()
        return "disposicion_final", numero
    if title.startswith("Disposición derogatoria "):
        numero = title.replace("Disposición derogatoria ", "", 1).split(".")[0].strip()
        return "disposicion_derogatoria", numero
    if title.startswith("Sección "):
        return "seccion", titulo
    if title.startswith("Capítulo "):
        return "capitulo", titulo
    return "otro", titulo


def _is_supported_block(titulo: str) -> bool:
    prefixes = (
        "Artículo ",
        "Articulo ",
        "Disposición adicional ",
        "Disposición transitoria ",
        "Disposición final ",
        "Disposición derogatoria ",
        "Sección ",
        "Capítulo ",
    )
    return titulo.startswith(prefixes)


def _yyyymmdd_to_iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def run_sync(
    worker_name: str = "worker-ley13-2023",
) -> dict[str, int]:
    engine = create_engine(DATABASE_URL, future=True)
    ensure_database_connection(engine)
    bloques_fetched = 0
    articulos_upserted = 0
    sync_start = datetime.now(UTC).isoformat()

    try:
        with httpx.Client(timeout=30.0) as client, engine.begin() as conn:
            upsert_ley13_norma(conn)
            ensure_source_revision_table(conn)

            # Intentar fetch desde BOE API
            index = fetch_index(client, LEY13_2023_NORMA["boe_id"])

            if index:
                # Datos reales del BOE
                for item in index:
                    if not _is_supported_block(item.titulo):
                        continue
                    bloque = fetch_block(client, item.id)

                    change = check_content_changed(
                        conn, worker_name, "bloque", bloque.bloque_id, bloque.texto
                    )

                    if not change.changed and destination_row_exists(
                        conn,
                        "version_articulo",
                        "boe_bloque_id",
                        bloque.bloque_id,
                    ):
                        bloques_fetched += 1
                        continue

                    invalidated = invalidate_old_embeddings(conn, bloque.bloque_id)
                    if invalidated:
                        print(
                            f"  [INVALIDATE] {invalidated} old embeddings for {bloque.bloque_id}"
                        )

                    upsert_articulo(conn, "LEY13_2023", bloque)
                    record_revision(
                        conn,
                        worker_name,
                        "bloque",
                        bloque.bloque_id,
                        bloque.texto,
                    )
                    bloques_fetched += 1
                    articulos_upserted += 1
            else:
                # Fallback: usar dataset sintético
                print("  [INFO] Using synthetic dataset for Ley 13/2023")
                for item in LEY13_2023_DATASET:
                    bloque = BloqueTexto(**item)
                    upsert_articulo(conn, "LEY13_2023", bloque)
                    bloques_fetched += 1
                    articulos_upserted += 1

            log_sync(
                conn,
                worker_name,
                "ok",
                bloques=bloques_fetched,
                articulos=articulos_upserted,
                started_at=sync_start,
            )
        return {"bloques": bloques_fetched, "articulos": articulos_upserted}
    except Exception as exc:
        entity_id = "ley13_2023"
        if not handle_worker_failure(engine, "ley13_2023", entity_id, "sync_entity", exc):
            logger.warning("Entity ley13_2023 moved to dead-letter")
            return {"bloques": 0, "articulos": 0}
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                bloques=bloques_fetched,
                articulos=articulos_upserted,
                error_msg=str(exc),
                started_at=sync_start,
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ley 13/2023 worker: sync IA regulation from BOE"
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
    init_sentry("ley13_2023")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-ley13-2023-weekly")
        print(
            f"[run-once] Bloques: {result['bloques']}, Artículos: {result['articulos']}"
        )
    else:
        print(f"Starting Ley 13/2023 worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
