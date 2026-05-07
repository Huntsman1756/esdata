# Worker Scheduler, Drift Guard, and DTA Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** alinear el repo con la remediacion real de `WorkerSilent`, anadir una guardia operativa explicita contra el drift de scheduler/alertas y cerrar la documentacion viva de convenios DTA por pais sin sobreprometer cobertura.

**Architecture:** se mantiene el modelo actual `systemd` + `docker compose run --rm` y se endurece con tres guardrails pequenos: un unit file de referencia correcto, una alerta `WorkerSilent` basada en `worker_stale_status` y un script operativo en `scripts/ops/` con modos `check`, `fix-drift` y `rerun`. La parte DTA no amplia funcionalidad; documenta el contrato HTTP real de `apps/api/routers/dta_convenios.py`, usando ejemplos verificados por tests y explicando los limites actuales entre fixtures, seeds y runtime.

**Tech Stack:** Python 3.12, pytest, FastAPI, Docker Compose, systemd, Prometheus, Markdown docs, SSH.

---

## File Map

- `infra/deploy/systemd/esdata-job@.service`
  Fuente de verdad del unit oneshot `cron-*`; debe reflejar el contrato real del VPS recuperado.
- `infra/observability/alerts.yml`
  Regla `WorkerSilent`; debe consumir `worker_stale_status == 1` y no una ventana fija de `48h`.
- `scripts/ops/worker_scheduler_guard.py`
  Utilidad operativa con subcomandos `check`, `fix-drift` y `rerun`; sin side effects por defecto.
- `scripts/tests/test_worker_scheduler_guard.py`
  Tests de contrato para el script: parsing de archivos, deteccion de drift y generacion de comandos.
- `apps/api/tests/test_status_contract.py`
  Fija el contrato semanal de `/status` para que `72h` no implique `stale=true` en workers `cron-*` semanales.
- `docs/deployment/server-installation.md`
  Guia de instalacion; debe documentar la materializacion `/etc/esdata/esdata.env`, el unit instalado y el chequeo anti-drift.
- `docs/operations/runbooks/deploy-compose.md`
  Runbook operativo; debe incluir verificacion de `systemd`, `worker_stale_status` y el uso del nuevo script.
- `docs/operations/agent-notes.md`
  Memoria operativa reusable del trap `--no-deps` y de la regla correcta de `WorkerSilent`.
- `docs/manual-usuario/06-api-y-ejemplos.md`
  Ejemplos DTA reales y conservadores.
- `docs/manual-usuario/09-referencia-de-endpoints.md`
  Mapa rapido de endpoints DTA.
- `docs/manual-usuario/05-limites-alcance-y-estado-actual.md`
  Limites de cobertura DTA por dataset/instancia.
- `docs/master-execution-roadmap.md`
  Solo si hace falta corregir o matizar una contradiccion factual activa sobre convenios DTA o cerrar el reclamo abierto del `2026-05-06`.

**Git policy:** no crear commits salvo peticion explicita del usuario.

### Task 1: Lock the scheduler and alert contracts with tests

**Files:**
- Create: `scripts/tests/test_worker_scheduler_guard.py`
- Modify: `apps/api/tests/test_status_contract.py`
- Test: `scripts/tests/test_worker_scheduler_guard.py`
- Test: `apps/api/tests/test_status_contract.py`

- [ ] **Step 1: Write the failing scheduler/alert contract tests**

Create `scripts/tests/test_worker_scheduler_guard.py` with this content:

```python
#!/usr/bin/env python3
"""Contract tests for worker scheduler drift guard."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ops.worker_scheduler_guard import (
    installed_unit_has_no_deps,
    repo_alert_uses_stale_gauge,
    build_fix_drift_commands,
)


def test_installed_unit_detects_no_deps_flag() -> None:
    unit_text = "ExecStart=/usr/bin/docker compose ... run --rm --no-deps %i\n"
    assert installed_unit_has_no_deps(unit_text) is True


def test_installed_unit_accepts_clean_run_rm_contract() -> None:
    unit_text = "ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i\n"
    assert installed_unit_has_no_deps(unit_text) is False


def test_repo_alert_detects_wrong_fixed_lag_rule() -> None:
    alerts_text = """
groups:
  - name: esdata.workers
    rules:
      - alert: WorkerSilent
        expr: worker_lag_seconds > 172800
"""
    assert repo_alert_uses_stale_gauge(alerts_text) is False


def test_repo_alert_accepts_exported_stale_gauge() -> None:
    alerts_text = """
groups:
  - name: esdata.workers
    rules:
      - alert: WorkerSilent
        expr: worker_stale_status == 1
"""
    assert repo_alert_uses_stale_gauge(alerts_text) is True


def test_fix_drift_commands_reference_supported_runtime_paths() -> None:
    commands = build_fix_drift_commands(repo_root="/srv/esdata")
    assert any("/etc/esdata/esdata.env" in command for command in commands)
    assert any("esdata-job@.service" in command for command in commands)
    assert any("prometheus" in command for command in commands)
```

