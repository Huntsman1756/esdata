#!/usr/bin/env python3
"""Descargar textos completos de EUR-Lex para los CELEXs seed del worker.

Usa la REST API de EU Publications Office:
  http://publications.europa.eu/resource/celex/{CELEX}

Esta API devuelve el texto completo en HTML/XML con los headers correctos.
No requiere browser automation ni JS rendering.

Este script se ejecuta UNA VEZ fuera del container del worker, genera archivos
en corpora/eurlex/{celex}.html que el worker eurlex.py lee como fallback.

Uso:
    python scripts/eurlex_corpus_download.py

Requisitos:
    Ninguno — usa httpx (ya instalado en requirements)

Salida:
    corpora/eurlex/32014L0065.html  (MiFID II) — ~1.3MB
    corpora/eurlex/32014R0600.html (MiFIR)
    ...
"""

import sys
import time
from pathlib import Path

import httpx

# Agregar al path para importar EURLEX_NORMAS del worker
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "workers"))

from eurlex import EURLEX_NORMAS

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "corpora" / "eurlex"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EU_PUBS_BASE = "http://publications.europa.eu/resource/celex"

HEADERS = {
    "Accept-Language": "es, fr;q=0.8, de;q=0.7",
    "Accept": "text/html, text/html;type=simplified, text/plain, application/xhtml+xml, application/pdf",
}


def download_celex(celex: str, output_path: Path) -> bool:
    """Descargar el texto completo de un CELEX via EU Publications REST API."""
    url = f"{EU_PUBS_BASE}/{celex}"

    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url, headers=HEADERS)
            if response.status_code == 200 and len(response.content) > 1000:
                output_path.write_bytes(response.content)
                print(f"  OK   {celex} ({len(response.content):,} bytes)")
                return True
            else:
                print(f"  FAIL {celex} (HTTP {response.status_code}, {len(response.content)} bytes)")
                return False
    except Exception as e:
        print(f"  FAIL {celex} ({e})")
        return False


def main():
    print(f"Descargando {len(EURLEX_NORMAS)} CELEXs via EU Publications REST API")
    print(f"Endpoint: {EU_PUBS_BASE}/{{CELEX}}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    celexes = [
        (n["boe_id"].replace("EUR-CELEX-", ""), n["titulo"])
        for n in EURLEX_NORMAS
    ]

    success = 0
    failed = 0

    for i, (celex, titulo) in enumerate(celexes, 1):
        print(f"[{i}/{len(celexes)}] {celex} — {titulo[:60]}")
        output_path = OUTPUT_DIR / f"{celex}.html"

        if output_path.exists() and output_path.stat().st_size > 1000:
            print(f"  SKIP {celex} (ya existe, {output_path.stat().st_size:,} bytes)")
            success += 1
            continue

        time.sleep(1)  # Rate limit EU Publications Office
        if download_celex(celex, output_path):
            success += 1
        else:
            failed += 1

    print()
    print(f"Resultado: {success} OK, {failed} FAIL, {len(celexes)} total")

    if failed > 0:
        print("\nCELEXs que fallaron:")
        for celex, _titulo in celexes:
            output_path = OUTPUT_DIR / f"{celex}.html"
            if not output_path.exists() or output_path.stat().st_size <= 1000:
                print(f"  - {celex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
