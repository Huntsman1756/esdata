# MCP Fase 5.5 Secrets Outside Repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the active deploy runtime secret file outside the repository checkout and align deploy/runtime docs with that contract.

**Architecture:** Keep `infra/deploy/compose.env.example` as the only versioned template for the active Compose deploy, leave `.env.example` only as a broader repo inventory without deploy authority, switch the canonical runtime env path to `/etc/esdata/esdata.env`, remove the last Compose-level repo-local env-file dependency from `worker-aeat`, and protect the contract with one focused deploy regression suite.

**Tech Stack:** Docker Compose, Bash, systemd unit files, Python 3.12, pytest, Markdown

---

## File Map

- Modify: `scripts/tests/test_deploy_hetzner.py`
  Add regressions that require an external env-file path outside the repo and forbid `.env.prod` / `env_file:` in the active deploy path.
- Modify: `scripts/ops/deploy-hetzner.sh`
  Change the default `ENV_FILE` to `/etc/esdata/esdata.env`.
- Modify: `scripts/ops/backup-postgres.sh`
  Change the default `ENV_FILE` to `/etc/esdata/esdata.env`.
- Modify: `infra/deploy/systemd/esdata-job@.service`
  Point the service to `/etc/esdata/esdata.env`.
- Modify: `infra/deploy/docker-compose.prod.yml`
  Remove the repo-local `env_file` from `worker-aeat` and declare explicit runtime env vars instead.
- Modify: `infra/deploy/compose.env.example`
  Update the template comment so operators copy it to `/etc/esdata/esdata.env`.
- Modify: `docs/deployment/server-installation.md`
  Update the canonical install/deploy instructions to use the external host env-file path.
- Modify: `docs/operations/runbooks/deploy-compose.md`
  Update the canonical runbook to the external host env-file path.
- Modify: `docs/operations/runbooks/backup-restore.md`
  Update backup/restore instructions and examples to the external host env-file path.
- Modify: `docs/operations/README.md`
  Update quick operational commands to the external host env-file path.
- Modify: `docs/operations/OPERATIONS.md`
  Update operational commands and backup examples to the external host env-file path.
- Modify: `docs/operations/LOGGING.md`
  Update logging commands to the external host env-file path.
- Modify: `docs/operations/runbooks/worker-aeat.md`
  Update the AEAT runbook to the external host env-file path.
- Modify: `docs/environment-variables.md`
  Document `/etc/esdata/esdata.env` as the active runtime env-file location.
- Modify: `docs/deployment/vps-trial-deploy.md`
  Update the VPS trial deploy instructions to the external host env-file path.
- Modify: `docs/integrations/opencode-local-and-vps.md`
  Update the Compose example to the external host env-file path.
- Modify: `docs/reference/mcp-remediation-plan.md`
  Refine the `5.5` target file description away from the repo-local path.
- Modify: `docs/master-execution-roadmap.md`
  Close `5.5` with fresh evidence.
- Modify: `docs/operations/agent-notes.md`
  Record the reusable invariant about keeping the runtime env-file outside the checkout.

## Task 1: Add and verify the failing deploy regressions

**Files:**
- Modify: `scripts/tests/test_deploy_hetzner.py`

- [ ] **Step 1: Add a regression for the external env-file contract**

```python
EXPECTED_EXTERNAL_ENV_FILE = "/etc/esdata/esdata.env"


def test_canonical_deploy_uses_external_env_file_outside_repo_checkout():
    ...
    assert EXPECTED_EXTERNAL_ENV_FILE in script
    assert EXPECTED_EXTERNAL_ENV_FILE in backup_script
    assert EXPECTED_EXTERNAL_ENV_FILE in systemd_service
    assert "infra/deploy/.env.prod" not in server_doc
    assert "infra/deploy/.env.prod" not in runbook


def test_compose_profiled_worker_does_not_depend_on_repo_local_env_file():
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert ".env.prod" not in compose
    assert "env_file:" not in compose
```

- [ ] **Step 2: Run the focused regression and verify red**

Run: `python -m pytest scripts/tests/test_deploy_hetzner.py -q`

Expected: FAIL because the current deploy script/default docs still point at `infra/deploy/.env.prod` and `worker-aeat` still contains `env_file: [.env.prod]`.

## Task 2: Align the active deploy path with the external env-file contract

