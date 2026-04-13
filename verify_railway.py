#!/usr/bin/env python3
"""verify_railway.py - comprobar estado real del despliegue."""

import json
import subprocess
import sys


def run(cmd: str):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


SERVICES = [
    "esdata",
    "worker-boe",
    "worker-dgt",
    "worker-teac",
    "worker-modelos",
    "cron-boe-daily",
    "cron-dgt-weekly",
    "cron-teac-weekly",
    "cron-modelos-daily",
    "Postgres",
]
CRITICAL_VARS = {"DATABASE_URL", "BOE_API_BASE", "APP_ENV"}

print("=== Estado Railway ===\n")

code, out, _ = run("railway --version")
if code != 0:
    print("[FAIL] railway CLI no encontrado. Instalar: npm install -g @railway/cli")
    sys.exit(1)
print(f"[OK  ] railway CLI: {out}\n")

code, out, err = run("railway status --json")
if code != 0:
    print(f"[FAIL] no se pudo obtener `railway status --json`: {err}")
    sys.exit(1)

status = json.loads(out)
service_nodes = status["environments"]["edges"][0]["node"]["serviceInstances"]["edges"]
status_by_name = {
    node["node"]["serviceName"]: node["node"]["latestDeployment"]["status"]
    for node in service_nodes
}

for service in SERVICES:
    current = status_by_name.get(service)
    if current is None:
        print(f"[WARN] {service}: no existe en el proyecto")
    elif current == "SUCCESS":
        print(f"[OK  ] {service}: {current}")
    else:
        print(f"[WARN] {service}: {current}")

print("\n--- Variables de entorno worker-boe ---")
code, out, err = run("railway variable list --service worker-boe -k")
if code != 0:
    print(f"[WARN] No se pudieron listar variables: {err[:120]}")
else:
    keys = {line.split("=", 1)[0].strip() for line in out.splitlines() if "=" in line}
    for key in sorted(CRITICAL_VARS):
        icon = "[OK  ]" if key in keys else "[FAIL]"
        state = "configurada" if key in keys else "NO ENCONTRADA"
        print(f"{icon} {key} {state}")

print("\n--- Comprobaciones manuales recomendadas ---")
print("railway logs --service worker-boe --tail 50")
print("railway logs --service worker-modelos --tail 50")
print("railway logs --service esdata --tail 50")
print("curl https://esdata-production.up.railway.app/health")
print("curl https://esdata-production.up.railway.app/status")
print("curl https://esdata-production.up.railway.app/v1/legislacion/cobertura")
print("curl https://esdata-production.up.railway.app/v1/modelos")

print("\n--- Verificacion de BD tras migracion ---")
print("Ejecutar manualmente despues de aplicar 002_fulltext_search.sql:")
print("SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector,")
print("       COUNT(*) AS total")
print("FROM version_articulo;")
