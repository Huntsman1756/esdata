"""Worker BOE — Boletin Oficial del Estado.

Fuente: https://www.boe.es/diario_boe/xml.php (XML diario) + API ELI.
Persistencia: tablas `norma`, `articulo`, `version_articulo` con
`tipo_fuente='boe'`. Conflict key: `norma.codigo` UNIQUE y
`articulo (norma_id, numero)` UNIQUE.

Sync intervalo: diario via cron (ver `docker-compose.prod.yml`).
Auditoria: cada ejecucion escribe en `sync_log` (worker='worker-boe').

Limitaciones conocidas:
- Parser HTML de articulado depende de la estructura del XML BOE; cambios
  en upstream pueden generar `[PARTIAL]` rows.
- Consolidacion (texto vigente) parcial: solo se almacena ultima version
  conocida; histogramas de versiones no se reconstruyen retroactivamente.
"""

import argparse
from contextlib import contextmanager
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import httpx
from runtime import (
    ensure_database_connection,
    handle_worker_failure,
    sleep_with_heartbeat,
    touch_heartbeat,
)
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)

BOE_API_BASE = os.getenv(
    "BOE_API_BASE",
    "https://www.boe.es/datosabiertos/api/legislacion-consolidada",
)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://esdata:esdata_dev@localhost:5432/esdata",
)
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "3600"))

DEFAULT_NORMAS = {
    "LIVA": "BOE-A-1992-28740",
    "LIRPF": "BOE-A-2006-20764",
    "LIS": "BOE-A-2014-12328",
    "LGT": "BOE-A-2003-23186",
    "ITPAJD": "BOE-A-1993-253",
    # Added 2026-05-09 per audit: compliance domains gap
    "LEY10_2010": "BOE-A-2010-6737",       # Ley 10/2010 Prevencion blanqueo capitales (SEPBLAC)
    "RDL19_2018": "BOE-A-2018-16036",      # RDL 19/2018 Servicios de pago — implementa PSD2 en Espana
}

KNOWN_BOE_CODES = set(DEFAULT_NORMAS.keys())
BOE_SYNC_LOCK_KEY = 88420032

NORMA_CLASSIFICATIONS = {
    "LIVA": {"tipo_documento": "ley", "ambito": "tributario"},
    "LIRPF": {"tipo_documento": "ley", "ambito": "tributario"},
    "LIS": {"tipo_documento": "ley", "ambito": "tributario"},
    "LGT": {"tipo_documento": "ley", "ambito": "tributario"},
    "ITPAJD": {
        "tipo_documento": "real_decreto_legislativo",
        "ambito": "tributario",
    },
    "LEY10_2010": {"tipo_documento": "ley", "ambito": "prevencion_blanqueo"},
    "RDL19_2018": {
        "tipo_documento": "real_decreto_ley",
        "ambito": "servicios_pago",
    },
}

LAW_TO_NORMA = {
    "37/1992": "LIVA",
    "27/2014": "LIS",
    "35/2006": "LIRPF",
    "58/2003": "LGT",
    "10/2010": "LEY10_2010",
    "19/2018": "RDL19_2018",
}


_SYNC_LOG_BOOTSTRAP_LOGGED: set[str] = set()


def _ensure_sync_log_table(conn) -> None:
    """Garantiza tabla `sync_log` (no-op en todos los dialects; schema owned por Alembic)."""
    dialect = conn.engine.dialect.name
    if dialect not in _SYNC_LOG_BOOTSTRAP_LOGGED:
        _SYNC_LOG_BOOTSTRAP_LOGGED.add(dialect)


@dataclass
class NormaMetadata:
    codigo: str
    boe_id: str
    titulo: str
    eli_uri: str | None
    jurisdiccion: str
    tipo_fuente: str
    tipo_documento: str
    ambito: str
    estado_cobertura: str
    vigente_desde: str


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


def parse_metadata(codigo: str, boe_id: str, payload: dict) -> NormaMetadata:
    item = payload["data"][0]
    classification = NORMA_CLASSIFICATIONS[codigo]
    return NormaMetadata(
        codigo=codigo,
        boe_id=boe_id,
        titulo=item["titulo"],
        eli_uri=item.get("url_eli"),
        jurisdiccion="es",
        tipo_fuente="boe",
        tipo_documento=classification["tipo_documento"],
        ambito=classification["ambito"],
        estado_cobertura="ingestada",
        vigente_desde=_yyyymmdd_to_iso(item["fecha_vigencia"]),
    )


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