**Files:**
- Modify: `scripts/ops/deploy-hetzner.sh`
- Modify: `scripts/ops/backup-postgres.sh`
- Modify: `infra/deploy/systemd/esdata-job@.service`
- Modify: `infra/deploy/docker-compose.prod.yml`
- Modify: `infra/deploy/compose.env.example`

- [ ] **Step 1: Switch deploy script defaults to the external host env-file**

```bash
ENV_FILE="${ENV_FILE:-/etc/esdata/esdata.env}"
```

Apply that default in both `scripts/ops/deploy-hetzner.sh` and `scripts/ops/backup-postgres.sh`.

- [ ] **Step 2: Switch the systemd unit to the external host env-file**

```ini
ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env -f /opt/esdata/infra/deploy/docker-compose.prod.yml run --rm %i
```

- [ ] **Step 3: Remove the repo-local Compose `env_file` dependency from `worker-aeat`**

Replace the `worker-aeat` block so it follows the same explicit env wiring pattern as `worker-modelos`:

```yaml
  worker-aeat:
    build:
      context: ../..
      dockerfile: apps/workers/Dockerfile.aeat
    profiles: ["aeat"]
    restart: "no"
    environment:
      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is required}
      AEAT_MODELS_SYNC_INTERVAL: ${MODELOS_SYNC_INTERVAL:-86400}
      WORKER_NAME: worker-aeat-modelos
      WORKER_CMD: python aeat_models.py --run-once
      WORKER_REQUEST_DELAY: ${WORKER_REQUEST_DELAY:-1.0}
      PYTHONUNBUFFERED: "1"
```

- [ ] **Step 4: Update the template comment to the new host path**

```dotenv
# Copy this template to `/etc/esdata/esdata.env` on the host for deployment.
```

## Task 3: Sync active docs to the external env-file contract

**Files:**
- Modify: `docs/deployment/server-installation.md`
- Modify: `docs/operations/runbooks/deploy-compose.md`
- Modify: `docs/operations/runbooks/backup-restore.md`
- Modify: `docs/operations/README.md`
- Modify: `docs/operations/OPERATIONS.md`
- Modify: `docs/operations/LOGGING.md`
- Modify: `docs/operations/runbooks/worker-aeat.md`
- Modify: `docs/environment-variables.md`
- Modify: `docs/deployment/vps-trial-deploy.md`
- Modify: `docs/integrations/opencode-local-and-vps.md`
- Modify: `docs/reference/mcp-remediation-plan.md`

- [ ] **Step 1: Update the install/deploy guides**

Make `docs/deployment/server-installation.md` and `docs/operations/runbooks/deploy-compose.md` say the active host path is `/etc/esdata/esdata.env`, created from `infra/deploy/compose.env.example` with `chmod 600`, and update all command examples to `--env-file /etc/esdata/esdata.env`.

- [ ] **Step 2: Update operational docs and runbooks**

Change all active operational examples in `docs/operations/README.md`, `docs/operations/OPERATIONS.md`, `docs/operations/LOGGING.md`, `docs/operations/runbooks/backup-restore.md`, and `docs/operations/runbooks/worker-aeat.md` to the same `--env-file /etc/esdata/esdata.env` contract.

- [ ] **Step 3: Update supporting docs**

Update `docs/environment-variables.md`, `docs/deployment/vps-trial-deploy.md`, `docs/integrations/opencode-local-and-vps.md`, and `docs/reference/mcp-remediation-plan.md` so they reference the external host env-file instead of `infra/deploy/.env.prod`.

## Task 4: Verify green and close the phase

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Re-run the focused deploy regression**

Run: `python -m pytest scripts/tests/test_deploy_hetzner.py -q`

Expected: PASS.

- [ ] **Step 2: Re-run the deploy/runtime consistency checks**

Run: `python -m pytest scripts/tests/test_compose_env_example.py -q`

Expected: PASS.

Run: `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config`

Expected: command succeeds when provided a real host env-file.

Run: `docker compose --env-file infra/deploy/compose.env.example -f infra/deploy/docker-compose.prod.yml config`

Expected: PASS, proving the versioned template still resolves the active runtime contract.

Run: `bash -n "scripts/ops/deploy-hetzner.sh"`

Expected: no syntax errors.

- [ ] **Step 3: Close `5.5` in the roadmap and add the reusable note**

Add a `5.5 [COMPLETA]` historical note in `docs/master-execution-roadmap.md` with the fresh evidence above and update the live summary to the next exact step. Record the reusable invariant in `docs/operations/agent-notes.md` that real deploy env files belong outside the checkout.
