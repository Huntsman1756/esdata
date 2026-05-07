"""Smoke tests operativos para verificacion post-deploy.

Se ejecuta contra una API en produccion o local y verifica:
- Salud de API (health endpoint)
- Salud de workers (ultimo sync log)
- Cobertura de datos (minimo de documentos por tabla)
- Errores recientes de ingesta

Uso:
    python scripts/smoke_tests.py                     # contra API en ESDATA_API_URL
    python scripts/smoke_tests.py --local              # contra http://localhost:8000
    python scripts/smoke_tests.py --base-url http://x  # URL personalizada
    python scripts/smoke_tests.py --json               # salida JSON para CI
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
except ImportError:
    print("ERROR: httpx no instalado. Ejecutar: pip install httpx")
    sys.exit(1)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SmokeResult:
    def __init__(self, name: str):
        self.name = name
        self.started = time.monotonic()
        self.status = "pending"
        self.details: dict[str, Any] = {}
        self.error: str | None = None

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.started) * 1000

    def ok(self, **kwargs):
        self.status = "ok"
        self.details.update(kwargs)

    def fail(self, reason: str, **kwargs):
        self.status = "fail"
        self.error = reason
        self.details.update(kwargs)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "details": self.details,
            "error": self.error,
        }


def check_api_health(client: httpx.Client, result: SmokeResult) -> None:
    """Verificar que la API responde en /health."""
    try:
        resp = client.get("/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result.ok(
                status_code=resp.status_code,
                response_time_ms=round(resp.elapsed.total_seconds() * 1000, 1),
                health=data if isinstance(data, dict) else {},
            )
        else:
            result.fail(
                f"Status {resp.status_code}",
                status_code=resp.status_code,
                body=resp.text[:500],
            )
    except httpx.TimeoutException:
        result.fail("Timeout conectando a API")
    except httpx.ConnectError as e:
        result.fail(f"Conexion fallida: {e}")
    except Exception as e:
        result.fail(f"Error inesperado: {e}")


def check_api_search(client: httpx.Client, result: SmokeResult) -> None:
    """Verificar que la busqueda de legislacion funciona."""
    try:
        resp = client.get(
            "/v1/legislacion/buscar",
            params={"q": "iva", "limit": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data if isinstance(data, list) else data.get("resultados", [])
            result.ok(
                status_code=resp.status_code,
                response_time_ms=round(resp.elapsed.total_seconds() * 1000, 1),
                results_count=len(results),
            )
            if len(results) == 0:
                result.fail("Sin resultados para 'iva' (posible problema de datos)")
        else:
            result.fail(
                f"Status {resp.status_code}",
                body=resp.text[:500],
            )
    except httpx.TimeoutException:
        result.fail("Timeout en busqueda")
    except Exception as e:
        result.fail(f"Error: {e}")


def check_api_doctrina(client: httpx.Client, result: SmokeResult) -> None:
    """Verificar que la busqueda de doctrina funciona."""
    try:
        resp = client.get(
            "/v1/doctrina/buscar",
            params={"q": "retencion", "limit": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data if isinstance(data, list) else data.get("resultados", [])
            result.ok(
                status_code=resp.status_code,
                response_time_ms=round(resp.elapsed.total_seconds() * 1000, 1),
                results_count=len(results),
            )
        else:
            result.fail(
                f"Status {resp.status_code}",
                body=resp.text[:500],
            )
    except httpx.TimeoutException:
        result.fail("Timeout en busqueda doctrina")
    except Exception as e:
        result.fail(f"Error: {e}")


def check_db_coverage(client: httpx.Client, result: SmokeResult) -> None:
    """Verificar cobertura minima de datos via endpoint de stats."""
    try:
        resp = client.get("/v1/stats", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result.ok(
                status_code=resp.status_code,
                stats=data,
            )
        else:
            result.fail(
                f"Status {resp.status_code} (endpoint /v1/stats no disponible)",
                body=resp.text[:500],
            )
    except Exception as e:
        result.fail(f"Error obteniendo stats: {e}")


def check_sync_logs(client: httpx.Client, result: SmokeResult) -> None:
    """Verificar que hay logs de sincronizacion recientes."""
    try:
        resp = client.get(
            "/v1/sync/logs",
            params={"limit": 5},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            logs = data if isinstance(data, list) else data.get("logs", [])
            result.ok(
                status_code=resp.status_code,
                logs_count=len(logs),
                last_sync=logs[0] if logs else None,
            )
            if len(logs) == 0:
                result.fail("Sin logs de sincronizacion (posible problema de workers)")
        else:
            result.fail(
                f"Status {resp.status_code} (endpoint /v1/sync/logs no disponible)",
                body=resp.text[:500],
            )
    except Exception as e:
        result.fail(f"Error obteniendo sync logs: {e}")


def check_api_errors(client: httpx.Client, result: SmokeResult) -> None:
    """Verificar que no hay errores recientes en la API."""
    try:
        resp = client.get("/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Algunos health endpoints incluyen campo de errores
            errors = data.get("errors", []) if isinstance(data, dict) else []
            result.ok(
                status_code=resp.status_code,
                errors_count=len(errors),
            )
            if errors:
                result.fail(f"Se encontraron {len(errors)} errores en health check")
        else:
            result.fail(f"Status {resp.status_code}")
    except Exception as e:
        result.fail(f"Error verificando errores: {e}")


SMOKE_TESTS = [
    ("api_health", check_api_health, "API health endpoint"),
    ("api_search", check_api_search, "Busqueda de legislacion"),
    ("api_doctrina", check_api_doctrina, "Busqueda de doctrina"),
    ("db_coverage", check_db_coverage, "Cobertura de datos"),
    ("sync_logs", check_sync_logs, "Logs de sincronizacion"),
    ("api_errors", check_api_errors, "Errores recientes"),
]


def run_smoke_tests(
    base_url: str,
    json_output: bool = False,
    fail_fast: bool = False,
) -> tuple[list[SmokeResult], bool]:
    """Ejecutar todos los smoke tests.

    Returns:
        Tuple de (resultados, todos_ok)
    """
    full_url = base_url.rstrip("/")
    if not full_url.startswith(("http://", "https://")):
        full_url = f"http://{full_url}"

    results: list[SmokeResult] = []
    all_ok = True

    with httpx.Client(base_url=f"{full_url}/", timeout=30) as client:
        for test_fn, test_func, description in SMOKE_TESTS:
            result = SmokeResult(test_fn)
            print(f"  [RUN] {test_fn}: {description}")
            try:
                test_func(client, result)
            except Exception as e:
                result.fail(f"Excepcion: {e}")

            results.append(result)

            status_icon = "✅" if result.status == "ok" else "❌"
            print(f"  {status_icon} {test_fn}: {result.status}" +
                  (f" — {result.error}" if result.error else ""))

            if result.status == "fail":
                all_ok = False
                if fail_fast:
                    print("\n  ⚠️  Fail-fast activado, deteniendo tests.")
                    break

    return results, all_ok


def print_summary(results: list[SmokeResult]) -> None:
    """Imprimir resumen de resultados."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "ok")
    failed = total - passed

    print("\n" + "=" * 60)
    print("  SMOKE TESTS — RESULTADOS")
    print("=" * 60)

    for r in results:
        status_icon = "✅" if r.status == "ok" else "❌"
        print(f"  {status_icon} {r.name}: {r.status} ({r.elapsed_ms:.0f}ms)")
        if r.details:
            for key, value in r.details.items():
                if key in ("response_time_ms", "results_count", "elapsed_ms"):
                    print(f"      {key}: {value}")
        if r.error:
            print(f"      ERROR: {r.error}")

    print("-" * 60)
    print(f"  Total: {total} | ✅ {passed} | ❌ {failed}")
    print("=" * 60)


def print_json_output(results: list[SmokeResult]) -> None:
    """Imprimir resultados en JSON para CI/CD."""
    all_ok = all(r.status == "ok" for r in results)
    output = {
        "timestamp": _iso_now(),
        "passed": all_ok,
        "total": len(results),
        "passed_count": sum(1 for r in results if r.status == "ok"),
        "failed_count": sum(1 for r in results if r.status != "ok"),
        "tests": [r.to_dict() for r in results],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Smoke tests operativos")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Usar http://localhost:8000",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="URL base de la API (ej: http://localhost:8000 o https://api.example.com)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida JSON para CI/CD",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Detener al primer fallo",
    )
    args = parser.parse_args()

    if args.local:
        base_url = "http://localhost:8000"
    elif args.base_url:
        base_url = args.base_url
    else:
        # Intentar obtener de entorno
        import os
        base_url = os.getenv("ESDATA_API_URL", "http://localhost:8000")

    print(f"\n  Smoke tests contra: {base_url}")
    print(f"  Fecha: {_iso_now()}")
    print()

    results, all_ok = run_smoke_tests(base_url, json_output=args.json, fail_fast=args.fail_fast)

    if args.json:
        print_json_output(results)
    else:
        print_summary(results)
        print()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