def parse_metadata_from_xml(codigo: str, boe_id: str, xml_text: str) -> NormaMetadata:
    root = ET.fromstring(xml_text)
    metadatos = root.find("metadatos")
    if metadatos is None:
        raise ValueError(f"No metadatos element in XML for {codigo}/{boe_id}")

    def get_text(tag: str) -> str | None:
        elem = metadatos.find(tag)
        return elem.text.strip() if elem is not None and elem.text else None

    titulo = get_text("titulo") or ""
    eli_url = get_text("url_eli")
    fecha_vigencia_raw = get_text("fecha_vigencia") or "19700101"

    classification = NORMA_CLASSIFICATIONS[codigo]
    return NormaMetadata(
        codigo=codigo,
        boe_id=boe_id,
        titulo=titulo,
        eli_uri=eli_url,
        jurisdiccion="es",
        tipo_fuente="boe",
        tipo_documento=classification["tipo_documento"],
        ambito=classification["ambito"],
        estado_cobertura="ingestada",
        vigente_desde=_yyyymmdd_to_iso(fecha_vigencia_raw),
    )


def _parse_xml_index(xml_text: str) -> list[BloqueIndex]:
    """Parse article list from the consolidated XML."""
    root = ET.fromstring(xml_text)
    texto = root.find("texto")
    if texto is None:
        return []

    articles = []
    for child in texto:
        if child.tag == "p":
            text_content = (child.text or "").strip()
            if re.match(r"Artículo\s+\d+", text_content, re.IGNORECASE):
                articles.append(
                    BloqueIndex(
                        id=text_content,
                        titulo=text_content,
                        fecha_actualizacion="",
                    )
                )
    return articles


def _extract_xml_block(xml_text: str, block_id: str) -> BloqueTexto:
    """Extract a single article block from the consolidated XML."""
    root = ET.fromstring(xml_text)
    texto = root.find("texto")
    if texto is None:
        raise ValueError(f"No texto element in XML for {block_id}")

    parts = []
    found = False
    for child in texto:
        text_content = (child.text or "").strip()
        if child.tag == "p" and block_id in text_content:
            found = True
            parts.append(text_content)
        elif found:
            if child.tag == "p" and re.match(r"Artículo\s+\d+", text_content, re.IGNORECASE):
                break
            if child.tag == "p":
                parts.append(text_content)
            elif child.tag in ("div", "section", "chapter", "title"):
                parts.append((child.text or "") + "".join(child.itertext()))

    if not parts:
        raise ValueError(f"No content found for block {block_id}")

    titulo = parts[0]
    tipo_articulo, numero = _infer_tipo_y_numero(titulo)
    full_text = "\n".join(p for p in parts if p)

    return BloqueTexto(
        bloque_id=block_id,
        tipo_bloque="articulo",
        numero=numero,
        titulo=titulo,
        tipo_articulo=tipo_articulo,
        texto=full_text,
        vigente_desde="",
    )


def fetch_index(client: httpx.Client, boe_id: str) -> list[BloqueIndex]:
    # Try the consolidated JSON API first
    try:
        response = client.get(
            f"{BOE_API_BASE}/id/{boe_id}/texto/indice",
            headers={"Accept": "application/json"},
        )
        if getattr(response, "status_code", 200) == 200:
            return parse_index(response.json())
    except (httpx.HTTPStatusError, httpx.RequestError):
        pass

    # Fallback: parse XML for article list
    xml_url = f"https://www.boe.es/diario_boe/xml.php?id={boe_id}"
    response = client.get(xml_url, timeout=60.0)
    response.raise_for_status()
    return _parse_xml_index(response.text)


def fetch_block(client: httpx.Client, boe_id: str, block_id: str) -> BloqueTexto:
    # Try the consolidated JSON API first
    try:
        response = client.get(
            f"{BOE_API_BASE}/id/{boe_id}/texto/bloque/{block_id}",
            headers={"Accept": "application/xml"},
        )
        if getattr(response, "status_code", 200) == 200:
            return parse_block_xml(block_id, response.text)
    except (httpx.HTTPStatusError, httpx.RequestError):
        pass

    # Fallback: extract from consolidated XML
    xml_url = f"https://www.boe.es/diario_boe/xml.php?id={boe_id}"
    response = client.get(xml_url, timeout=60.0)
    response.raise_for_status()
    return _extract_xml_block(response.text, block_id)