- [ ] **Step 2: Add the weekly stale regression test to `/status`**

Append this test to `apps/api/tests/test_status_contract.py`:

```python
@pytest.mark.asyncio
async def test_status_keeps_weekly_cron_healthy_with_three_day_lag():
    app, _ = _get_app_and_engine()
    _seed_sync_log(
        "cron-cnmv-weekly",
        finished_at=datetime.now(UTC) - timedelta(hours=72),
        status="ok",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["cron-cnmv-weekly"]
    assert worker["status"] == "ok"
    assert worker["stale"] is False
```

- [ ] **Step 3: Run the tests to verify they fail for the right reasons**

Run:

```bash
python -m pytest scripts/tests/test_worker_scheduler_guard.py apps/api/tests/test_status_contract.py -v --tb=short
```

Expected:

- import error for `scripts.ops.worker_scheduler_guard` because the script does not exist yet
- or, once the script scaffold exists, tests fail because `infra/observability/alerts.yml` still contains `worker_lag_seconds > 172800`
- the new `/status` test passes or is ready to pass once imports resolve, proving the API contract already treats weekly cron workers as healthy at `72h`

### Task 2: Implement the repo-side systemd and alert fixes

**Files:**
- Modify: `infra/deploy/systemd/esdata-job@.service`
- Modify: `infra/observability/alerts.yml`

- [ ] **Step 1: Update the unit file to the supported runtime contract**

Replace `infra/deploy/systemd/esdata-job@.service` with:

```ini
[Unit]
Description=esdata scheduled job (%i)
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=deploy
WorkingDirectory=/srv/esdata
ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i
```

- [ ] **Step 2: Replace the fixed 48h rule with the exported stale gauge**

Replace the `WorkerSilent` stanza in `infra/observability/alerts.yml` with:

```yaml
      - alert: WorkerSilent
        expr: worker_stale_status == 1
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Worker {{ $labels.worker }} marcado como stale"
          description: "El worker {{ $labels.worker }} supera el umbral de frescura exportado por la API a partir de sync_log."
```

- [ ] **Step 3: Re-run the narrow tests for the changed contracts**

Run:

```bash
python -m pytest scripts/tests/test_worker_scheduler_guard.py apps/api/tests/test_status_contract.py -v --tb=short
```

Expected:

- tests still fail because the guard script is not implemented yet
- no failure remains related to the `48h` alert or to the wrong `ExecStart` contract in the repo files

### Task 3: Implement the explicit drift/remediation guard script

**Files:**
- Create: `scripts/ops/worker_scheduler_guard.py`
- Test: `scripts/tests/test_worker_scheduler_guard.py`

- [ ] **Step 1: Write the minimal script structure and pure helper functions**

Create `scripts/ops/worker_scheduler_guard.py` with this content:

