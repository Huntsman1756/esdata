#!/usr/bin/env python
"""Seed de documentos AEPD desde su portal web.

Descubre y almacena guías PDF, resoluciones, informes jurídicos, instrucciones
y circulares de la Agencia Espanola de Proteccion de Datos.

Uso:
    python scripts/data/seed_aepd.py
"""

import argparse
import re
import time
from datetime import datetime, timezone
from html import unescape

import psycopg
import requests
from pypdf import PdfReader
from io import BytesIO

DB_URL_DEFAULT = "postgresql://esdata:esdata_dev@localhost:5434/esdata"
AEPD_BASE = "https://www.aepd.es"
DELAY = 2.0


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    chunks = []
    for page in reader.pages:
        text_value = page.extract_text() or ""
        cleaned = _normalize_ws(text_value)
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def extract_html_text(content: bytes) -> str:
    html = content.decode("utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "\n", html)
    text_value = re.sub(r"\n\s*\n", "\n", html)
    return _normalize_ws(unescape(text_value))


def detect_type(url: str, text: str) -> str:
    lowered = url.lower()
    text_lower = text.lower()
    if "instruccion" in lowered or "instrucción" in text_lower:
        return "instruccion_aepd"
    if "circular" in lowered:
        return "circular_aepd"
    if "reposicion" in lowered or "resolucion" in text_lower:
        return "resolucion_aepd"
    if "informe" in lowered or "informe juridico" in text_lower:
        return "informe_juridico_aepd"
    if "guia" in lowered or text_lower.startswith("guía") or text_lower.startswith("guia"):
        return "guia_aepd"
    if "nota tecnica" in lowered or "nota técnica" in text_lower:
        return "nota_tecnica_aepd"
    if "orientacion" in lowered or "orientación" in text_lower:
        return "orientacion_aepd"
    if "recomendacion" in lowered or "recomendación" in text_lower:
        return "recomendacion_aepd"
    if "estudio" in lowered:
        return "estudio_aepd"
    if "decalogo" in lowered or "decálogo" in text_lower:
        return "decalogo_aepd"
    if "faq" in lowered:
        return "faq_aepd"
    if "tech-dispatch" in lowered:
        return "tech_dispatch_aepd"
    return "documento_aepd"


def detect_ambito(text: str, url: str) -> str:
    lowered = text.lower()
    url_lower = url.lower()
    if "cookie" in lowered:
        return "cookies"
    if "videovigilancia" in lowered or "camara" in lowered:
        return "videovigilancia"
    if "sanidad" in lowered or "paciente" in lowered or "salud" in lowered:
        return "salud"
    if "menor" in lowered:
        return "menores"
    if "biometria" in lowered:
        return "biometria"
    if "ia" in lowered or "inteligencia artificial" in lowered or "machine learning" in lowered or "fingerprinting" in lowered:
        return "ia_y_tecnologias"
    if "drone" in lowered:
        return "drones"
    if "laboral" in lowered:
        return "relaciones_laborales"
    if "educativo" in lowered or "centro educativo" in lowered:
        return "educacion"
    if "blockchain" in lowered:
        return "blockchain"
    if "anonimizacion" in lowered or "anonimización" in lowered:
        return "anonimizacion"
    if "brecha" in lowered:
        return "brechas_seguridad"
    if "pyme" in lowered or "autonomo" in lowered or "autónomo" in lowered:
        return "pymes"
    if "administracion" in lowered or "aapp" in lowered:
        return "administraciones_publicas"
    if "local" in lowered:
        return "administracion_local"
    if "ficha" in lowered or "prevencion" in lowered:
        return "prevencion_delitos"
    if "schrems" in lowered:
        return "transferencias_internacionales"
    if "verificacion edad" in lowered or "edad menores" in lowered:
        return "verificacion_edad"
    if "criptografia" in lowered:
        return "criptografia"
    if "wifi" in lowered or "tracking" in lowered:
        return "wifi_tracking"
    if "5g" in lowered:
        return "telecomunicaciones"
    if "dns" in lowered:
        return "dns_privacidad"
    if "teletrabajo" in lowered:
        return "teletrabajo"
    if "android" in lowered or "apps moviles" in lowered or "apps móviles" in lowered:
        return "apps_moviles"
    if "neurodatos" in lowered:
        return "neurodatos"
    if "generacion datos sinteticos" in lowered:
        return "datos_sinteticos"
    if "aprendizaje federado" in lowered:
        return "aprendizaje_federado"
    if "patron adictivo" in lowered:
        return "patrones_adictivos"
    if "fichero" in lowered or "ficheros" in lowered:
        return "ficheros_datos"
    if "derecho acceso" in lowered:
        return "derechos_arCO"
    return "proteccion_datos_general"


def extract_reference(url: str) -> str:
    m = re.search(r"/documento/([^/]+)\.pdf", url)
    if m:
        return f"AEPD-{m.group(1)}"
    m = re.search(r"/guias/([^/]+)\.pdf", url)
    if m:
        return f"AEPD-GUIA-{m.group(1)}"
    m = re.search(r"(\d{4}-\d{4})\.pdf", url)
    if m:
        return f"AEPD-INFO-{m.group(1)}"
    return f"AEPD-{datetime.now(timezone.utc).strftime('%Y%m%d')}"


def build_payload(url: str, content: bytes) -> dict:
    if content[:5] == b"%PDF-":
        text = extract_pdf_text(content)
    else:
        text = extract_html_text(content)

    if not text:
        raise ValueError(f"No text extracted from AEPD document: {url}")

    ref = extract_reference(url)
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")

    return {
        "referencia": ref,
        "fecha": datetime.now(timezone.utc).date().isoformat(),
        "titulo": first_line[:200] if first_line else ref,
        "texto": text,
        "url_fuente": url,
        "tipo_documento": detect_type(url, text),
        "tipo_fuente": "aepd",
        "organismo_emisor": "AEPD",
        "ambito": detect_ambito(text, url),
        "jurisdiccion": "es",
    }


def upsert_documento(conn, payload: dict) -> None:
    conn.execute(
        psycopg.sql.SQL(
            """
            INSERT INTO documento_interpretativo (
                tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                ambito, referencia, fecha, titulo, texto, url_fuente
            ) VALUES (
                %(tipo_documento)s, 'AEPD', 'es', 'aepd',
                %(ambito)s, %(referencia)s, %(fecha)s, %(titulo)s, %(texto)s, %(url_fuente)s
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = excluded.tipo_documento,
                ambito = excluded.ambito,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        payload,
    )


def fetch_pdf(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code == 200 and resp.content[:5] == b"%PDF-":
            return resp.content
    except Exception:
        pass
    return None


def fetch_html(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


def seed_pdf_guides(conn) -> int:
    """Seed guías PDF desde /guias/ path."""
    pdf_guides = [
        "https://www.aepd.es/guias/guia-rgpd-para-responsables-de-tratamiento.pdf",
        "https://www.aepd.es/guias/guia-videovigilancia.pdf",
        "https://www.aepd.es/guias/guia-cookies.pdf",
        "https://www.aepd.es/guias/guia-centros-educativos.pdf",
        "https://www.aepd.es/guias/guia-ciudadano.pdf",
        "https://www.aepd.es/guias/guia-proteccion-datos-por-defecto.pdf",
        "https://www.aepd.es/guias/guia-proteccion-datos-administracion-local.pdf",
        "https://www.aepd.es/guias/guia-pacientes-usuarios-sanidad.pdf",
        "https://www.aepd.es/guias/guia-profesionales-sector-sanitario.pdf",
        "https://www.aepd.es/guias/guia-brechas-seguridad.pdf",
        "https://www.aepd.es/guias/guia-drones.pdf",
        "https://www.aepd.es/guias/guia-control-presencia-biometrico.pdf",
        "https://www.aepd.es/guias/guia-privacidad-desde-diseno.pdf",
        "https://www.aepd.es/guias/guia-privacidad-y-seguridad-en-internet.pdf",
        "https://www.aepd.es/guias/guia-administradores-fincas.pdf",
        "https://www.aepd.es/guias/guia-compra-segura-digital-web.pdf",
        "https://www.aepd.es/guias/guia-directrices-contratos.pdf",
        "https://www.aepd.es/guias/guia-modelo-clausula-informativa.pdf",
        "https://www.aepd.es/guias/guia-listado-de-cumplimiento-del-rgpd.pdf",
        "https://www.aepd.es/guias/guia-tecnologias-admin-digital.pdf",
        "https://www.aepd.es/guias/guia-cifrado-autonomos-pymes.pdf",
        "https://www.aepd.es/guias/guia-aepd-uso-de-imagenes-de-terceros-en-sistemas-ia.pdf",
        "https://www.aepd.es/guias/10-malentendidos-anonimizacion.pdf",
        "https://www.aepd.es/guias/10-malentendidos-machinelearning.pdf",
        "https://www.aepd.es/guias/adecuacion-rgpd-ia.pdf",
        "https://www.aepd.es/guias/orientaciones-ia-agentica.pdf",
        "https://www.aepd.es/guias/recomendaciones-ia-aepd.pdf",
        "https://www.aepd.es/guias/guia-sobre-generacion-datos-sinteticos.pdf",
        "https://www.aepd.es/guias/guia-orientaciones-procedimientos-anonimizacion.pdf",
        "https://www.aepd.es/guias/gestion-riesgo-y-evaluacion-impacto-en-tratamientos-datos-personales.pdf",
        "https://www.aepd.es/guias/orientaciones-criptografia-aepd-isms-apep.pdf",
        "https://www.aepd.es/guias/nota-tecnica-blockchain.pdf",
        "https://www.aepd.es/guias/anexo-tecnico-blockchain.pdf",
        "https://www.aepd.es/guias/faqs-sentencia-schrems-ii-es.pdf",
        "https://www.aepd.es/guias/decalogo-principios-verificacion-edad-proteccion-menores.pdf",
        "https://www.aepd.es/guias/orientaciones-analitica-web-aapp.pdf",
        "https://www.aepd.es/guias/orientaciones-riesgo-brechas-masivas-aapp.pdf",
        "https://www.aepd.es/guias/requisitos-auditorias-tratamientos-incluyan-ia.pdf",
        "https://www.aepd.es/guias/recomendaciones-apps-espacios-publicos.pdf",
        "https://www.aepd.es/guias/nota-equivocos-biometria.pdf",
        "https://www.aepd.es/guias/estrategia-menores-aepd-lineas-accion.pdf",
        "https://www.aepd.es/guias/nota-tecnica-privacidad-5g.pdf",
        "https://www.aepd.es/guias/nota-tecnica-proteger-datos-teletrabajo.pdf",
        "https://www.aepd.es/guias/nota-tecnica-apps-moviles.pdf",
        "https://www.aepd.es/guias/neurodatos-aepd-edps.pdf",
        "https://www.aepd.es/guias/tech-dispatch-aprendizaje-federado.pdf",
        "https://www.aepd.es/guias/patrones-adictivos-en-tratamiento-de-datos-personales.pdf",
        "https://www.aepd.es/guias/la-proteccion-de-datos-en-las-relaciones-laborales.pdf",
        "https://www.aepd.es/guias/guia-cookies-analiticas-externas.pdf",
        "https://www.aepd.es/guias/estudio-fingerprinting-huella-digital.pdf",
        "https://www.aepd.es/guias/orientaciones-wifi-tracking-seguimiento.pdf",
        "https://www.aepd.es/guias/nota-tecnica-privacidad-dns.pdf",
    ]

    stored = 0
    for url in pdf_guides:
        content = fetch_pdf(url)
        if not content:
            print(f"  [SKIP] Could not fetch PDF: {url}")
            continue
        try:
            payload = build_payload(url, content)
            upsert_documento(conn, payload)
            stored += 1
            print(f"  [OK] {payload['referencia']} ({payload['tipo_documento']})")
        except Exception as e:
            print(f"  [FAIL] {url}: {e}")
        time.sleep(DELAY)

    return stored


def seed_resolutions(conn) -> int:
    """Seed resoluciones, informes juridicos e instrucciones."""
    resolution_urls = [
        "https://www.aepd.es/documento/pd-00059-2026.pdf",
        "https://www.aepd.es/documento/pd-00024-2026.pdf",
        "https://www.aepd.es/documento/reposicion-pd-00238-2025.pdf",
        "https://www.aepd.es/documento/reposicion-ps-00016-2025.pdf",
        "https://www.aepd.es/documento/reposicion-ps-00097-2025.pdf",
        "https://www.aepd.es/documento/reposicion-ps-00328-2024.pdf",
        "https://www.aepd.es/documento/reposicion-ps-00410-2024.pdf",
        "https://www.aepd.es/documento/reposicion-ps-00551-2024.pdf",
        "https://www.aepd.es/documento/reposicion-ai-00346-2024.pdf",
        "https://www.aepd.es/documento/reposicion-pa-00034-2024.pdf",
        "https://www.aepd.es//documento/2022-0085.pdf",
        "https://www.aepd.es//documento/2022-0084.pdf",
        "https://www.aepd.es//documento/2022-0083.pdf",
        "https://www.aepd.es//documento/2022-0082.pdf",
        "https://www.aepd.es//documento/2022-0081.pdf",
        "https://www.aepd.es//documento/2022-0080.pdf",
        "https://www.aepd.es//documento/2022-0078.pdf",
        "https://www.aepd.es//documento/2022-0077.pdf",
        "https://www.aepd.es//documento/2022-0076.pdf",
        "https://www.aepd.es//documento/2022-0075.pdf",
        "https://www.aepd.es/documento/main-circular-01-2019.pdf",
        "https://www.aepd.es/es/documento/instruccion-aepd-gestion-aplazamientos-fraccionamientos-pago.pdf",
        "https://www.aepd.es/es/documento/acuerdo-de-modificacion-instruccion-aplazamientos.pdf",
        "https://www.aepd.es/documento/proyecto-circular-opiniones-politicas-tramite-de-audiencia.pdf",
    ]

    stored = 0
    for url in resolution_urls:
        content = fetch_pdf(url)
        if not content:
            print(f"  [SKIP] Could not fetch PDF: {url}")
            continue
        try:
            payload = build_payload(url, content)
            upsert_documento(conn, payload)
            stored += 1
            print(f"  [OK] {payload['referencia']} ({payload['tipo_documento']})")
        except Exception as e:
            print(f"  [FAIL] {url}: {e}")
        time.sleep(DELAY)

    return stored


def seed_html_pages(conn) -> int:
    """Seed HTML pages from key AEPD sections."""
    html_pages = [
        "https://www.aepd.es/guias-y-herramientas/guias",
        "https://www.aepd.es/informes-y-resoluciones/resoluciones",
        "https://www.aepd.es/informes-y-resoluciones/informes-juridicos",
        "https://www.aepd.es/informes-y-resoluciones/instrucciones",
        "https://www.aepd.es/publicaciones-y-resoluciones/circulares",
        "https://www.aepd.es/areas-de-actuacion/salud/guias-informes-del-gabinete-juridico-y-consultas-de-delegados-de-pd-sobre-salud",
        "https://www.aepd.es/areas-de-actuacion/administraciones-publicas/guias-informes-y-documentos",
    ]

    stored = 0
    for url in html_pages:
        content = fetch_html(url)
        if not content:
            print(f"  [SKIP] Could not fetch HTML: {url}")
            continue
        try:
            payload = build_payload(url, content)
            upsert_documento(conn, payload)
            stored += 1
            print(f"  [OK] {payload['referencia']} ({payload['tipo_documento']})")
        except Exception as e:
            print(f"  [FAIL] {url}: {e}")
        time.sleep(DELAY)

    return stored


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed AEPD documents")
    parser.add_argument("--dry-run", action="store_true", help="List URLs without fetching")
    args = parser.parse_args()

    conn = psycopg.connect(DB_URL_DEFAULT, autocommit=True)

    try:
        total = 0

        if args.dry_run:
            print("=== Dry run: would seed the following ===")
            print(f"\n  PDF guides: {len(seed_pdf_guides.__code__.co_consts)} URLs")
            print(f"  Resolutions: 24 URLs")
            print(f"  HTML pages: 7 URLs")
            return

        print("\n=== Seeding AEPD PDF guides ===")
        total += seed_pdf_guides(conn)

        print("\n=== Seeding AEPD resolutions & instructions ===")
        total += seed_resolutions(conn)

        print("\n=== Seeding AEPD HTML pages ===")
        total += seed_html_pages(conn)

        print(f"\nDone! {total} documents stored in documento_interpretativo")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