def parse_block_xml(block_id: str, xml_text: str) -> BloqueTexto:
    root = ET.fromstring(xml_text)
    bloque = root.find(".//bloque")
    version = root.find(".//version")
    if bloque is None or version is None:
        raise ValueError(f"Invalid BOE block payload for {block_id}")

    titulo = bloque.attrib.get("titulo", "").strip()
    tipo_articulo, numero = _infer_tipo_y_numero(titulo)
    parts = []
    for p in version.findall("p"):
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


def fetch_metadata(client: httpx.Client, codigo: str, boe_id: str) -> NormaMetadata:
    # Try the consolidated JSON API first
    try:
        response = client.get(
            f"{BOE_API_BASE}/id/{boe_id}/metadatos", headers={"Accept": "application/json"}
        )
        if getattr(response, "status_code", 200) == 200:
            return parse_metadata(codigo, boe_id, response.json())
    except (httpx.HTTPStatusError, httpx.RequestError):
        pass

    # Fallback: parse XML metadata
    xml_url = f"https://www.boe.es/diario_boe/xml.php?id={boe_id}"
    response = client.get(xml_url, timeout=30.0)
    response.raise_for_status()
    return parse_metadata_from_xml(codigo, boe_id, response.text)


def upsert_norma(conn, metadata: NormaMetadata) -> None:
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
        metadata.__dict__,
    )


