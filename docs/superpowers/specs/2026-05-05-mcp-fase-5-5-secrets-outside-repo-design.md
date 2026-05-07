# Diseno - Fase 5.5 secretos fuera del repo

## Objetivo

Sacar el fichero runtime secreto del deploy activo fuera del checkout del repo y alinear scripts, Compose y docs operativas con ese contrato sin tocar valores sensibles reales.

## Problema confirmado

- Git ya ignora `.env.*` y no existe `infra/deploy/.env.prod` trackeado en el worktree.
- Aun asi, el deploy canonico y varios runbooks activos siguen tratando `infra/deploy/.env.prod` como path operativo normal.
- `scripts/ops/deploy-hetzner.sh`, `scripts/ops/backup-postgres.sh` y `infra/deploy/systemd/esdata-job@.service` apuntan al fichero repo-local.
- `docs/deployment/server-installation.md`, `docs/operations/runbooks/deploy-compose.md`, `docs/operations/runbooks/backup-restore.md`, `docs/operations/README.md`, `docs/operations/OPERATIONS.md`, `docs/operations/LOGGING.md`, `docs/operations/runbooks/worker-aeat.md`, `docs/deployment/vps-trial-deploy.md` y `docs/integrations/opencode-local-and-vps.md` refuerzan la misma convencion.
- `infra/deploy/docker-compose.prod.yml` mantiene una fuga adicional: `worker-aeat` profile-gated carga `env_file: [.env.prod]`, lo que reintroduce dependencia a un secreto repo-adjacent incluso si el resto del deploy ya usa `--env-file` externo.

## Decision

- El runtime secreto del deploy Compose activo pasa a vivir en `/etc/esdata/esdata.env`.
- El repo mantiene `infra/deploy/compose.env.example` como plantilla autoritativa del deploy activo y puede conservar `.env.example` solo como inventario amplio sin autoridad operativa sobre ese deploy.
- Los scripts y unidades operativas pueden aceptar override via `ENV_FILE`, pero el default canonico debe ser `/etc/esdata/esdata.env`.
- `worker-aeat` no debe depender de `env_file` repo-local; debe declarar explicitamente las mismas env vars runtime que necesita desde el entorno Compose ya cargado.

## Alcance aprobado

Incluye:

- actualizar defaults de `scripts/ops/deploy-hetzner.sh` y `scripts/ops/backup-postgres.sh`
- actualizar `infra/deploy/systemd/esdata-job@.service`
- eliminar `env_file: [.env.prod]` de `worker-aeat` y declarar sus env vars necesarias
- alinear docs operativas activas con `/etc/esdata/esdata.env`
- anadir regresiones pequenas que fijen el path externo y eviten reintroducir `.env.prod` repo-local en deploy/Compose
- actualizar roadmap y `docs/operations/agent-notes.md`

No incluye:

- leer, mover o exponer secretos reales del host
- rotar credenciales productivas reales en esta sesion
- introducir un gestor de secretos nuevo
- cambiar el boundary de variables runtime definido en `5.3`

## Aceptacion

- `scripts/tests/test_deploy_hetzner.py` falla en rojo antes del cambio y queda verde despues.
- `scripts/ops/deploy-hetzner.sh`, `scripts/ops/backup-postgres.sh` y `infra/deploy/systemd/esdata-job@.service` usan `/etc/esdata/esdata.env` por defecto.
- `infra/deploy/docker-compose.prod.yml` ya no contiene `env_file` ni `.env.prod` y `worker-aeat` sigue recibiendo las env vars necesarias via `${...}`.
- Las docs activas dejan de instruir a operadores a guardar secretos reales dentro de `/opt/esdata`.
- La verificacion minima cierra con evidencia fresca y sin exponer valores sensibles.
