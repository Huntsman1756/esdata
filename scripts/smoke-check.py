#!/usr/bin/env python3
"""Reusable HTTP smoke checks for esdata deployments."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_CHECKS = [
    ("/health", 200, None),
    ("/v1/legislacion/LIVA/articulos/91", 200, "texto"),
    ("/v1/legislacion/ITPAJD", 200, "codigo"),
    ("/v1/legislacion/IRNR", 200, "codigo"),
    ("/v1/legislacion/IIEE", 200, "codigo"),
    ("/v1/legislacion/HL", 200, "codigo"),
    ("/v1/legislacion/DAC6", 200, "codigo"),
    ("/v1/legislacion/DAC6RD", 200, "codigo"),
    ("/v1/legislacion/DAC6EU", 200, "codigo"),
    ("/v1/bdns", 200, "convocatorias"),
    ("/v1/materias/tipo-reducido-iva", 200, "articulos"),
    ("/v1/legislacion/buscar?q=tipo+reducido&norma=LIVA", 200, "resultados"),
    ("/v1/legislacion/cobertura", 200, "normas"),
    ("/v1/modelos/124", 200, "codigo"),
    ("/status", 200, "workers"),
]


def run_check(base_url: str, path: str, expected_status: int, expected_key: str | None, retries: int, sleep_seconds: int) -> str | None:
    last_error = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(f"{base_url}{path}", timeout=10) as response:
                status_code = response.getcode()
                payload = json.loads(response.read().decode("utf-8"))

            if status_code == expected_status and (
                not expected_key or expected_key in payload
            ):
                return None

            last_error = (
                f"status {status_code} (esperado {expected_status})"
                if status_code != expected_status
                else f"clave '{expected_key}' ausente en respuesta"
            )
        except urllib.error.HTTPError as exc:
            last_error = f"status {exc.code} (esperado {expected_status})"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(sleep_seconds)

    return f"FAIL {path}: {last_error}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run reusable smoke checks against esdata API")
    parser.add_argument("--base-url", required=True, help="Base URL of the esdata API")
    parser.add_argument("--retries", type=int, default=10, help="Retries per check")
    parser.add_argument("--sleep", type=int, default=5, help="Seconds between retries")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    parsed = urllib.parse.urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        print(f"Invalid base URL: {base_url}")
        return 2

    failed = []
    for path, expected_status, expected_key in DEFAULT_CHECKS:
        error = run_check(
            base_url,
            path,
            expected_status,
            expected_key,
            retries=args.retries,
            sleep_seconds=args.sleep,
        )
        if error:
            failed.append(error)

    if failed:
        print("\n".join(failed))
        return 1

    print(f"Smoke tests OK ({len(DEFAULT_CHECKS)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