```python
#!/usr/bin/env python3
"""Check and remediate scheduler/alert drift for esdata cron workers."""

from __future__ import annotations

import argparse
from pathlib import Path


def installed_unit_has_no_deps(unit_text: str) -> bool:
    return "--no-deps" in unit_text


def repo_alert_uses_stale_gauge(alerts_text: str) -> bool:
    return "alert: WorkerSilent" in alerts_text and "expr: worker_stale_status == 1" in alerts_text


def build_fix_drift_commands(repo_root: str) -> list[str]:
    return [
        f"install -m 0644 {repo_root}/infra/deploy/systemd/esdata-job@.service /etc/systemd/system/esdata-job@.service",
        "systemctl daemon-reload",
        f"docker compose --env-file /etc/esdata/esdata.env -f {repo_root}/infra/deploy/docker-compose.prod.yml up -d prometheus",
    ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or remediate worker scheduler drift")
    parser.add_argument("mode", choices=["check", "fix-drift", "rerun"])
    parser.add_argument("--repo-root", default="/srv/esdata")
    parser.add_argument("--installed-unit", default="/etc/systemd/system/esdata-job@.service")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("workers", nargs="*")
    args = parser.parse_args()

    if args.mode == "check":
        repo_root = Path(args.repo_root)
        alerts_text = _read(repo_root / "infra" / "observability" / "alerts.yml")
        unit_text = _read(Path(args.installed_unit))
        print(f"WorkerSilent uses stale gauge: {repo_alert_uses_stale_gauge(alerts_text)}")
        print(f"Installed unit has --no-deps: {installed_unit_has_no_deps(unit_text)}")
        return 0

    if args.mode == "fix-drift":
        for command in build_fix_drift_commands(args.repo_root):
            print(command)
        if not args.apply:
            print("Dry run only. Re-run with --apply to execute manually approved steps.")
        return 0

    for worker in args.workers:
        print(f"sudo systemctl start esdata-job@{worker}.service")
        print(f"systemctl show esdata-job@{worker}.service -p Result -p ExecMainStatus -p ActiveState -p SubState")
        print(f"journalctl -u esdata-job@{worker}.service -n 80 --no-pager")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the script tests to verify the new helpers pass**

Run:

```bash
python -m pytest scripts/tests/test_worker_scheduler_guard.py -v --tb=short
```

Expected:

- all tests in `scripts/tests/test_worker_scheduler_guard.py` pass

- [ ] **Step 3: Strengthen the script so `fix-drift` and `rerun` stay explicit and auditable**

Update `scripts/ops/worker_scheduler_guard.py` so `fix-drift --apply` still prints the commands before running and `rerun` rejects an empty worker list:

```python
    if args.mode == "fix-drift":
        commands = build_fix_drift_commands(args.repo_root)
        for command in commands:
            print(command)
        if not args.apply:
            print("Dry run only. Re-run with --apply to execute manually approved steps.")
            return 0
        print("Apply mode requested. Execute the printed commands in an approved VPS session.")
        return 0

    if not args.workers:
        print("rerun requires at least one cron-* worker name")
        return 2

    for worker in args.workers:
        print(f"sudo systemctl start esdata-job@{worker}.service")
        print(f"systemctl show esdata-job@{worker}.service -p Result -p ExecMainStatus -p ActiveState -p SubState")
        print(f"journalctl -u esdata-job@{worker}.service -n 80 --no-pager")
```

- [ ] **Step 4: Re-run the script tests and a smoke invocation**

Run:

```bash
python -m pytest scripts/tests/test_worker_scheduler_guard.py -v --tb=short
python scripts/ops/worker_scheduler_guard.py fix-drift --repo-root /srv/esdata
python scripts/ops/worker_scheduler_guard.py rerun cron-dgt-weekly cron-teac-weekly
```

Expected:

- tests pass
- the `fix-drift` invocation prints the install/systemctl/prometheus commands without executing them
- the `rerun` invocation prints the three validation commands per worker

### Task 4: Update deploy and operations docs for the corrected runtime contract

**Files:**
- Modify: `docs/deployment/server-installation.md`
- Modify: `docs/operations/runbooks/deploy-compose.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Update server installation to describe the installed env file and drift check**

Edit `docs/deployment/server-installation.md` so the `Cron jobs automaticos` section includes these exact lines in its timer flow:

````md
sudo cp infra/deploy/systemd/esdata-job@.service /etc/systemd/system/
sudo cp infra/deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esdata-boe-daily.timer esdata-modelos-daily.timer esdata-dgt-weekly.timer esdata-teac-weekly.timer esdata-bdns-weekly.timer esdata-borme-weekly.timer esdata-cnmv-weekly.timer esdata-sepblac-weekly.timer esdata-bde-weekly.timer esdata-cendoj-weekly.timer esdata-aepd-weekly.timer esdata-eurlex-weekly.timer
systemctl cat esdata-job@.service
python scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service
````

Also add one paragraph just below the code block:

````md
En el VPS la materializacion operativa del entorno vive en `/etc/esdata/esdata.env`. `infra/deploy/.env.prod` sigue siendo la referencia del repo para Compose y documentacion, pero el unit instalado debe apuntar al fichero externalizado del host. Si `systemctl cat esdata-job@.service` muestra `--no-deps`, hay drift operativo y debe corregirse antes de confiar en los cron semanales.
````

- [ ] **Step 2: Update the deploy runbook to mention stale gauge and the new script**

Edit `docs/operations/runbooks/deploy-compose.md` so the `Timers systemd` and `Verificaciones post-deploy` sections include these exact fragments:

