# MCP Fase 5.3 Env Runtime Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align `infra/deploy/docker-compose.prod.yml`, `infra/deploy/compose.env.example`, and `docs/environment-variables.md` so operators can distinguish the active Compose runtime variables from code-only or legacy variables without ambiguity.

**Architecture:** Treat `docker-compose.prod.yml` as the source of truth for active runtime variables, keep `compose.env.example` scoped to the active Compose deployment template, and update `docs/environment-variables.md` into a global inventory with explicit per-variable status (`runtime deploy`, `code-only`, `legacy/no cableada`). Use one focused regression test around the env example plus `docker compose config` as the main verification of operational consistency.

**Tech Stack:** Docker Compose, Python 3.12, pytest, Markdown

**Repo Note:** Do not commit or push as part of this plan unless the user explicitly asks.

---

## File Map

- Modify: `infra/deploy/compose.env.example`
  Remove variables that no longer belong to the active Compose deployment template and keep the file aligned with actual runtime inputs.
- Modify: `docs/environment-variables.md`
  Rework the variable inventory so each variable is clearly classified as `runtime deploy`, `code-only`, or `legacy/no cableada`.
- Reference and modify only on mismatch: `infra/deploy/docker-compose.prod.yml`
  Use this file as the runtime source of truth. Modify it only if Task 2 finds a real mismatch between the active runtime contract and the documented/templated variables.
- Create: `scripts/tests/test_compose_env_example.py`
  Add a focused regression around the env example to keep removed legacy variables out and assert key active runtime variables remain present.
- Modify: `docs/master-execution-roadmap.md`
  Close `5.3` with fresh evidence and point the live summary to `5.4` if the implementation is green.
- Modify: `docs/operations/agent-notes.md`
  Record the reusable invariant about classifying env vars by active wiring instead of mixing runtime and code-only settings.

### Task 1: Add a failing regression for the deploy env template boundary

**Files:**
- Create: `scripts/tests/test_compose_env_example.py`
- Reference: `infra/deploy/compose.env.example`
- Reference: `infra/deploy/docker-compose.prod.yml`
- Reference: `docs/superpowers/specs/2026-05-05-mcp-fase-5-3-env-runtime-alignment-design.md`

- [ ] **Step 1: Write the failing regression test file**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / "infra" / "deploy" / "compose.env.example"


def _parse_env_keys() -> set[str]:
    keys: set[str] = set()
    for raw_line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    return keys


def test_compose_env_example_keeps_active_runtime_keys_and_excludes_legacy_frontend_key():
    keys = _parse_env_keys()

    assert "DATABASE_URL" in keys
    assert "ESDATA_API_BASE_URL" in keys
    assert "MCP_API_KEY" in keys
    assert "HC_PING_URL_CRON_BDE_WEEKLY" in keys
    assert "NEXT_PUBLIC_API_BASE_URL" not in keys
```

- [ ] **Step 2: Run the focused regression to verify red**

Run: `python -m pytest scripts/tests/test_compose_env_example.py -q`

Expected: FAIL because `infra/deploy/compose.env.example` still contains `NEXT_PUBLIC_API_BASE_URL` even though the spec for `5.3` says that legacy/non-wired variable must be removed from the active Compose template.

- [ ] **Step 3: Optional commit, only if the user explicitly asks**

```bash
git add scripts/tests/test_compose_env_example.py
git commit -m "test: add compose env template boundary regression"
```

### Task 2: Align the active Compose env template and variable inventory

**Files:**
- Modify: `infra/deploy/compose.env.example`
- Modify: `docs/environment-variables.md`
- Reference and modify only on mismatch: `infra/deploy/docker-compose.prod.yml`
- Modify: `scripts/tests/test_compose_env_example.py`

- [ ] **Step 1: Remove legacy/non-wired variables from the active Compose template**

Edit `infra/deploy/compose.env.example` so it keeps only variables required or actually consumed by the active Compose deployment template. At minimum, remove:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Keep active runtime keys such as:

```dotenv
DATABASE_URL=postgresql+psycopg://esdata:change-me@postgres:5432/esdata
ESDATA_API_BASE_URL=http://api:8000
ESDATA_API_KEY=change-me-api-key
MCP_API_KEY=change-me-mcp-key
HC_PING_URL_CRON_BDE_WEEKLY=
```

- [ ] **Step 2: Only touch `docker-compose.prod.yml` if a real mismatch is found**

Apply a change to `infra/deploy/docker-compose.prod.yml` only if, during Task 2, you discover a variable that the file requires/defaults incorrectly relative to the intended active runtime contract. If no mismatch is found, leave the file unchanged and use it purely as the classification source of truth.

The only acceptable “no-op” result here is: no diff in `infra/deploy/docker-compose.prod.yml` because the file already matches the active runtime contract.

- [ ] **Step 3: Rework `docs/environment-variables.md` into a classified inventory**

Restructure the document so it explicitly separates at least these sections:

```md
## Fuente activa de runtime deploy

- `infra/deploy/docker-compose.prod.yml` define las variables del despliegue Compose activo.
- `infra/deploy/compose.env.example` es la plantilla de valores para ese runtime.

## Variables `runtime deploy`