def upsert_articulo(conn, codigo: str, bloque: BloqueTexto) -> None:
    conn.execute(
        text(
            """
            INSERT INTO articulo (norma_id, numero, titulo, tipo)
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
            SET texto = :texto,
                boe_bloque_id = :boe_bloque_id
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
            INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
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


def auto_link_materias(conn) -> int:
    """Link materias to articles based on keyword matching in article text.

    Each materia has curated keywords. We search for these keywords in the
    text of all articles and create articulo_materia links with relevance=2
    (principal) when found.
    """
    materias = list(
        conn.execute(text("SELECT slug, etiqueta FROM materia ORDER BY slug")).mappings()
    )

    # Curated keyword sets per materia slug
    keyword_map = {
        "tipo-reducido-iva": [
            "tipo reducido",
            "tipo impositivo reducido",
            "6 por 100",
            "10 por 100",
            "3 por 100",
            "superreducido",
        ],
    }

    links_created = 0
    for mat in materias:
        keywords = keyword_map.get(mat["slug"], [mat["etiqueta"].lower()])
        for kw in keywords:
            rows = conn.execute(
                text(
                    """
                SELECT DISTINCT a.id, n.codigo
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                JOIN version_articulo va ON va.articulo_id = a.id
                WHERE LOWER(va.texto) LIKE :kw
                  AND NOT EXISTS (
                      SELECT 1 FROM articulo_materia am
                      WHERE am.articulo_id = a.id AND am.materia_id = (
                          SELECT id FROM materia WHERE slug = :slug
                      )
                  )
                """
                ),
                {"kw": f"%{kw}%", "slug": mat["slug"]},
            ).mappings()

            for row in rows:
                conn.execute(
                    text(
                        """
                    INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
                    SELECT :articulo_id, id, 2
                    FROM materia
                    WHERE slug = :slug
                    ON CONFLICT (articulo_id, materia_id) DO NOTHING
                    """
                    ),
                    {"articulo_id": row["id"], "slug": mat["slug"]},
                )
                links_created += 1

    return links_created


def auto_link_doctrina(conn) -> int:
    """Link doctrine documents to articles by parsing references in doctrine text.

    Looks for patterns like "LIVA 91", "art. 91", "artículo 91", etc.
    """
    docs = list(
        conn.execute(text("SELECT id, referencia, texto FROM documento_interpretativo")).mappings()
    )

    links_created = 0
    for doc in docs:
        found_refs = _extract_doctrina_refs(doc["texto"])

        for codigo, numero, confianza, metodo_enlace in found_refs:
            conn.execute(
                text(
                    """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT :doc_id, a.id, :metodo_enlace, :confianza_enlace, :nota
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo AND a.numero = :numero
                ON CONFLICT (documento_id, articulo_id)
                DO UPDATE SET
                    metodo_enlace = EXCLUDED.metodo_enlace,
                    confianza_enlace = EXCLUDED.confianza_enlace,
                    nota = EXCLUDED.nota
                WHERE documento_articulo.metodo_enlace IN (
                    'auto_link',
                    'auto_link_exact',
                    'auto_link_heuristic'
                )
                AND (
                    (
                        EXCLUDED.metodo_enlace = 'auto_link_exact'
                        AND documento_articulo.metodo_enlace IN (
                            'auto_link',
                            'auto_link_heuristic'
                        )
                    )
                    OR (
                        EXCLUDED.metodo_enlace = 'auto_link_heuristic'
                        AND documento_articulo.metodo_enlace = 'auto_link'
                    )
                    OR (
                        EXCLUDED.metodo_enlace = documento_articulo.metodo_enlace
                        AND EXCLUDED.confianza_enlace > documento_articulo.confianza_enlace
                    )
                )
                """
                ),
                {
                    "doc_id": doc["id"],
                    "codigo": codigo,
                    "numero": numero,
                    "metodo_enlace": metodo_enlace,
                    "confianza_enlace": confianza,
                    "nota": f"Referencia auto-detectada: {codigo} art. {numero}",
                },
            )
            links_created += 1

    return links_created


def _extract_doctrina_refs(text_value: str) -> set[tuple[str, str, float, str]]:
    explicit_norma_refs = set()
    source = text_value.upper()

    explicit_patterns = [
        re.compile(r"\b(LIVA|LIRPF|LIS|LGT)\s+(\d+)\b", re.IGNORECASE),
        re.compile(r"\b(LIVA|LIRPF|LIS|LGT)\s+ART\.?\s*(\d+)\b", re.IGNORECASE),
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)\s+DE\s+LA\s+(LIVA|LIRPF|LIS|LGT)\b", re.IGNORECASE
        ),
        re.compile(r"ART\.?\s*(\d+)\s+DE\s+LA\s+(LIVA|LIRPF|LIS|LGT)\b", re.IGNORECASE),
        re.compile(r"\bART\.?\s+(\d+)\s+(LIVA|LIRPF|LIS|LGT)\b", re.IGNORECASE),
    ]

    for pattern in explicit_patterns:
        for match in pattern.finditer(source):
            first, second = match.groups()
            if first.isdigit():
                numero, codigo = first, second
            else:
                codigo, numero = first, second
            explicit_norma_refs.add((codigo.upper(), numero, 1.00, "auto_link_exact"))

    law_patterns = [
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][0-9A-ZÁÉÍÓÚÜÑº]+\)?(?:\s+[0-9A-ZÁÉÍÓÚÜÑº]+\)?)?)*\s+DE\s+LA\s+LEY\s+(\d+/\d{4})(?:\s+DEL\s+[A-ZÁÉÍÓÚÜÑ]+)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)(?:[\.,][0-9A-ZÁÉÍÓÚÜÑº]+\)?(?:\s+[0-9A-ZÁÉÍÓÚÜÑº]+\)?)?)*\s+DE\s+LA\s+LEY\s+(\d+/\d{4})(?:\s+DEL\s+[A-ZÁÉÍÓÚÜÑ]+)?\b",
            re.IGNORECASE,
        ),
    ]

    for pattern in law_patterns:
        for match in pattern.finditer(source):
            numero, ley = match.groups()
            codigo = LAW_TO_NORMA.get(ley)
            if codigo:
                explicit_norma_refs.add((codigo, numero, 1.00, "auto_link_exact"))

    # Named law alias: "de la Ley del IVA" -> LIVA
    for pattern in [
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+DEL\s+IVA\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+DEL\s+IVA\b",
            re.IGNORECASE,
        ),
    ]:
        for match in pattern.finditer(source):
            explicit_norma_refs.add(("LIVA", match.group(1), 1.00, "auto_link_exact"))

    if explicit_norma_refs:
        return explicit_norma_refs

    # Explicit law name mention (no article attached): e.g. "a efectos de la Ley del IVA"
    # If only one explicit law name is mentioned, resolve standalone article refs to it.
    explicit_law_normas = set()
    if re.search(r"\bLEY\s+DEL\s+IVA\b", source):
        explicit_law_normas.add("LIVA")
    if re.search(r"\bLEY\s+GENERAL\s+TRIBUTARIA\b", source):
        explicit_law_normas.add("LGT")

    if len(explicit_law_normas) == 1:
        sola_norma = explicit_law_normas.pop()
        article_refs = set()
        for match in re.finditer(r"(?:ART[ÍI]?CULO|ART\.?)\s+(\d+)\b", source):
            article_refs.add((sola_norma, match.group(1), 1.00, "auto_link_exact"))
        if article_refs:
            return article_refs

    # Small first contextual heuristic for doctrine without explicit article citation.
    # TEAC resolutions about IVA + base imponible often target LIVA art. 91 in our MVP set.
    if "IVA" in source and "BASE IMPONIBLE" in source:
        return {("LIVA", "91", 0.75, "auto_link_heuristic")}
    if "IVA" in source and "REGIMEN ESPECIAL" in source:
        return {("LIVA", "91", 0.75, "auto_link_heuristic")}
    if "IVA" in source and "RECARGO DE EQUIVALENCIA" in source:
        return {("LIVA", "24", 0.75, "auto_link_heuristic")}

    context_normas = []
    for codigo in DEFAULT_NORMAS:
        if re.search(rf"\b{codigo}\b", source):
            context_normas.append(codigo)

    if "IVA" in source and "LIVA" not in context_normas:
        context_normas.append("LIVA")
    if "SOCIEDADES" in source and "LIS" not in context_normas:
        context_normas.append("LIS")
    if "IRPF" in source and "LIRPF" not in context_normas:
        context_normas.append("LIRPF")

    if len(context_normas) != 1:
        return set()

    contextual_refs = set()
    for match in re.finditer(r"(?:ART[ÍI]?CULO|ART\.?)\s+(\d+)\b", source):
        contextual_refs.add((context_normas[0], match.group(1), 0.85, "auto_link_heuristic"))

    return contextual_refs


def log_sync(
    conn,
    worker: str,
    status: str,
    bloques: int = 0,
    articulos: int = 0,
    documentos_processed: int = 0,
    documentos_upserted: int = 0,
    doctrina_links_created: int = 0,
    error_msg: str | None = None,
    started_at: str | None = None,
) -> None:
    if conn is None:
        logging.getLogger(__name__).warning("log_sync llamado con conn=None, skip")
        return
    now = datetime.now(timezone.utc).isoformat()
    effective_started_at = started_at or now
    _ensure_sync_log_table(conn)
    conn.execute(
        text(
            """
            INSERT INTO sync_log (
                worker,
                started_at,
                finished_at,
                status,
                bloques_processed,
                articulos_upserted,
                documentos_processed,
                documentos_upserted,
                doctrina_links_created,
                error_msg
            )
            VALUES (
                :worker,
                :started_at,
                :finished_at,
                :status,
                :bloques_processed,
                :articulos_upserted,
                :documentos_processed,
                :documentos_upserted,
                :doctrina_links_created,
                :error_msg
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
            "doctrina_links_created": doctrina_links_created,
            "error_msg": error_msg,
        },
    )


def _ensure_schema(conn) -> None:
    """Ensure worker-owned schema objects exist before syncing.

    Tables are created by Alembic only. This function ensures
    extensions and indexes that the worker needs exist.
    """
    dialect = conn.engine.dialect.name

    if dialect == "postgresql":
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

        idx_exists = conn.execute(
            text(
                """
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_version_articulo_texto_trgm'
            )
            """
            )
        ).scalar()

        if not idx_exists:
            conn.execute(
                text(
                    "CREATE INDEX idx_version_articulo_texto_trgm ON version_articulo USING gin (texto gin_trgm_ops)"
                )
            )


def _report_idle_in_transaction_connections(engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.connect() as check_conn:
        idle = check_conn.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE state = 'idle in transaction' "
                "AND pid != pg_backend_pid()"
            )
        ).scalar()
        if idle > 0:
            print(f"  DEADLOCK_RISK: {idle} conexiones idle in transaction tras run_sync")