````md
Validacion operativa minima:

1. el unit instalado debe ejecutar `docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i` sin `--no-deps`
2. `WorkerSilent` debe evaluarse sobre `worker_stale_status`, no sobre una ventana fija de `48h`
3. tras cambiar `infra/observability/alerts.yml`, hay que recrear `prometheus` o recargar explicitamente sus reglas en el host
4. antes de validar alertas, invocar `/status` una vez para refrescar las metricas `worker_stale_status` derivadas de `sync_log`

Comando recomendado de chequeo:

```bash
python scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service
```
````

- [ ] **Step 3: Insert the reusable trap into agent notes**

Insert this note at the top of `docs/operations/agent-notes.md` under `## Notas actuales`:

````md
### 2026-05-06 - Cron semanales en produccion: `--no-deps` en systemd rompe jobs y `WorkerSilent` no puede usar 48h fijo

- Scope: `infra/deploy/systemd/esdata-job@.service`, `infra/observability/alerts.yml`, VPS Compose/productivo
- Hallazgo: si el unit instalado de `esdata-job@.service` deriva y ejecuta `docker compose ... run --rm --no-deps %i`, varios `cron-*` semanales pueden fallar antes de arrancar el worker real con el error `container ... is not connected to the network deploy_esdata-internal`; en ese estado no hay fila nueva en `sync_log` porque el fallo sucede antes del codigo Python.
- Impacto: los cron one-shot quedan rotos aunque los timers `systemd` sigan disparando, y la monitorizacion se vuelve enganosa si `WorkerSilent` se basa en `worker_lag_seconds > 172800` en lugar de usar el contrato real de stale ya calculado por la API.
- Regla practica: el unit instalado debe mantenerse alineado con el repo y ejecutar `docker compose ... run --rm %i` sin `--no-deps`; `WorkerSilent` debe evaluar `worker_stale_status == 1`; y tras cambiar reglas de Prometheus hay que refrescar `/status` antes de validar alertas.
````

- [ ] **Step 4: Run a documentation spot check and the script tests again**

Run:

```bash
python -m pytest scripts/tests/test_worker_scheduler_guard.py -v --tb=short
```

Expected:

- script tests still pass
- the docs now mention `systemctl cat esdata-job@.service`, `/etc/esdata/esdata.env`, `worker_stale_status` and the guard script

### Task 5: Document the DTA endpoints and limits conservatively

**Files:**
- Modify: `docs/manual-usuario/06-api-y-ejemplos.md`
- Modify: `docs/manual-usuario/09-referencia-de-endpoints.md`
- Modify: `docs/manual-usuario/05-limites-alcance-y-estado-actual.md`
- Test: `apps/api/tests/test_dta_convenios.py`

- [ ] **Step 1: Add real DTA API examples to the manual**

Append this block to `docs/manual-usuario/06-api-y-ejemplos.md` just after the `Modelos AEAT` section and before `Obligaciones regulatorias`:

````md
## Convenios DTA y retenciones internacionales

Listar convenios DTA:

```bash
curl -G -s http://127.0.0.1:8000/v1/internacional/convenios --data-urlencode "pais_a=US" --data-urlencode "pais_b=ES"
```

Detalle de un convenio:

```bash
curl -s http://127.0.0.1:8000/v1/internacional/convenios/ES_US_DTA
```

Listar reglas de retencion:

```bash
curl -G -s http://127.0.0.1:8000/v1/internacional/convenios/retenciones --data-urlencode "tipo_renta=dividends"
```

Calcular retencion aplicable:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/internacional/convenios/retencion \
  -H "Content-Type: application/json" \
  -d '{"pais_residencia":"US","tipo_renta":"dividends"}'