| Variable | Requerida | Default | Estado | Uso |
|----------|-----------|---------|--------|-----|
| `DATABASE_URL` | Si | | `runtime deploy` | API + workers + crons + ops |
| `ESDATA_API_BASE_URL` | Si | | `runtime deploy` | Web SSR |
| `MCP_API_KEY` | Si fuera de test | | `runtime deploy` | API/MCP |

## Variables `code-only`

| Variable | Requerida | Default | Estado | Uso |
|----------|-----------|---------|--------|-----|
| `ESDATA_CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:8000` | `code-only` | API |
| `ESDATA_SENTRY_DSN` | No | | `code-only` | API/workers |

## Variables `legacy/no cableada`

| Variable | Estado | Nota |
|----------|--------|------|
| `NEXT_PUBLIC_API_BASE_URL` | `legacy/no cableada` | Retirada del runtime activo; no usar en deploy Compose |
```

Use `docker-compose.prod.yml` as the source for `runtime deploy`, and move any variables that exist only in code/tests or helper scripts into `code-only` or `legacy/no cableada` rather than leaving them mixed into the active runtime tables.

- [ ] **Step 4: Run the focused regression to verify green**

Run: `python -m pytest scripts/tests/test_compose_env_example.py -q`

Expected: PASS, proving the active Compose env template no longer carries `NEXT_PUBLIC_API_BASE_URL` while still keeping key active runtime variables.

- [ ] **Step 5: Validate the active Compose template against the compose file**

Run: `docker compose --env-file "infra/deploy/compose.env.example" -f "infra/deploy/docker-compose.prod.yml" config`

Expected: command succeeds without unresolved variable errors.

- [ ] **Step 6: Optional commit, only if the user explicitly asks**

```bash
git add infra/deploy/compose.env.example infra/deploy/docker-compose.prod.yml docs/environment-variables.md scripts/tests/test_compose_env_example.py
git commit -m "docs: align deploy env variables with runtime"
```

### Task 3: Close docs for Fase 5.3 with fresh evidence

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`
- Reference: `docs/superpowers/specs/2026-05-05-mcp-fase-5-3-env-runtime-alignment-design.md`

- [ ] **Step 1: Update the roadmap live summary to close `5.3` and point to `5.4`**

```md
- Objetivo actual: preparar **Fase 5.4** del plan MCP para alinear el worker set del deploy con el scope real.
- Estado actual: **Fase 5.3** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; **Fase 5.4** queda pendiente de confirmacion explicita del usuario antes de abrirse.
- Estado del agente activo: `5.3` cerrada con evidencia fresca; el deploy Compose activo, `compose.env.example` y `docs/environment-variables.md` ya diferencian variables `runtime deploy`, `code-only` y `legacy/no cableada`.
- Reclamo actual: `[SIN RECLAMO]` sin archivos reclamados tras el cierre de `5.3`.
- Siguiente paso exacto: pedir confirmacion del usuario para abrir **Fase 5.4** (`scripts/ops/deploy-hetzner.sh`, `infra/deploy/docker-compose.prod.yml`, `docs/deployment/server-installation.md`, `docs/operations/runbooks/deploy-compose.md`).
```

- [ ] **Step 2: Add the `5.3` historical note with exact evidence**

```md
- Nota 2026-05-05: Fase 5.3 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `infra/deploy/compose.env.example` queda alineado con el deploy Compose activo, `docs/environment-variables.md` pasa a clasificar las variables por estado real (`runtime deploy`, `code-only`, `legacy/no cableada`) y `NEXT_PUBLIC_API_BASE_URL` deja de aparecer como parte del runtime activo. Evidencia fresca del cierre: `python -m pytest scripts/tests/test_compose_env_example.py -q` -> `1 passed`; `docker compose --env-file infra/deploy/compose.env.example -f infra/deploy/docker-compose.prod.yml config` -> resuelve correctamente. Riesgo residual explicitado: el repo puede seguir conteniendo variables fuera del deploy activo usadas por scripts/tests locales; `5.3` las reclasifica, no las elimina del codigo.
```

- [ ] **Step 3: Add the reusable env-wiring note to `docs/operations/agent-notes.md`**

```md
### 2026-05-05 - Variables de entorno: separar runtime deploy de code-only y legacy

- Scope: `infra/deploy/docker-compose.prod.yml`, `infra/deploy/compose.env.example`, `docs/environment-variables.md`
- Hallazgo: mezclar en el mismo inventario variables del deploy activo, variables solo de codigo/tests y restos heredados crea falsos supuestos operativos y handoffs inseguros.
- Impacto: un operador puede creer que una variable no cableada forma parte del despliegue activo, o perder una variable realmente necesaria porque solo aparece escondida en Compose.
- Regla practica: tratar `docker-compose.prod.yml` como fuente de verdad del runtime activo; `compose.env.example` como plantilla solo de ese runtime; y la documentacion global de variables como inventario clasificado por estado real de cableado.
```

- [ ] **Step 4: Re-run the focused operational verification after docs updates**

Run: `docker compose --env-file "infra/deploy/compose.env.example" -f "infra/deploy/docker-compose.prod.yml" config`

Expected: command succeeds, confirming the roadmap closure note matches the final active template.

- [ ] **Step 5: Optional commit, only if the user explicitly asks**

```bash
git add docs/master-execution-roadmap.md docs/operations/agent-notes.md docs/superpowers/plans/2026-05-05-mcp-fase-5-3-env-runtime-alignment.md
git commit -m "docs: record env runtime alignment"
```
