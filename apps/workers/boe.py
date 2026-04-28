import argparse
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

import httpx
from change_detection import (
    check_content_changed,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_bool_env, get_database_url, get_interval_seconds
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

BOE_API_BASE = os.getenv(
    "BOE_API_BASE",
    "https://www.boe.es/datosabiertos/api/legislacion-consolidada",
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 3600)
BOE_TRACK_VERSIONS = get_bool_env("BOE_TRACK_VERSIONS", False)

# Rate limit for BOE API: 10 req/min = 6 sec between requests
BOE_RATE_LIMIT_SECONDS = 6.0

DEFAULT_NORMAS = {
    "LIVA": "BOE-A-1992-28740",
    "LIRPF": "BOE-A-2006-20764",
    "LIS": "BOE-A-2014-12328",
    "LGT": "BOE-A-2003-23186",
    "ITPAJD": "BOE-A-1993-25359",
    "IRNR": "BOE-A-2004-4527",
    "IIEE": "BOE-A-1992-28741",
    "HL": "BOE-A-2004-4214",
    "DAC6": "BOE-A-2020-17265",
    "DAC6RD": "BOE-A-2021-5394",
    "RIRPF": "BOE-A-2007-6820",
    "RIVA": "BOE-A-1992-28759",
    "RIS": "BOE-A-2014-12531",
    "RD1080": "BOE-A-2015-12843",
    "LIVA_IGIC": "BOE-A-2022-5689",
    "TRLMV": "BOE-A-2011-14568",
    "LEY62018": "BOE-A-2018-10582",
    "NRV9": "BOE-A-2008-10273",
    "LEY222010": "BOE-A-2010-16380",
    "RD2172008": "BOE-A-2008-500",
    "LECR": "BOE-A-2014-11230",
}

NORMA_CLASSIFICATIONS = {
    "LIVA": {"tipo_documento": "ley", "ambito": "tributario"},
    "LIRPF": {"tipo_documento": "ley", "ambito": "tributario"},
    "LIS": {"tipo_documento": "ley", "ambito": "tributario"},
    "LGT": {"tipo_documento": "ley", "ambito": "tributario"},
    "ITPAJD": {
        "tipo_documento": "real_decreto_legislativo",
        "ambito": "tributario",
    },
    "IRNR": {
        "tipo_documento": "real_decreto_legislativo",
        "ambito": "tributario",
    },
    "IIEE": {
        "tipo_documento": "ley",
        "ambito": "tributario",
    },
    "HL": {
        "tipo_documento": "real_decreto_legislativo",
        "ambito": "tributario_local",
    },
    "DAC6": {
        "tipo_documento": "ley",
        "ambito": "tributario_internacional",
    },
    "DAC6RD": {
        "tipo_documento": "real_decreto",
        "ambito": "tributario_internacional",
    },
    "DAC6EU": {
        "tipo_documento": "directiva_ue",
        "ambito": "tributario_ue",
    },
    "RIRPF": {
        "tipo_documento": "real_decreto",
        "ambito": "tributario",
    },
    "RIVA": {
        "tipo_documento": "real_decreto",
        "ambito": "tributario",
    },
    "RIRNR": {
        "tipo_documento": "real_decreto",
        "ambito": "tributario",
    },
    "RIS": {
        "tipo_documento": "real_decreto",
        "ambito": "tributario",
    },
    "RD1080": {
        "tipo_documento": "real_decreto",
        "ambito": "tributario",
    },
    "LIVA_IGIC": {
        "tipo_documento": "ley",
        "ambito": "tributario_canarias",
    },
    "TRLMV": {
        "tipo_documento": "real_decreto_legislativo",
        "ambito": "mercado_valores",
    },
    "LEY62018": {
        "tipo_documento": "ley",
        "ambito": "mercado_valores",
    },
    "LEY222010": {
        "tipo_documento": "ley",
        "ambito": "mercado_valores",
    },
    "RD2172008": {
        "tipo_documento": "real_decreto",
        "ambito": "contable",
    },
    "LECR": {
        "tipo_documento": "ley",
        "ambito": "capital_riesgo",
    },
}

LAW_TO_NORMA = {
    "37/1992": "LIVA",
    "27/2014": "LIS",
    "35/2006": "LIRPF",
    "58/2003": "LGT",
    "38/1992": "IIEE",
    "5/2004": "IRNR",
    "2/2004": "HL",
    "10/2020": "DAC6",
    "439/2007": "RIRPF",
    "1628/2012": "RIVA",
    "173/2014": "RIS",
    "1080/2015": "RD1080",
    "10/2022": "LIVA_IGIC",
    "1/2010": "LEYSOC",
    "1514/2006": "NRV9",
    "11/2021": "LEY112021",
    "4/2015": "TRLMV",
    "6/2018": "LEY62018",
    "22/2010": "LEY222010",
    "217/2008": "RD2172008",
    "22/2014": "LECR",
}


SCHEMA_STATEMENTS = []


def _schema_statements(dialect: str) -> list[str]:
    id_type = "SERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY"
    timestamp_default = "now()" if dialect == "postgresql" else "CURRENT_TIMESTAMP"

    return [
        f"""
        CREATE TABLE IF NOT EXISTS norma (
            id {id_type},
            codigo TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            boe_id TEXT UNIQUE NOT NULL,
            eli_uri TEXT UNIQUE,
            jurisdiccion TEXT NOT NULL,
            tipo_fuente TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            ambito TEXT NOT NULL,
            estado_cobertura TEXT NOT NULL,
            vigente_desde DATE NOT NULL,
            ultima_verificacion TEXT,
            created_at TIMESTAMPTZ DEFAULT {timestamp_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS articulo (
            id {id_type},
            norma_id INTEGER NOT NULL REFERENCES norma(id),
            numero TEXT NOT NULL,
            titulo TEXT,
            tipo TEXT NOT NULL,
            UNIQUE (norma_id, numero)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS version_articulo (
            id {id_type},
            articulo_id INTEGER NOT NULL REFERENCES articulo(id),
            texto TEXT NOT NULL,
            vigente_desde DATE NOT NULL,
            vigente_hasta DATE,
            boe_bloque_id TEXT
        )
        """,
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
            url_fuente TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS empresa (
            id {id_type},
            nombre TEXT NOT NULL,
            nif TEXT,
            domicilio TEXT,
            fuente_inicial TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT {timestamp_default},
            UNIQUE (nombre)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS obligacion_regulatoria (
            id {id_type},
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            fuente TEXT NOT NULL,
            organismo_emisor TEXT NOT NULL,
            tipo_obligacion TEXT NOT NULL,
            sujeto_obligado TEXT NOT NULL,
            periodicidad TEXT,
            reporte_modelo TEXT,
            ambito TEXT NOT NULL,
            estado_vigencia TEXT NOT NULL,
            documento_origen_tipo TEXT NOT NULL,
            documento_origen_ref TEXT NOT NULL,
            seccion_origen TEXT,
            anexo_origen TEXT,
            nota TEXT,
            created_at TIMESTAMPTZ DEFAULT {timestamp_default}
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS obligacion_documento (
            obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id),
            documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
            tipo_relacion TEXT NOT NULL,
            PRIMARY KEY (obligacion_id, documento_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS documento_empresa (
            documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            rol TEXT NOT NULL,
            confianza_extraccion NUMERIC(3,2) NOT NULL,
            nota TEXT,
            PRIMARY KEY (documento_id, empresa_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS documento_articulo (
            documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
            articulo_id INTEGER NOT NULL REFERENCES articulo(id),
            metodo_enlace TEXT NOT NULL,
            confianza_enlace NUMERIC(3,2) NOT NULL,
            nota TEXT,
            PRIMARY KEY (documento_id, articulo_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS materia (
            id {id_type},
            slug TEXT UNIQUE NOT NULL,
            etiqueta TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS articulo_materia (
            articulo_id INTEGER NOT NULL REFERENCES articulo(id),
            materia_id INTEGER NOT NULL REFERENCES materia(id),
            relevancia SMALLINT NOT NULL DEFAULT 1,
            PRIMARY KEY (articulo_id, materia_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS sync_log (
            id {id_type},
            worker TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL,
            bloques_processed INTEGER,
            articulos_upserted INTEGER,
            documentos_processed INTEGER,
            documentos_upserted INTEGER,
            doctrina_links_created INTEGER,
            error_msg TEXT,
            rows_processed INTEGER,
            errors INTEGER,
            duration_ms INTEGER
        )
        """,
    ]


def _create_base_schema(conn) -> None:
    for statement in _schema_statements(conn.engine.dialect.name):
        conn.execute(text(statement))

    conn.execute(
        text(
            """
            INSERT INTO materia (slug, etiqueta)
            VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
            ON CONFLICT (slug) DO NOTHING
            """
        )
    )


def _ensure_sync_log_table(conn) -> None:
    dialect = conn.engine.dialect.name
    _schema_statements(dialect)  # validates dialect
    if dialect == "sqlite":
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        if "sync_log" not in tables:
            conn.execute(text(_schema_statements(dialect)[-1]))
            return
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(sync_log)")).fetchall()}
        for col in ("rows_processed", "errors", "duration_ms"):
            if col not in columns:
                conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {col} INTEGER"))
    else:
        tables = {row[0] for row in conn.execute(text("""SELECT table_name FROM information_schema.tables WHERE table_name = 'sync_log'""")).fetchall()}
        if not tables:
            conn.execute(text(_schema_statements(dialect)[-1]))
            return
        cursor = conn.execute(text("""SELECT column_name FROM information_schema.columns WHERE table_name = 'sync_log'""")).fetchall()
        existing = {row[0] for row in cursor}
        for col, typ in (("rows_processed", "INTEGER"), ("errors", "INTEGER"), ("duration_ms", "INTEGER")):
            if col not in existing:
                conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {col} {typ}"))


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


# Reference-only norms can live in the same catalog even if they are not
# fetched from the BOE consolidated legislation API.
MANUAL_NORMAS = {
    "DAC6EU": NormaMetadata(
        codigo="DAC6EU",
        boe_id="DOUE-L-2018-80963",
        titulo="Directiva (UE) 2018/822 del Consejo, de 25 de mayo de 2018, que modifica la Directiva 2011/16/UE por lo que se refiere al intercambio automático y obligatorio de información en el ámbito de la fiscalidad en relación con los mecanismos transfronterizos sujetos a comunicación de información.",
        eli_uri="https://eur-lex.europa.eu/eli/dir/2018/822/oj",
        jurisdiccion="ue",
        tipo_fuente="eurlex",
        tipo_documento="directiva_ue",
        ambito="tributario_ue",
        estado_cobertura="referenciada",
        vigente_desde="2018-06-25",
    )
}


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


def fetch_index(client: httpx.Client, boe_id: str) -> list[BloqueIndex]:
    response = client.get(
        f"{BOE_API_BASE}/id/{boe_id}/texto/indice",
        headers={"Accept": "application/json"},
    )
    if response.status_code == 404:
        print(f"  [WARN] {boe_id} not found in BOE API, skipping")
        return []
    response.raise_for_status()
    return parse_index(response.json())


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


def fetch_block(client: httpx.Client, boe_id: str, block_id: str) -> BloqueTexto:
    response = client.get(
        f"{BOE_API_BASE}/id/{boe_id}/texto/bloque/{block_id}",
        headers={"Accept": "application/xml"},
    )
    response.raise_for_status()
    return parse_block_xml(block_id, response.text)


def fetch_metadata(client: httpx.Client, codigo: str, boe_id: str) -> NormaMetadata:
    """Fetch metadata from BOE API with fallback for unavailable endpoints.

    Some BOE IDs (e.g. BOE-A-1993-253 for ITPAJD) return 404 on /metadatos.
    In those cases we fall back to classification-based defaults.
    """
    try:
        response = client.get(
            f"{BOE_API_BASE}/id/{boe_id}/metadatos",
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return parse_metadata(codigo, boe_id, response.json())
    except httpx.HTTPStatusError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 404:
            # Fallback to classification-based metadata
            classification = NORMA_CLASSIFICATIONS[codigo]
            return NormaMetadata(
                codigo=codigo,
                boe_id=boe_id,
                titulo=f"Norma {codigo} ({boe_id})",
                eli_uri=None,
                jurisdiccion="es",
                tipo_fuente="boe",
                tipo_documento=classification["tipo_documento"],
                ambito=classification["ambito"],
                estado_cobertura="ingestada",
                vigente_desde="1900-01-01",  # Conservative default
            )
        raise


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
    materias = conn.execute(
        text("SELECT slug, etiqueta FROM materia ORDER BY slug")
    ).mappings()

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
    docs = conn.execute(
        text("SELECT id, referencia, texto FROM documento_interpretativo")
    ).mappings()

    links_created = 0
    for doc in docs:
        found_refs = _extract_doctrina_refs(doc["texto"])

        for codigo, numero, confianza in found_refs:
            conn.execute(
                text(
                    """
                INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                SELECT :doc_id, a.id, 'auto_link', :confianza_enlace, :nota
                FROM articulo a
                JOIN norma n ON n.id = a.norma_id
                WHERE n.codigo = :codigo AND a.numero = :numero
                ON CONFLICT (documento_id, articulo_id)
                DO UPDATE SET
                    metodo_enlace = EXCLUDED.metodo_enlace,
                    confianza_enlace = EXCLUDED.confianza_enlace,
                    nota = EXCLUDED.nota
                WHERE EXCLUDED.confianza_enlace > documento_articulo.confianza_enlace
                """
                ),
                {
                    "doc_id": doc["id"],
                    "codigo": codigo,
                    "numero": numero,
                    "confianza_enlace": confianza,
                    "nota": f"Referencia auto-detectada: {codigo} art. {numero}",
                },
            )
            links_created += 1

    return links_created


def _extract_doctrina_refs(text_value: str) -> set[tuple[str, str, float]]:
    explicit_norma_refs = set()
    source = text_value.upper()

    explicit_patterns = [
        re.compile(r"\b(LIVA|LIRPF|LIS|LGT|ITPAJD|IRNR)\s+(\d+)\b", re.IGNORECASE),
        re.compile(r"\b(LIVA|LIRPF|LIS|LGT|ITPAJD|IRNR)\s+ART\.?\s*(\d+)\b", re.IGNORECASE),
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)\s+DE\s+(?:LA|LAS)\s+(LIVA|LIRPF|LIS|LGT|ITPAJD|IRNR)\b", re.IGNORECASE
        ),
        re.compile(r"ART\.?\s*(\d+)\s+DE\s+(?:LA|LAS)\s+(LIVA|LIRPF|LIS|LGT|ITPAJD|IRNR)\b", re.IGNORECASE),
        re.compile(r"\bART\.?\s+(\d+)\s+(LIVA|LIRPF|LIS|LGT|ITPAJD|IRNR)\b", re.IGNORECASE),
    ]

    for pattern in explicit_patterns:
        for match in pattern.finditer(source):
            first, second = match.groups()
            if first.isdigit():
                numero, codigo = first, second
            else:
                codigo, numero = first, second
            explicit_norma_refs.add((codigo.upper(), numero, 1.00))

    law_patterns = [
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+(\d+/\d{4})\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+(\d+/\d{4})\b",
            re.IGNORECASE,
        ),
    ]

    for pattern in law_patterns:
        for match in pattern.finditer(source):
            numero, ley = match.groups()
            codigo = LAW_TO_NORMA.get(ley)
            if codigo:
                explicit_norma_refs.add((codigo, numero, 1.00))

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
            explicit_norma_refs.add(("LIVA", match.group(1), 1.00))

    # Named law alias: IRNR (non-residents)
    for pattern in [
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+DE\s+(?:LA\s+)?RENTE\s+DE\s+(?:LOS\s+)?NO\s+RESIDENTES\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+DE\s+(?:LA\s+)?RENTE\s+DE\s+(?:LOS\s+)?NO\s+RESIDENTES\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)\s+IRNR\b", re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)\s+IRNR\b", re.IGNORECASE,
        ),
    ]:
        for match in pattern.finditer(source):
            explicit_norma_refs.add(("IRNR", match.group(1), 1.00))

    # Named regulation alias: RIRPF (Reglamento IRPF, RD 439/2007)
    for pattern in [
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DEL\s+REGLAMENTO\s+DEL\s+IRPF\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DEL\s+REGLAMENTO\s+DEL\s+IRPF\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)\s+RIRPF\b", re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)\s+RIRPF\b", re.IGNORECASE,
        ),
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)\s+DEL\s+RD\s+439/2007\b", re.IGNORECASE,
        ),
        re.compile(
            r"ART\.?\s*(\d+)\s+RD\s+439/2007\b", re.IGNORECASE,
        ),
        re.compile(
            r"ART[ÍI]?CULO\s+(\d+)\s+DE\s+L\s*[AÁ]\s*REGLAMENTO\b", re.IGNORECASE,
        ),
    ]:
        for match in pattern.finditer(source):
            explicit_norma_refs.add(("RIRPF", match.group(1), 1.00))

    if explicit_norma_refs:
        return explicit_norma_refs

    # Explicit law name mention (no article attached): e.g. "a efectos de la Ley del IVA"
    # If only one explicit law name is mentioned, resolve standalone article refs to it.
    explicit_law_normas = set()
    if re.search(r"\bLEY\s+DEL\s+IVA\b", source):
        explicit_law_normas.add("LIVA")
    if re.search(r"\bLEY\s+GENERAL\s+TRIBUTARIA\b", source):
        explicit_law_normas.add("LGT")
    if re.search(r"\bNO\s+RESIDENTES\b", source) or re.search(r"\bIRNR\b", source):
        explicit_law_normas.add("IRNR")

    if len(explicit_law_normas) == 1:
        sola_norma = explicit_law_normas.pop()
        article_refs = set()
        for match in re.finditer(r"(?:ART[ÍI]?CULO|ART\.?)\s+(\d+)\b", source):
            article_refs.add((sola_norma, match.group(1), 1.00))
        if article_refs:
            return article_refs

    # Small first contextual heuristic for doctrine without explicit article citation.
    # TEAC resolutions about IVA + base imponible often target LIVA art. 91 in our MVP set.
    if "IVA" in source and "BASE IMPONIBLE" in source:
        return {("LIVA", "91", 0.75)}
    if "IVA" in source and "REGIMEN ESPECIAL" in source:
        return {("LIVA", "91", 0.75)}
    if "IVA" in source and "RECARGO DE EQUIVALENCIA" in source:
        return {("LIVA", "24", 0.75)}

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
    if "NO RESIDENT" in source and "IRNR" not in context_normas:
        context_normas.append("IRNR")
    if "REGLAMENTO" in source and "IRPF" in source and "RIRPF" not in context_normas:
        context_normas.append("RIRPF")

    if len(context_normas) != 1:
        return set()

    contextual_refs = set()
    for match in re.finditer(r"(?:ART[ÍI]?CULO|ART\.?)\s+(\d+)\b", source):
        contextual_refs.add((context_normas[0], match.group(1), 0.85))

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
    now = datetime.now(UTC).isoformat()
    effective_started_at = started_at or now
    duration_ms = max(0, int((datetime.fromisoformat(now) - datetime.fromisoformat(effective_started_at)).total_seconds() * 1000))
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
                error_msg,
                rows_processed,
                errors,
                duration_ms
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
                :error_msg,
                :rows_processed,
                :errors,
                :duration_ms
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
            "rows_processed": max(bloques, articulos, documentos_processed, documentos_upserted, doctrina_links_created),
            "errors": 0 if not error_msg else 1,
            "duration_ms": duration_ms,
        },
    )


def _ensure_schema(conn) -> None:
    """Ensure worker-owned schema objects exist before syncing."""
    dialect = conn.engine.dialect.name

    if dialect == "sqlite":
        norma_columns = conn.execute(text("PRAGMA table_info(norma)")).fetchall()
        norma_column_names = {column[1] for column in norma_columns}
    else:
        norma_column_names = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'norma'
                    """
                )
            ).fetchall()
        }

    added_norma_columns = set()

    if norma_column_names and "tipo_documento" not in norma_column_names:
        conn.execute(text("ALTER TABLE norma ADD COLUMN tipo_documento TEXT"))
        added_norma_columns.add("tipo_documento")
    if norma_column_names and "estado_cobertura" not in norma_column_names:
        conn.execute(text("ALTER TABLE norma ADD COLUMN estado_cobertura TEXT"))
        added_norma_columns.add("estado_cobertura")
    if added_norma_columns:
        conn.execute(
            text(
                """
                UPDATE norma
                SET tipo_documento = 'ley'
                WHERE tipo_documento IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE norma
                SET ambito = 'tributario'
                WHERE ambito = 'fiscal'
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE norma
                SET estado_cobertura = 'ingestada'
                WHERE estado_cobertura IS NULL
                """
            )
        )

    if dialect == "postgresql":
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    _create_base_schema(conn)

    if dialect == "sqlite":
        columns = conn.execute(text("PRAGMA table_info(sync_log)")).fetchall()
        column_names = {column[1] for column in columns}
    else:
        column_names = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'sync_log'
                    """
                )
            ).fetchall()
        }

    if "bloques_processed" not in column_names:
        conn.execute(
            text(
                """
            ALTER TABLE sync_log
            ADD COLUMN bloques_processed INTEGER,
            ADD COLUMN articulos_upserted INTEGER
            """
            )
        )
        conn.execute(
            text(
                """
            UPDATE sync_log
            SET bloques_processed = items_processed,
                articulos_upserted = items_processed
            WHERE bloques_processed IS NULL AND items_processed IS NOT NULL
            """
            )
        )
        column_names |= {"bloques_processed", "articulos_upserted"}

    missing_metric_columns = [
        column
        for column in (
            "documentos_processed",
            "documentos_upserted",
            "doctrina_links_created",
            "rows_processed",
            "errors",
            "duration_ms",
        )
        if column not in column_names
    ]

    for column in missing_metric_columns:
        conn.execute(text(f"ALTER TABLE sync_log ADD COLUMN {column} INTEGER"))

    # Create trigram index for full-text search if it doesn't exist
    if dialect == "postgresql":
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
    else:
        idx_exists = True

    if not idx_exists:
        conn.execute(
            text(
                "CREATE INDEX idx_version_articulo_texto_trgm ON version_articulo USING gin (texto gin_trgm_ops)"
            )
        )


# ---------------------------------------------------------------------------
# BOE consolidated API version monitoring (32.3)
# ---------------------------------------------------------------------------


def _fetch_normas_timestamps(
    client: httpx.Client,
    boe_ids: set[str] | None = None,
) -> dict[str, str]:
    """Fetch fecha_actualizacion for all normas from the BOE consolidated API.

    Returns a dict mapping boe_id -> fecha_actualizacion string.
    If boe_ids is provided, filters to only those IDs.

    Rate limited: sleeps BOE_RATE_LIMIT_SECONDS between requests.
    """
    timestamps: dict[str, str] = {}
    try:
        resp = client.get(
            BOE_API_BASE,
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            logger.warning("BOE API root returned status %d", resp.status_code)
            return timestamps

        data = resp.json()
        normas = data.get("data", [])

        for norma in normas:
            boe_id = norma.get("identificador", "")
            if not boe_id:
                continue
            if boe_ids and boe_id not in boe_ids:
                continue
            fecha = norma.get("fecha_actualizacion", "")
            if fecha:
                timestamps[boe_id] = fecha

    except Exception:
        logger.warning("Failed to fetch normas timestamps from BOE API")

    return timestamps


def _get_stored_timestamps(engine) -> dict[str, str]:
    """Read last known fecha_actualizacion per boe_id from norma.ultima_verificacion.

    Returns dict mapping boe_id -> fecha_actualizacion.
    """
    stored: dict[str, str] = {}
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    "SELECT boe_id, ultima_verificacion FROM norma "
                    "WHERE ultima_verificacion IS NOT NULL"
                )
            )
            for row in result:
                boe_id = row[0]
                fecha = row[1]
                if boe_id and fecha:
                    stored[boe_id] = fecha
    except Exception:
        logger.warning("Failed to read stored timestamps from DB")
    return stored


def _update_stored_timestamps(engine, boe_id: str, fecha: str) -> None:
    """Persist a fecha_actualizacion for a norma in norma.ultima_verificacion."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE norma SET ultima_verificacion = :fecha WHERE boe_id = :boe_id"
                ),
                {"fecha": fecha, "boe_id": boe_id},
            )
    except Exception:
        logger.warning("Failed to update stored timestamp for %s", boe_id)


def _detect_normas_needing_update(
    api_timestamps: dict[str, str],
    stored_timestamps: dict[str, str],
    boe_ids: set[str],
) -> list[str]:
    """Return list of boe_ids whose fecha_actualizacion changed.

    A norma needs updating if:
    - It's in our target set AND
    - Its timestamp in the API differs from stored (or stored is missing).
    """
    needs_update: list[str] = []
    for boe_id in boe_ids:
        api_ts = api_timestamps.get(boe_id, "")
        stored_ts = stored_timestamps.get(boe_id, "")
        if api_ts and api_ts != stored_ts:
            needs_update.append(boe_id)
    return needs_update


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def run_sync(
    codigos: list[str] | None = None,
    worker_name: str = "worker-boe",
) -> dict[str, int]:
    target_codes = codigos or [
        code.strip()
        for code in os.getenv("BOE_LEGISLACION_NORMAS", "LIVA").split(",")
        if code.strip()
    ]
    only_block_ids = [
        item.strip()
        for item in os.getenv("BOE_ONLY_BLOCK_IDS", "").split(",")
        if item.strip()
    ]
    engine = create_engine(DATABASE_URL, future=True)
    bloques_fetched = 0
    articulos_upserted = 0
    norman_actualizadas = 0
    sync_start = datetime.now(UTC).isoformat()

    try:
        with httpx.Client(timeout=30.0) as client, engine.begin() as conn:
            _ensure_schema(conn)
            ensure_source_revision_table(conn)

            # Phase 1: BOE API version monitoring (32.3)
            if BOE_TRACK_VERSIONS:
                boe_ids = {DEFAULT_NORMAS[c] for c in target_codes if c in DEFAULT_NORMAS}
                if boe_ids:
                    try:
                        api_timestamps = _fetch_normas_timestamps(client, boe_ids)
                        stored_timestamps = _get_stored_timestamps(engine)
                        normas_to_update = _detect_normas_needing_update(
                            api_timestamps, stored_timestamps, boe_ids
                        )

                        for boe_id in normas_to_update:
                            # Find the codigo for this boe_id
                            codigo_for_id = None
                            for c, bid in DEFAULT_NORMAS.items():
                                if bid == boe_id:
                                    codigo_for_id = c
                                    break
                            if not codigo_for_id:
                                continue

                            print(f"  [UPDATE] Norma {codigo_for_id} ({boe_id}) has new version")
                            result = _process_norma_from_api(
                                client, conn, codigo_for_id, boe_id, only_block_ids, worker_name
                            )
                            bloques_fetched += result.get("bloques", 0)
                            articulos_upserted += result.get("articulos", 0)
                            # Update stored timestamp
                            api_ts = api_timestamps.get(boe_id, "")
                            if api_ts:
                                _update_stored_timestamps(engine, boe_id, api_ts)
                            norman_actualizadas += 1

                            # Rate limit
                            time.sleep(BOE_RATE_LIMIT_SECONDS)
                    except Exception:
                        logger.warning("Version monitoring failed, continuing with full sync")

            # Phase 2: Full sync for all target normas
            for codigo in target_codes:
                if codigo in MANUAL_NORMAS:
                    upsert_norma(conn, MANUAL_NORMAS[codigo])
                    continue

                boe_id = DEFAULT_NORMAS[codigo]
                metadata = fetch_metadata(client, codigo, boe_id)
                upsert_norma(conn, metadata)
                for item in fetch_index(client, boe_id):
                    if not _is_supported_block(item.titulo):
                        continue
                    if only_block_ids and item.id not in only_block_ids:
                        continue
                    bloque = fetch_block(client, boe_id, item.id)

                    change = check_content_changed(
                        conn, worker_name, "bloque", bloque.bloque_id, bloque.texto
                    )

                    if not change.changed:
                        bloques_fetched += 1
                        continue

                    invalidated = invalidate_old_embeddings(conn, bloque.bloque_id)
                    if invalidated:
                        print(
                            f"  [INVALIDATE] {invalidated} old embeddings for {bloque.bloque_id}"
                        )

                    upsert_articulo(conn, codigo, bloque)
                    record_revision(
                        conn,
                        worker_name,
                        "bloque",
                        bloque.bloque_id,
                        bloque.texto,
                    )
                    bloques_fetched += 1
                    articulos_upserted += 1

                    # Rate limit between blocks
                    time.sleep(BOE_RATE_LIMIT_SECONDS)

            # Auto-linking post-ingestion
            materias_linked = auto_link_materias(conn)
            doctrina_linked = auto_link_doctrina(conn)
            log_sync(
                conn,
                worker_name,
                "ok",
                bloques=bloques_fetched,
                articulos=articulos_upserted,
                started_at=sync_start,
            )
            print(
                f"  Auto-link: materias={materias_linked}, doctrina={doctrina_linked}"
            )
        return {
            "bloques": bloques_fetched,
            "articulos": articulos_upserted,
            "actualizados": norman_actualizadas,
        }
    except Exception as exc:
        with engine.begin() as conn:
            log_sync(
                conn,
                worker_name,
                "error",
                bloques=bloques_fetched,
                articulos=articulos_upserted,
                error_msg=str(exc),
            )
        raise


def _process_norma_from_api(
    client: httpx.Client,
    conn,
    codigo: str,
    boe_id: str,
    only_block_ids: list[str],
    worker_name: str,
) -> dict[str, int]:
    """Process a single norma from the BOE API (used by version monitoring).

    Returns the counts of blocks fetched and articles upserted.
    """
    blocks_fetched = 0
    articulos_upserted = 0

    try:
        metadata = fetch_metadata(client, codigo, boe_id)
        upsert_norma(conn, metadata)
        for item in fetch_index(client, boe_id):
            if not _is_supported_block(item.titulo):
                continue
            if only_block_ids and item.id not in only_block_ids:
                continue
            bloque = fetch_block(client, boe_id, item.id)

            change = check_content_changed(
                conn, worker_name, "bloque", bloque.bloque_id, bloque.texto
            )

            if not change.changed:
                blocks_fetched += 1
                continue

            invalidated = invalidate_old_embeddings(conn, bloque.bloque_id)
            if invalidated:
                print(
                    f"  [INVALIDATE] {invalidated} old embeddings for {bloque.bloque_id}"
                )

            upsert_articulo(conn, codigo, bloque)
            record_revision(
                conn,
                worker_name,
                "bloque",
                bloque.bloque_id,
                bloque.texto,
            )
            blocks_fetched += 1
            articulos_upserted += 1
    except Exception:
        logger.warning("Failed to process norma %s (%s)", codigo, boe_id)

    return {"bloques": blocks_fetched, "articulos": articulos_upserted}


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

    # Sentry error monitoring
    from runtime import init_sentry
    init_sentry("boe")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-boe-daily")
        print(
            f"[run-once] Bloques: {result['bloques']}, Artículos: {result['articulos']}"
        )
    else:
        print(f"Starting BOE worker in continuous mode (interval={interval}s)")
        while True:
            result = run_sync()
            print(
                f"Synced bloques={result['bloques']}, articulos={result['articulos']} at {datetime.now(UTC).isoformat()}"
            )
            time.sleep(interval)
