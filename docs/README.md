# Documentación

## Objetivo

Separar claramente la documentación permanente de los snapshots de sesión e informes puntuales.

## Documentación permanente

- `architecture.md`
- `repository-structure.md`
- `environment-variables.md`
- `database.md`
- `infrastructure-handoff.md`
- `professionalization-roadmap.md`
- `deployment/overview.md`
- `deployment/server-installation.md`
- `deployment/rollback.md`
- `operations/README.md`
- `operations/runbooks/`

## Artefactos operativos auxiliares

- `openapi-gpt.json`
- `openapi-gpt-3.0.json`
- `deploy-commands.md`

## Snapshots y documentos históricos

Estos archivos siguen siendo útiles como contexto, pero no deben tomarse como fuente principal del estado actual del sistema:

- `next-session-handoff-2026-04-12.md`
- `session-status-2026-04-13.md`
- `production-status-2026-04-11.md`
- `production-status-2026-04-12.md`
- `postmortem-sprint-2.md`
- `dgt-mvp-implementation-plan.md`

## Regla práctica

Si un documento describe cómo está construido u operado hoy el sistema, debe vivir en la documentación permanente.
Si describe una sesión, un estado puntual o una entrega concreta, debe tratarse como histórico.
