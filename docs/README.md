# Documentacion

## Punto de entrada

- Estado vivo, fase actual y siguiente paso: `master-execution-roadmap.md`
- Reglas globales del repo: `../AGENTS.md`
- Reglas documentales locales: `AGENTS.md`
- Manual funcional vivo: `manual-usuario/README.md`

## Estructura oficial

- `master-execution-roadmap.md` — unica fuente activa de estado y ejecucion
- `manual-usuario/` — manual vivo para usuarios, operadores e integradores
- `architecture/` — arquitectura, boundaries y mapas tecnicos permanentes
- `operations/` — runbooks y operacion del sistema
- `deployment/` — despliegue, instalacion y rollback
- `adr/` — decisiones estructurales permanentes
- `reference/` — material de referencia estable y artefactos tecnicos reutilizables
- `archive/` — historicos, snapshots, planes cerrados y handoffs
- `superpowers/` — specs y planes de trabajo generados por skills

## Documentacion activa hoy

- `master-execution-roadmap.md`
- `manual-usuario/README.md`
- `architecture.md`
- `repository-structure.md`
- `environment-variables.md`
- `database.md`
- `deployment/overview.md`
- `deployment/server-installation.md`
- `deployment/rollback.md`
- `operations/README.md`
- `operations/agent-notes.md`
- `REMEDIATION.md`
- `POLICY_PATCHES.md`
- `operations/bootstrap-hardening-checklist.md`

## Referencia estable

- `controlled-vocabulary-regulatorio.md`
- `license-and-sourcing-policy.md`
- `ownership-mapping.md`
- `reference-map.md`
- `sociedad-valores-scope.md`
- `modelos-onboarding.md`
- `openapi-gpt.json`
- `openapi-gpt-3.0.json`
- `openapi-gpt-minimal-modelos.json`
- `openapi-gpt-clipboard.json`

## Archivo historico

No usar estos documentos como fuente activa del estado actual. Si se consultan, debe ser por necesidad puntual de contexto o auditoria.

- `archive/handoffs/`
- `archive/status/`
- `archive/plans/`
- `archive/infra/`
- `archive/postmortems/`

## Reglas

- Ningun documento historico compite con `master-execution-roadmap.md`.
- `README.md` del repo no guarda estado vivo.
- El manual explica capacidades y uso; el roadmap explica ejecucion y siguiente paso.
- Si un documento deja de ser activo pero sigue siendo util, se mueve a `archive/` y se marca como historico.