def _try_acquire_sync_lock(conn) -> bool:
    dialect = getattr(getattr(conn, "engine", None), "dialect", None)
    if getattr(dialect, "name", None) != "postgresql":
        return True

    row = conn.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
        {"lock_key": BOE_SYNC_LOCK_KEY},
    ).fetchone()
    return bool(row[0]) if row else False


@contextmanager
def _hold_sync_lock(engine):
    if engine.dialect.name != "postgresql":
        yield True
        return

    lock_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    acquired = False
    try:
        acquired = bool(
            lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": BOE_SYNC_LOCK_KEY},
            ).scalar()
        )
        yield acquired
    finally:
        try:
            if acquired:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": BOE_SYNC_LOCK_KEY},
                )
        finally:
            lock_conn.close()


def run_sync(
    codigos: list[str] | None = None,
    worker_name: str = "worker-boe",
) -> dict[str, int]:
    target_codes = codigos or [
        code.strip()
        for code in os.getenv("BOE_LEGISLACION_NORMAS", "LIVA").split(",")
        if code.strip()
    ]
    unknown_codes = [c for c in target_codes if c not in KNOWN_BOE_CODES]
    if unknown_codes:
        logging.warning(
            "BOE worker: skipping unknown codes not in DEFAULT_NORMAS: %s. "
            "Add them to DEFAULT_NORMAS or remove from BOE_LEGISLACION_NORMAS.",
            unknown_codes,
        )
        target_codes = [c for c in target_codes if c in KNOWN_BOE_CODES]
    only_block_ids = [
        item.strip()
        for item in os.getenv("BOE_ONLY_BLOCK_IDS", "").split(",")
        if item.strip()
    ]
    engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
    ensure_database_connection(engine, logger=logging.getLogger(__name__))
    total_bloques = 0
    total_articulos = 0
    run_start = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=30.0) as client:
        with _hold_sync_lock(engine) as lock_acquired:
            with engine.begin() as conn:
                _ensure_schema(conn)

            if not lock_acquired:
                with engine.begin() as conn:
                    log_sync(
                        conn,
                        worker_name,
                        "partial",
                        bloques=0,
                        articulos=0,
                        error_msg="BOE sync already in progress",
                        started_at=run_start,
                    )
                print("  SKIP BOE: BOE sync already in progress")
                _report_idle_in_transaction_connections(engine)
                return {"bloques": 0, "articulos": 0}

            for codigo in target_codes:
                boe_id = DEFAULT_NORMAS[codigo]
                try:
                    metadata = fetch_metadata(client, codigo, boe_id)
                except ValueError:
                    print(f"  SKIP {codigo} ({boe_id}): not in BOE API")
                    continue

                bloques_fetched = 0
                articulos_upserted = 0
                ley_start = datetime.now(timezone.utc).isoformat()
                try:
                    with engine.begin() as conn:
                        upsert_norma(conn, metadata)
                    index = fetch_index(client, boe_id)
                    for item in index:
                        if not _is_supported_block(item.titulo):
                            continue
                        if only_block_ids and item.id not in only_block_ids:
                            continue
                        touch_heartbeat()
                        bloque = fetch_block(client, boe_id, item.id)
                        with engine.begin() as conn:
                            upsert_articulo(conn, codigo, bloque)
                        bloques_fetched += 1
                        articulos_upserted += 1
                        time.sleep(float(os.environ.get("WORKER_REQUEST_DELAY", "1.0")))

                    with engine.begin() as conn:
                        auto_link_materias(conn)
                        auto_link_doctrina(conn)
                        log_sync(
                            conn,
                            worker_name,
                            "ok",
                            bloques=bloques_fetched,
                            articulos=articulos_upserted,
                            started_at=ley_start,
                        )
                    total_bloques += bloques_fetched
                    total_articulos += articulos_upserted
                    print(f"  DONE {codigo}: {bloques_fetched} blocks, {articulos_upserted} articulos")
                except Exception as exc:
                    print(
                        f"  ERROR {codigo}: {exc} at {datetime.now(timezone.utc).isoformat()}"
                    )
                    try:
                        with engine.begin() as conn:
                            log_sync(
                                conn,
                                worker_name,
                                "error",
                                bloques=bloques_fetched,
                                articulos=articulos_upserted,
                                error_msg=str(exc),
                                started_at=ley_start,
                            )
                    except Exception as e:
                        logger.error("Failed to write sync_log for error logging: %s", e)

    _report_idle_in_transaction_connections(engine)

    return {"bloques": total_bloques, "articulos": total_articulos}


def _yyyymmdd_to_iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _infer_tipo_y_numero(titulo: str) -> tuple[str, str]:
    title = titulo.strip()
    if title.startswith("Artículo "):
        numero = title.replace("Artículo ", "", 1).split(".")[0].strip()
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
    return "otro", title


def _is_supported_block(titulo: str) -> bool:
    prefixes = (
        "Artículo ",
        "Disposición adicional ",
        "Disposición transitoria ",
        "Disposición final ",
        "Disposición derogatoria ",
    )
    return titulo.startswith(prefixes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BOE worker: sync consolidated legislation from BOE API"
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

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-boe-daily")
        print(
            f"[run-once] Bloques: {result['bloques']}, Artículos: {result['articulos']}"
        )
    else:
        print(f"Starting BOE worker in continuous mode (interval={interval}s)")
        while True:
            touch_heartbeat()
            try:
                result = run_sync()
                print(
                    f"Synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(timezone.utc).isoformat()}"
                )
            except Exception as exc:
                print(f"[ERROR] Sync failed: {exc} at {datetime.now(timezone.utc).isoformat()}")
            sleep_with_heartbeat(interval)
