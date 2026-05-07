# Diseno - Fase 5.4 worker set alignment

## Objetivo

Alinear el worker set que arranca el deploy canonico con el scope real del runtime Compose activo.

## Problema confirmado

- `infra/deploy/docker-compose.prod.yml` define 12 servicios `worker-*` continuos sin `profiles`.
- `scripts/ops/deploy-hetzner.sh` solo levanta 8 workers en su `up -d --build --remove-orphans ...` final.
- `docs/deployment/server-installation.md` y `docs/operations/runbooks/deploy-compose.md` siguen documentando ese set incompleto.

Workers continuos definidos hoy por Compose:

- `worker-boe`
- `worker-dgt`
- `worker-teac`
- `worker-modelos`
- `worker-bdns`
- `worker-borme`
- `worker-cnmv`
- `worker-sepblac`
- `worker-cendoj`
- `worker-eurlex`
- `worker-bde`
- `worker-aepd`

## Decision

- La fuente de verdad para `5.4` es `infra/deploy/docker-compose.prod.yml`.
- El worker set canonico del deploy son todos los servicios `worker-*` continuos del Compose activo, excluyendo servicios profile-gated como `worker-aeat`.
- `scripts/ops/deploy-hetzner.sh` y los runbooks activos deben arrancar exactamente ese set, no una seleccion historica parcial.

## Fuera de scope

- Anadir o quitar servicios del Compose activo.
- Redisenar el set de `cron-*` o los timers `systemd` versionados.
- Corregir expectativas de `/status` o surfaces API fuera del worker set de deploy.

## Aceptacion

- Existe una regresion que compara el worker set continuo de `docker-compose.prod.yml` con el deploy canonico y los runbooks activos.
- `scripts/ops/deploy-hetzner.sh` arranca todos los workers continuos del scope real.
- `docs/deployment/server-installation.md` y `docs/operations/runbooks/deploy-compose.md` dejan explicito el mismo set.
- La verificacion minima cierra en verde con evidencia fresca.
