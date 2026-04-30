"""Worker para EUR-Lex: legislacion de la UE (directivas, reglamentos).

Ingesta normas de EUR-Lex, parsea articulos usando la REST API
de EUR-Lex (consolidated text) y los almacena en las tablas
norma/articulo/version_articulo con tipo_fuente='eurlex'.

Modo hibrido:
  1. CELEXs hardcodeados de EURLEX_NORMAS (seed curado de docs clave).
  2. SPARQL discovery semanal para encontrar nuevas directivas/reglamentos.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from change_detection import (
    check_content_changed,
    destination_row_exists,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)
from runtime import get_database_url, get_interval_seconds

EURLEX_BASE = os.getenv(
    "EURLEX_BASE",
    "https://eur-lex.europa.eu",
)
SPARQL_BASE = os.getenv(
    "SPARQL_BASE",
    "https://data.europa.eu/sparql",
)
DATABASE_URL = get_database_url()
SYNC_INTERVAL_SECONDS = get_interval_seconds("SYNC_INTERVAL_SECONDS", 604800)

# ============================================================
# CELEXs hardcodeados — docs clave de legislacion UE
# ============================================================
# Formato: codigo | boe_id (CELEX) | tipo_documento | titulo | vigente_desde | ambito
# Incluye CELEXs de workers existentes para evitar duplicacion.
EURLEX_NORMAS: list[dict] = [
    # --- MiFID II / MiFIR ---
    {
        "codigo": "MIFID2_2014_65",
        "boe_id": "EUR-CELEX-32014L0065",
        "tipo_documento": "directiva",
        "titulo": "Directiva 2014/65/UE sobre los mercados de instrumentos financieros",
        "vigente_desde": "2014-07-17",
        "ambito": "mercados_financieros",
    },
    {"codigo": "MIFIR_2014_60", "boe_id": "EUR-CELEX-32014R0060", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) n. o 600/2014 sobre los mercados de instrumentos financieros (MiFIR)",
     "vigente_desde": "2014-06-12", "ambito": "mercados_financieros"},
    # --- MAR (Market Abuse Regulation) ---
    {"codigo": "MAR_2014_596", "boe_id": "EUR-CELEX-32014R0596", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) n. o 596/2014 sobre el abuso de mercado (MAR)",
     "vigente_desde": "2014-07-24", "ambito": "abuso_mercado"},
    # --- PRIIPs ---
    {"codigo": "PRIIPs_2014_1286", "boe_id": "EUR-CELEX-32014R1286", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) n. o 1286/2014 sobre los documentos de datos esenciales sobre productos PRIIPs",
     "vigente_desde": "2014-08-01", "ambito": "productos_inversion"},
    # --- DORA (Digital Operational Resilience Act) ---
    {"codigo": "DORA_2022_2535", "boe_id": "EUR-CELEX-32022R2535", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2022/2535 sobre la resiliencia operacional digital (DORA)",
     "vigente_desde": "2022-01-25", "ambito": "resiliencia_digital"},
    # --- CSRD (Corporate Sustainability Reporting Directive) ---
    {"codigo": "CSRD_2022_2467", "boe_id": "EUR-CELEX-32022R2467", "tipo_documento": "directiva",
     "titulo": "Directiva 2022/2464 sobre informacion de sostenibilidad empresarial (CSRD)",
     "vigente_desde": "2022-07-06", "ambito": "sostenibilidad"},
    # --- SFDR (Sustainable Finance Disclosure Regulation) ---
    {"codigo": "SFDR_2019_2088", "boe_id": "EUR-CELEX-32019R2088", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2019/2088 sobre divulgaciones de finanzas sostenibles (SFDR)",
     "vigente_desde": "2019-12-10", "ambito": "sostenibilidad"},
    # --- AIFMD ---
    {"codigo": "AIFMD_2011_61", "boe_id": "EUR-CELEX-32011L0061", "tipo_documento": "directiva",
     "titulo": "Directiva 2011/61/UE sobre gestores de fondos de inversion alternativos (AIFMD)",
     "vigente_desde": "2011-06-08", "ambito": "fondos_inversion"},
    {"codigo": "AIFMD2_2018_1806", "boe_id": "EUR-CELEX-32018R1806", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2018/1806 sobre la transferibilidad de participaciones de AIF",
     "vigente_desde": "2018-11-06", "ambito": "fondos_inversion"},
    # --- UCITS ---
    {"codigo": "UCITS_2009_65", "boe_id": "EUR-CELEX-32009L0065", "tipo_documento": "directiva",
     "titulo": "Directiva 2009/65/CE sobre los fondos de inversion colectivos (UCITS)",
     "vigente_desde": "2009-08-01", "ambito": "fondos_inversion"},
    # --- CRD V / CRR II ---
    {"codigo": "CRD_V_2019_2058", "boe_id": "EUR-CELEX-32019L2058", "tipo_documento": "directiva",
     "titulo": "Directiva (UE) 2019/879 por la que se modifica la Directiva 2013/36/UE (CRD V)",
     "vigente_desde": "2019-12-28", "ambito": "prudencial_bancario"},
    {"codigo": "CRR_II_2019_2057", "boe_id": "EUR-CELEX-32019R2057", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2019/2057 por el que se modifica el Reglamento (UE) n. o 575/2013 (CRR II)",
     "vigente_desde": "2019-12-28", "ambito": "prudencial_bancario"},
    # --- BRRD ---
    {"codigo": "BRRD_2014_59", "boe_id": "EUR-CELEX-32014L0059", "tipo_documento": "directiva",
     "titulo": "Directiva 2014/59/UE sobre el régimen de recuperación y resolución de entidades de credito",
     "vigente_desde": "2014-06-16", "ambito": "resolucion_bancaria"},
    # --- EMIR ---
    {"codigo": "EMIR_2012_648", "boe_id": "EUR-CELEX-32012R0648", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) n. o 648/2012 sobre los contratos derivados de tipo de cambio y opciones (EMIR)",
     "vigente_desde": "2012-07-16", "ambito": "derivados"},
    # --- PSD2 / PSD3 ---
    {"codigo": "PSD2_2015_236", "boe_id": "EUR-CELEX-32015L0236", "tipo_documento": "directiva",
     "titulo": "Directiva (UE) 2015/2366 sobre los servicios de pago en el mercado interior (PSD2)",
     "vigente_desde": "2015-12-22", "ambito": "servicios_pago"},
    {"codigo": "PSD3_2024_884", "boe_id": "EUR-CELEX-32024R0884", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2024/884 sobre los servicios de pago en el mercado interior (PSD3)",
     "vigente_desde": "2024-03-20", "ambito": "servicios_pago"},
    # --- IDD (Insurance Distribution Directive) ---
    {"codigo": "IDD_2016_97", "boe_id": "EUR-CELEX-32016L0097", "tipo_documento": "directiva",
     "titulo": "Directiva 2016/97/UE sobre la distribucion de seguros (IDD)",
     "vigente_desde": "2016-02-04", "ambito": "distribucion_seguros"},
    # --- Consumer Credit ---
    {"codigo": "CONSUMER_CREDIT_2008_48", "boe_id": "EUR-CELEX-32008L0048", "tipo_documento": "directiva",
     "titulo": "Directiva 2008/48/CE sobre los contratos de credito a los consumidores",
     "vigente_desde": "2008-05-21", "ambito": "credito_consumidor"},
    # --- Solvency II ---
    {"codigo": "SOLVENCY_II_2009_110", "boe_id": "EUR-CELEX-32009L0110", "tipo_documento": "directiva",
     "titulo": "Directiva 2009/138/CE sobre el acceso y ejercicio de la actividad de seguros y reaseguros (Solvency II)",
     "vigente_desde": "2009-11-25", "ambito": "seguros"},
    # --- AMLD ---
    {"codigo": "AMLD_2018_843", "boe_id": "EUR-CELEX-32018L0843", "tipo_documento": "directiva",
     "titulo": "Directiva (UE) 2018/843 sobre prevencion del blanqueo de capitales (AMLD5)",
     "vigente_desde": "2018-06-28", "ambito": "prevencion_blanqueo"},
    # --- DAC ---
    {"codigo": "DAC6_2018_825", "boe_id": "EUR-CELEX-32018L0825", "tipo_documento": "directiva",
     "titulo": "Directiva (UE) 2018/822 sobre la divulgacion obligatoria de informes relativos a disposiciones transfronterizas (DAC6)",
     "vigente_desde": "2018-06-25", "ambito": "transparencia_fiscal"},
    {"codigo": "DAC7_2021_1689", "boe_id": "EUR-CELEX-32021R1689", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2021/1689 sobre los requisitos fiscales de aplicacion a los servicios de la sociedad de la informacion (DAC7)",
     "vigente_desde": "2021-10-20", "ambito": "transparencia_fiscal"},
    # --- Prospectus Regulation ---
    {"codigo": "PROSPECTUS_2017_1129", "boe_id": "EUR-CELEX-32017R1129", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2017/1129 sobre el prospecto de informacion de valores",
     "vigente_desde": "2017-06-07", "ambito": "valores"},
    # --- CSDR ---
    {"codigo": "CSDR_2014_909", "boe_id": "EUR-CELEX-32014R0909", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) n. o 909/2014 sobre las depositarias centrales de valores (CSDR)",
     "vigente_desde": "2014-09-12", "ambito": "infraestructura_mercados"},
    # --- Alternative Performance Measures ---
    {"codigo": "APM_2020_683", "boe_id": "EUR-CELEX-32020R683", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2020/683 sobre las metrics financieras alternativas (APM)",
     "vigente_desde": "2020-07-03", "ambito": "informacion_financiera"},
    # --- ESG Ratings ---
    {"codigo": "ESG_RATINGS_2023_2819", "boe_id": "EUR-CELEX-32023R2819", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2023/2819 sobre los agentes de calificacion de datos de sostenibilidad (ESG Ratings)",
     "vigente_desde": "2023-12-20", "ambito": "sostenibilidad"},
    # --- Trade Repository ---
    {"codigo": "TRADE_REPOSITORY_2024_1781", "boe_id": "EUR-CELEX-32024R1781", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2024/1781 sobre los registros centrales de operaciones (Trade Repository)",
     "vigente_desde": "2024-07-11", "ambito": "derivados"},
    # --- Corporate Sustainability Due Diligence (CSDDD) ---
    {"codigo": "CSDDD_2024_1760", "boe_id": "EUR-CELEX-32024L1760", "tipo_documento": "directiva",
     "titulo": "Directiva (UE) 2024/1760 sobre la debida diligencia en materia de sostenibilidad de las empresas",
     "vigente_desde": "2024-07-25", "ambito": "sostenibilidad"},
    # --- AI Act ---
    {"codigo": "AI_ACT_2024_1689", "boe_id": "EUR-CELEX-32024R1689", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2024/1689 por el que se establecen normas armonizadas sobre la inteligencia artificial (AI Act)",
     "vigente_desde": "2024-07-12", "ambito": "tecnologia"},
    # --- Data Act ---
    {"codigo": "DATA_ACT_2023_2854", "boe_id": "EUR-CELEX-32023R2854", "tipo_documento": "reglamento",
     "titulo": "Reglamento (UE) 2023/2854 sobre la comparticion de datos y la utilizacion de datos (Data Act)",
     "vigente_desde": "2023-12-11", "ambito": "tecnologia"},
]

# ============================================================
# Data classes
# ============================================================

@dataclass
class BloqueTexto:
    bloque_id: str
    tipo_bloque: str
    numero: str
    titulo: str
    tipo_articulo: str
    texto: str
    vigente_desde: str


@dataclass
class NormaCELEX:
    """Parsed CELEX from SPARQL or search results."""
    celex: str
    titulo: str
    fecha: str
    tipo: str  # "DIRECTIVE" or "REGULATION"


# ============================================================
# Helpers
# ============================================================

def _infer_tipo_y_numero(titulo: str) -> tuple[str, str]:
    """Extract tipo_articulo and numero from EUR-Lex block title."""
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
    """Check if block type should be ingested."""
    prefixes = (
        "Artículo ", "Articulo ",
        "Disposición adicional ", "Disposición transitoria ",
        "Disposición final ", "Disposición derogatoria ",
        "Sección ", "Capítulo ",
    )
    return titulo.startswith(prefixes)


def _yyyymmdd_to_iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


# ============================================================
# EUR-Lex REST API
# ============================================================

def parse_index(payload: dict) -> list[dict]:
    """Parse EUR-Lex index JSON into block metadata list."""
    data = payload.get("data", [])
    if not data:
        return []
    blocks = data[0].get("bloque", [])
    return [
        {
            "id": item["id"],
            "titulo": item.get("titulo", "").strip(),
            "fecha_actualizacion": item.get("fecha_actualizacion", ""),
        }
        for item in blocks
        if item.get("titulo")
    ]


def fetch_index(client: httpx.Client, celex: str) -> list[dict]:
    """Fetch index from EUR-Lex consolidated text API.

    Falls back to HTML scraping when the REST API returns no index data.
    EUR-Lex blocks automated requests (requires JS), so we also check for
    a local corpus file before giving up.
    """
    # Try the REST API first
    try:
        response = client.get(
            f"{EURLEX_BASE}/rest.tx.legal-acts-index/{celex}",
            headers={"Accept": "application/json"},
        )
        if response.status_code == 200:
            parsed = parse_index(response.json())
            if parsed:
                return parsed
    except (httpx.HTTPStatusError, httpx.RequestError):
        pass

    # Fallback: check for local corpus file
    corpus_path = Path(f"corpora/eurlex/{celex}.txt")
    if corpus_path.exists():
        try:
            text = corpus_path.read_text(encoding="utf-8")
            return [
                {
                    "id": "corpus",
                    "titulo": "Texto completo (corpus local)",
                    "fecha_actualizacion": "",
                }
            ]
        except Exception:
            pass

    # Fallback: scrape the consolidated HTML page for article list
    return _fetch_index_html_fallback(client, celex)


def fetch_block_from_corpus(celex: str) -> BloqueTexto | None:
    """Load a block from the local corpus file when the live API is unavailable."""
    corpus_path = Path(f"corpora/eurlex/{celex}.txt")
    if not corpus_path.exists():
        return None
    try:
        text = corpus_path.read_text(encoding="utf-8")
        return BloqueTexto(
            bloque_id="corpus",
            tipo_bloque="completo",
            numero="1",
            titulo="Texto completo",
            tipo_articulo="completo",
            texto=text,
            vigente_desde="",
        )
    except Exception:
        return None


def _fetch_index_html_fallback(client: httpx.Client, celex: str) -> list[dict]:
    """Scrape EUR-Lex HTML page to build a block index when REST API fails.

    EUR-Lex requires JavaScript, so this often returns empty. The corpus
    fallback in fetch_index() is preferred.
    """
    url = f"{EURLEX_BASE}/legal-content/ES/TXT/?uri=CELEX:{celex}"
    try:
        response = client.get(url, headers={"Accept": "text/html"}, timeout=30.0)
        if response.status_code != 200:
            return []
        from xml.etree import ElementTree as ET

        html_text = response.text
        root = ET.fromstring(html_text)  # noqa: S314

        blocks = []
        for h_elem in root.iter():
            tag = h_elem.tag
            text = (h_elem.text or "").strip()
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                if text and ("articulo" in text.lower() or "disposición" in text.lower() or "sección" in text.lower() or "capítulo" in text.lower()):
                    blocks.append({
                        "id": f"html-{len(blocks)}",
                        "titulo": text,
                        "fecha_actualizacion": "",
                    })
            cls = h_elem.attrib.get("class", "")
            if cls and ("articulo" in cls.lower() or "disposition" in cls.lower()):
                text = (h_elem.text or "").strip()
                if text:
                    blocks.append({
                        "id": f"html-{len(blocks)}",
                        "titulo": text,
                        "fecha_actualizacion": "",
                    })
        return blocks
    except Exception as exc:
        print(f"  [WARN] HTML fallback failed for {celex}: {exc}")
        return []


def fetch_block(client: httpx.Client, block_id: str) -> BloqueTexto:
    """Fetch a single block from EUR-Lex."""
    response = client.get(
        f"{EURLEX_BASE}/rest.tx.legal-acts-index/{block_id}",
        headers={"Accept": "application/xml"},
    )
    response.raise_for_status()
    return _parse_block_xml(block_id, response.text)


def _parse_block_xml(block_id: str, xml_text: str) -> BloqueTexto:
    from xml.etree import ElementTree as ET

    root = ET.fromstring(xml_text)  # noqa: S314
    bloque = root.find(".//bloque")
    version = root.find(".//version")
    if bloque is None or version is None:
        raise ValueError(f"Invalid EUR-Lex block payload for {block_id}")

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


# ============================================================
# SPARQL discovery
# ============================================================

def _sparql_directives(cutoff: str) -> list[str]:
    """Query SPARQL for recent EU directives. Returns list of CELEX strings."""
    query = f"""
    PREFIX cdm: <http://data.europa.eu/eli/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    SELECT ?celex ?date
    WHERE {{
      ?work a cdm:Work .
      ?work rdf:type <http://publications.europa.eu/resource/authority/resource-type/DIRECTIVE> .
      ?work <http://publications.europa.eu/ontology/ecli#hasCELEX> ?celex .
      ?work <http://purl.org/dc/terms/issued> ?date .
      FILTER(?date > "{cutoff}"^^xsd:date)
    }}
    ORDER BY DESC(?date)
    LIMIT 200
    """
    return _run_sparql(query)


def _sparql_regulations(cutoff: str) -> list[str]:
    """Query SPARQL for recent EU regulations. Returns list of CELEX strings."""
    query = f"""
    PREFIX cdm: <http://data.europa.eu/eli/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?celex ?date
    WHERE {{
      ?work a cdm:Work .
      ?work rdf:type <http://publications.europa.eu/resource/authority/resource-type/REGULATION> .
      ?work <http://publications.europa.eu/ontology/ecli#hasCELEX> ?celex .
      ?work <http://purl.org/dc/terms/issued> ?date .
      FILTER(?date > "{cutoff}"^^xsd:date)
    }}
    ORDER BY DESC(?date)
    LIMIT 200
    """
    return _run_sparql(query)


def _run_sparql(query: str) -> list[str]:
    """Execute a SPARQL query and return list of CELEX strings."""
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                SPARQL_BASE,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
            )
            response.raise_for_status()
            results = response.json()
            bindings = results.get("results", {}).get("bindings", [])
            celexes = []
            for binding in bindings:
                celex_val = binding.get("celex", {}).get("value", "")
                if celex_val and celex_val.startswith("3"):
                    celexes.append(celex_val)
            return celexes
    except Exception as exc:
        print(f"  [WARN] SPARQL query failed: {exc}")
        return []


def discover_new_celexs(
    client: httpx.Client,
    existing_celexs: set[str],
) -> list[str]:
    """Discover new EU directives/regulations via SPARQL not yet in DB.

    Returns list of new CELEX strings (without EUR-CELEX- prefix).
    """
    cutoff = (datetime.now(UTC) - timedelta(days=180)).strftime("%Y-%m-%d")
    print(f"  [SPARQL] Querying directives from {cutoff}...")
    time.sleep(10)  # Rate limit SPARQL
    directive_celexs = _sparql_directives(cutoff)

    print(f"  [SPARQL] Querying regulations from {cutoff}...")
    time.sleep(10)  # Rate limit SPARQL
    regulation_celexs = _sparql_regulations(cutoff)

    all_celexs = set(directive_celexs + regulation_celexs)
    new_celexs = sorted(all_celexs - existing_celexs)
    print(f"  [SPARQL] Found {len(all_celexs)} total, {len(new_celexs)} new since {cutoff}")
    return new_celexs


# ============================================================
# DB helpers — upsert norma/articulo/version_articulo
# ============================================================

def upsert_norma(conn, norma: dict, vigente_desde: str) -> None:
    """Upsert a norma record."""
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
        {
            "codigo": norma["codigo"],
            "titulo": norma["titulo"],
            "boe_id": norma["boe_id"],
            "eli_uri": f"https://eur-lex.europa.eu/eli/{_eli_path(norma['boe_id'])}",
            "jurisdiccion": "ue",
            "tipo_fuente": "eurlex",
            "tipo_documento": norma["tipo_documento"],
            "ambito": norma["ambito"],
            "estado_cobertura": "ingestada",
            "vigente_desde": vigente_desde,
        },
    )


def _eli_path(boe_id: str) -> str:
    """Convert EUR-CELEX-32014L0065 -> reg/2014/65/oj or dir/2014/65/oj.

    CELEX format: 3[YYYY][TRL][NNNN]
    - 3 = EU prefix
    - YYYY = year
    - T = type (R=regulation, L=directive, D=decision)
    - NNNN = number (may have leading zeros)
    """
    if not boe_id.startswith("EUR-CELEX-"):
        return "unknown/oj"
    celex = boe_id.replace("EUR-CELEX-", "")
    # CELEX: 32014R0909 -> year=2014 (chars 1-5), type=R (char 5), num=0909 (chars 6+)
    year = celex[1:5]
    type_char = celex[5]
    num = celex[6:].lstrip("0") or "0"
    if type_char == "L":
        prefix = "dir"
    elif type_char == "R":
        prefix = "reg"
    elif type_char == "D":
        prefix = "dec"
    else:
        prefix = "dec"
    return f"{prefix}/{year}/{num}/oj"


def upsert_articulo(conn, codigo: str, bloque: BloqueTexto) -> None:
    """Upsert articulo + version_articulo for a EUR-Lex block."""
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


# ============================================================
# Sync log
# ============================================================

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
    duration_ms = max(
        0,
        int(
            (datetime.fromisoformat(now) - datetime.fromisoformat(effective_started_at)).total_seconds() * 1000
        ),
    )
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


# ============================================================
# Main sync
# ============================================================

def run_sync(  # noqa: C901
    worker_name: str = "worker-eurlex",
) -> dict[str, int]:
    """Run a full sync cycle: seed CELEXs + SPARQL discovery."""
    engine = create_engine(DATABASE_URL, future=True)
    bloques_fetched = 0
    articulos_upserted = 0
    normas_upserted = 0
    nuevos_sparql = 0
    sync_start = datetime.now(UTC).isoformat()

    try:
        with httpx.Client(timeout=30.0) as client, engine.begin() as conn:
            _ensure_sync_log_table(conn)
            ensure_source_revision_table(conn)

            # Phase 1: Process hardcoded CELEXs
            for norma_def in EURLEX_NORMAS:
                celex = norma_def["boe_id"].replace("EUR-CELEX-", "")
                vigente_desde = norma_def["vigente_desde"]
                upsert_norma(conn, norma_def, vigente_desde)
                normas_upserted += 1

                index = fetch_index(client, celex)
                if not index:
                    print(f"  [SKIP] {celex} has no index")
                    continue

                for item in index:
                    if not _is_supported_block(item["titulo"]):
                        bloques_fetched += 1
                        continue

                    # Try live API first, fall back to corpus
                    try:
                        bloque = fetch_block(client, item["id"])
                    except Exception:  # noqa: S112
                        bloque = fetch_block_from_corpus(celex)
                        if not bloque:
                            continue

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

                    upsert_articulo(conn, norma_def["codigo"], bloque)
                    record_revision(
                        conn, worker_name, "bloque", bloque.bloque_id, bloque.texto
                    )
                    bloques_fetched += 1
                    articulos_upserted += 1

                    time.sleep(1)  # Rate limit EUR-Lex REST

            # Phase 2: SPARQL discovery for new CELEXs
            existing_celexs = set()
            for n in EURLEX_NORMAS:
                existing_celexs.add(n["boe_id"].replace("EUR-CELEX-", ""))
            # Also check what's already in DB
            rows = conn.execute(
                text("SELECT boe_id FROM norma WHERE tipo_fuente = 'eurlex' AND boe_id IS NOT NULL")
            ).fetchall()
            for row in rows:
                bid = row[0] or ""
                if bid.startswith("EUR-CELEX-"):
                    existing_celexs.add(bid.replace("EUR-CELEX-", ""))

            new_celexs = discover_new_celexs(client, existing_celexs)
            for celex in new_celexs:
                nuevos_sparql += 1
                # Use EUR-Lex search to get metadata
                try:
                    search_url = (
                        f"{EURLEX_BASE}/search?q=celex:{celex}&scope=EUROLX&type=html&lang=en"
                    )
                    resp = client.get(search_url, follow_redirects=True)
                    if resp.status_code == 200:
                        # Extract CELEX from result page
                        titulo = f"EUR-Lex document {celex}"
                        tipo = "reglamento" if "REGULATION" in celex.upper() or celex[4] == "R" else "directiva"
                        # Extract year from CELEX
                        year = celex[:4]
                        vigente_desde = f"{year}-01-01"

                        upsert_norma(
                            conn,
                            {
                                "codigo": f"EURLEX-{celex}",
                                "boe_id": f"EUR-CELEX-{celex}",
                                "tipo_documento": tipo,
                                "titulo": titulo,
                                "vigente_desde": vigente_desde,
                                "ambito": "ue_general",
                            },
                            vigente_desde,
                        )
                        normas_upserted += 1

                        index = fetch_index(client, celex)
                        if index:
                            for item in index:
                                if not _is_supported_block(item["titulo"]):
                                    bloques_fetched += 1
                                    continue
                                try:
                                    bloque = fetch_block(client, item["id"])
                                except Exception:  # noqa: S112
                                    bloque = fetch_block_from_corpus(celex)
                                    if not bloque:
                                        continue
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
                                    print(f"  [INVALIDATE] {invalidated} old embeddings for {bloque.bloque_id}")
                                upsert_articulo(conn, f"EURLEX-{celex}", bloque)
                                record_revision(conn, worker_name, "bloque", bloque.bloque_id, bloque.texto)
                                bloques_fetched += 1
                                articulos_upserted += 1
                                time.sleep(1)
                except Exception:
                    print(f"  [SKIP] Could not process new CELEX {celex}")

            log_sync(
                conn,
                worker_name,
                "ok",
                bloques=bloques_fetched,
                articulos=articulos_upserted,
                started_at=sync_start,
            )
        return {
            "bloques": bloques_fetched,
            "articulos": articulos_upserted,
            "normas": normas_upserted,
            "nuevos_sparql": nuevos_sparql,
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
                started_at=sync_start,
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EUR-Lex worker: sync EU legislation (directives, regulations)"
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
    init_sentry("eurlex")

    interval = args.interval if args.interval is not None else SYNC_INTERVAL_SECONDS

    if args.run_once:
        result = run_sync(worker_name="cron-eurlex-weekly")
        print(
            f"[run-once] Bloques: {result['bloques']}, Articulos: {result['articulos']}, "
            f"Normas: {result['normas']}, Nuevos SPARQL: {result['nuevos_sparql']}"
        )
    else:
        print(f"Starting EUR-Lex worker in continuous mode (interval={interval}s)")
        while True:
            Path("/tmp/worker_heartbeat").touch()
            try:
                result = run_sync()
                print(
                    f"Synced bloques={result['bloques']}, articulos={result['articulos']}, "
                    f"normas={result['normas']}, nuevos_sparql={result['nuevos_sparql']} "
                    f"at {datetime.now(UTC).isoformat()}"
                )
            except Exception as exc:
                print(f"[ERROR] EUR-Lex sync failed: {exc} at {datetime.now(UTC).isoformat()}")
            time.sleep(interval)
