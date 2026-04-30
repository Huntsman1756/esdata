#!/usr/bin/env python3
"""Descargar textos completos de EUR-Lex para los CELEXs seed del worker.

EUR-Lex bloquea requests automatizados (WAF + JS challenge), asi que se
necesita un browser headless para renderizar las paginas y extraer el HTML.

Este script se ejecuta UNA VEZ fuera del container del worker, genera archivos
en corpora/eurlex/{celex}.html que el worker eurlex.py lee como fallback.

Uso:
    python scripts/eurlex_corpus_download.py

Requisitos:
    playwright (pip install playwright)
    playwright install chromium

Salida:
    corpora/eurlex/32014L0065.html  (MiFID II)
    corpora/eurlex/32014R0060.html (MiFIR)
    ...
"""

import os
import sys
import time
from pathlib import Path

# Agregar al path para importar EURLEX_NORMAS del worker
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "workers"))

from eurlex import EURLEX_NORMAS
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "corpora" / "eurlex"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_celex(celex: str, titulo: str, output_path: Path) -> bool:
    """Descargar el texto completo de un CELEX via browser headless."""
    url = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )
        page = context.new_page()

        try:
            response = page.goto(url, wait_until="networkidle", timeout=60000)
            if response and response.status == 200:
                # Esperar a que el WAF challenge se resuelva
                time.sleep(5)
                html = page.content()
                if len(html) > 1000:
                    output_path.write_text(html, encoding="utf-8")
                    print(f"  OK   {celex} ({len(html)} bytes)")
                    return True
                else:
                    print(f"  FAIL {celex} (solo {len(html)} bytes)")
                    return False
            else:
                status = response.status if response else "error"
                print(f"  FAIL {celex} (HTTP {status})")
                return False
        except Exception as e:
            print(f"  FAIL {celex} ({e})")
            return False
        finally:
            browser.close()


def main():
    print(f"Descargando {len(EURLEX_NORMAS)} CELEXs de EUR-Lex...")
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
            print(f"  SKIP {celex} (ya existe, {output_path.stat().st_size} bytes)")
            success += 1
            continue

        time.sleep(2)  # Rate limit EUR-Lex
        if download_celex(celex, titulo, output_path):
            success += 1
        else:
            failed += 1

    print()
    print(f"Resultado: {success} OK, {failed} FAIL, {len(celexes)} total")

    if failed > 0:
        print("\nCELEXs que fallaron:")
        for celex, titulo in celexes:
            output_path = OUTPUT_DIR / f"{celex}.html"
            if not output_path.exists() or output_path.stat().st_size <= 1000:
                print(f"  - {celex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