```

Reglas practicas:

- estos endpoints exponen convenios DTA y reglas de retencion ya cargados en la instancia; no implican cobertura exhaustiva de todos los paises
- el calculo de `retencion` cruza la regla de withholding por tipo de renta con un convenio DTA vigente si existe para la pareja de paises consultada
- en fixtures y compatibilidad legacy pueden coexistir codigos como `DTA_US_ES` y `ES_US_DTA`; usa en ejemplos solo los codigos verificados por tests o por la instancia objetivo
````

- [ ] **Step 2: Add the DTA endpoint block to the endpoint reference**

Insert this section into `docs/manual-usuario/09-referencia-de-endpoints.md` after `Modelos AEAT` and before `Obligaciones, cambios y compliance`:

````md
## Convenios DTA y retenciones internacionales

- `GET /v1/internacional/convenios` — listado de convenios DTA con filtros por `pais_a`, `pais_b`, `estado` y `tipo_acuerdo`
- `GET /v1/internacional/convenios/{codigo}` — detalle de un convenio DTA
- `GET /v1/internacional/convenios/retenciones` — listado de reglas de retencion por tipo de renta y pais
- `GET /v1/internacional/convenios/retenciones/{codigo}` — detalle de una regla de retencion
- `POST /v1/internacional/convenios/retencion` — calculo cruzado de retencion aplicable segun pais de residencia, tipo de renta y convenio DTA vigente

Uso recomendado:

- usa `convenios` para explorar cobertura efectiva por pais en la instancia actual
- usa `retenciones` para inspeccionar la regla base por tipo de renta
- usa `retencion` cuando necesites la respuesta operativa final con `tipo_retencion_aplicable`, `tiene_convenio_dta`, `codigo_convenio` y `formulario_recomendado`
````

- [ ] **Step 3: Add the DTA coverage warning to the limits chapter**

Append this paragraph to `docs/manual-usuario/05-limites-alcance-y-estado-actual.md` before `## Regla sobre cobertura`:

````md
En internacional y convenios DTA, la existencia de seeds o fixtures en el repo no garantiza por si sola que todos esos convenios esten cargados o validados en una instancia concreta. La cobertura operativa debe inferirse del contrato HTTP expuesto por la API y del dataset realmente sembrado en el entorno objetivo; por eso el manual documenta ejemplos verificados, no una matriz exhaustiva de paises.
````

- [ ] **Step 4: Run the DTA router tests before and after the doc update review**

Run:

```bash
python -m pytest apps/api/tests/test_dta_convenios.py -q
```

Expected:

- `18 passed` or the current full-green count for that file

### Task 6: Reconcile any active factual contradiction in the roadmap

**Files:**
- Modify if needed: `docs/master-execution-roadmap.md`

- [ ] **Step 1: Check whether the active roadmap still claims the old DTA fixture set as current truth**

Review this exact range:

```text
docs/master-execution-roadmap.md:2328-2335
```

Expected decision rule:

- if the roadmap text still states a fixture set that no longer matches `apps/api/tests/conftest.py`, edit it to describe the current verified examples conservatively
- if the text is already acceptable as historical evidence and not active truth, leave it untouched

- [ ] **Step 2: If a correction is needed, replace the contradictory fixture sentence with this wording**

Use this replacement sentence only if the current roadmap is factually wrong as active documentation:

````md
- Fixture DB en `conftest.py` con tablas `irs_dta_convention` y `irs_withholding_rule` y ejemplos verificados de convenios/reglas para pruebas del router DTA; la cobertura exacta depende del fixture actual y no debe inferirse solo desde snapshots historicos del roadmap.
````

- [ ] **Step 3: Re-read the manual and roadmap together for contradiction**

Check manually:

- `docs/manual-usuario/06-api-y-ejemplos.md`
- `docs/manual-usuario/09-referencia-de-endpoints.md`
- `docs/manual-usuario/05-limites-alcance-y-estado-actual.md`
- `docs/master-execution-roadmap.md`

Expected:

- no active document promises exhaustive DTA country coverage that is not verified

### Task 7: Verify locally and then verify the VPS with fresh evidence

**Files:**
- Verify: `infra/deploy/systemd/esdata-job@.service`
- Verify: `infra/observability/alerts.yml`
- Verify: `scripts/ops/worker_scheduler_guard.py`
- Verify: DTA manual docs

- [ ] **Step 1: Run the local validation bundle**

Run:

```bash
python -m pytest scripts/tests/test_worker_scheduler_guard.py apps/api/tests/test_status_contract.py apps/api/tests/test_dta_convenios.py -v --tb=short
ruff check scripts/ops/worker_scheduler_guard.py scripts/tests/test_worker_scheduler_guard.py apps/api/tests/test_status_contract.py
docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config
```

Expected:

- targeted tests pass
- `ruff` is clean on the changed Python files
- Compose config resolves without errors

- [ ] **Step 2: Sync the fixed runtime files and guard script to the VPS checkout**

Run:

```bash
scp infra/deploy/systemd/esdata-job@.service steamcases-vps:/srv/esdata/infra/deploy/systemd/esdata-job@.service
scp infra/observability/alerts.yml steamcases-vps:/srv/esdata/infra/observability/alerts.yml
scp scripts/ops/worker_scheduler_guard.py steamcases-vps:/srv/esdata/scripts/ops/worker_scheduler_guard.py
```

Expected:

- all three `scp` commands complete without errors

- [ ] **Step 3: Run the guard in check mode on the VPS before any runtime action**

Run:

```bash
ssh steamcases-vps 'cd /srv/esdata && python3 scripts/ops/worker_scheduler_guard.py check --repo-root /srv/esdata --installed-unit /etc/systemd/system/esdata-job@.service'
```

Expected:

- output includes `WorkerSilent uses stale gauge: True`
- output includes `Installed unit has --no-deps: False` once the installed unit is already corrected

- [ ] **Step 4: If the installed unit still drifts, apply the printed fix and verify systemd**

Run:

```bash
ssh steamcases-vps 'sudo install -m 0644 /srv/esdata/infra/deploy/systemd/esdata-job@.service /etc/systemd/system/esdata-job@.service && sudo systemctl daemon-reload && systemctl cat esdata-job@.service'
```

Expected:

- `ExecStart=` shows `--env-file /etc/esdata/esdata.env ... run --rm %i`
- no `--no-deps` appears in the installed unit

- [ ] **Step 5: Recreate Prometheus, refresh `/status`, and verify no stale false positives remain**

Run:

```bash
ssh steamcases-vps 'bash -s' <<'REMOTE'
set -euo pipefail
cd /srv/esdata
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml up -d prometheus
API_KEY=$(grep '^ESDATA_API_KEY=' /etc/esdata/esdata.env | cut -d= -f2-)
curl -fsS -H "X-API-Key: $API_KEY" http://127.0.0.1:8000/status >/tmp/esdata-status.json
curl -fsS http://127.0.0.1:8000/metrics >/tmp/esdata-metrics.txt
docker ps --format 'table {{.Names}}\t{{.Status}}'
REMOTE
```

Expected:

- `deploy-prometheus-1` is back `Up`
- `/metrics` reflects fresh `worker_stale_status` values

- [ ] **Step 6: If needed, run the explicit weekly reruns and validate each one**

Run only if the incident still requires reruns:

```bash
ssh steamcases-vps 'cd /srv/esdata && python3 scripts/ops/worker_scheduler_guard.py rerun cron-dgt-weekly cron-teac-weekly cron-bdns-weekly cron-borme-weekly cron-bde-weekly cron-cendoj-weekly cron-aepd-weekly cron-eurlex-weekly'
```

Then execute the printed commands one worker at a time and verify after each worker:

```bash
ssh steamcases-vps 'systemctl show esdata-job@cron-dgt-weekly.service -p Result -p ExecMainStatus -p ActiveState -p SubState'
ssh steamcases-vps 'journalctl -u esdata-job@cron-dgt-weekly.service -n 80 --no-pager'
ssh steamcases-vps "docker exec deploy-postgres-1 psql -U esdata -d esdata -P pager=off -c \"SELECT worker, status, started_at, finished_at, errors FROM sync_log WHERE worker = 'cron-dgt-weekly' ORDER BY started_at DESC LIMIT 1;\""
```

Expected for each rerun:

- `Result=success`
- `ExecMainStatus=0`
- no new `not connected to the network deploy_esdata-internal`
- a fresh `sync_log` row exists for that worker

- [ ] **Step 7: Close with one fresh cross-check on the VPS**

Run:

```bash
ssh steamcases-vps "curl -fsS http://127.0.0.1:8000/metrics | egrep 'worker_(stale_status|lag_seconds)\{'"
ssh steamcases-vps "systemctl list-timers --all 'esdata-*'"
```

Expected:

- weekly `cron-*` workers show `worker_stale_status ... 0.0` when healthy
- timers remain enabled and scheduled as expected

## Self-Review Checklist

- Spec coverage:
  - scheduler contract: Task 2 and Task 7
  - observability contract: Task 2 and Task 7
  - guided remediation script: Task 3 and Task 7
  - DTA docs: Task 5
  - roadmap reconciliation if needed: Task 6
- Placeholder scan:
  - no `TODO`, `TBD` or unnamed files remain
  - script and test file paths are exact
- Type consistency:
  - helper names in tests match `worker_scheduler_guard.py`
  - DTA field names in docs match `IrsFiscalCheckResponse` and router names

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-06-worker-scheduler-observability.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
