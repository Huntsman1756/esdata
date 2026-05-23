# Documentacion

## Objetivo

Mantener una unica capa de documentacion viva, coherente con el codigo y lista para handoff operativo.

## Fuentes vivas

- `master-execution-roadmap.md` — estado activo y siguiente paso exacto
- `deployment/overview.md` — estrategia de despliegue
- `deployment/server-installation.md` — instalacion y bootstrap
- `deployment/rollback.md` — rollback
- `INSTALLATION.md` — instalacion y arranque rapido para handoff
- `COMPLIANCE.md` — estado de cumplimiento real y gaps conocidos
- `environment-variables.md` — contrato de variables
- `database.md` — bootstrap y operacion DB
- `operations/README.md` — indice operativo
- `operations/OPERATIONS.md` — operacion diaria
- `operations/runbooks/` — runbooks repetibles
- `integrations/README.md` — matriz activa de integraciones LLM/clientes
- `manual-usuario/README.md` — manual vivo de uso e integracion
- `fiscal-regulatory-coverage-matrix.md` — matriz de cobertura fiscal-regulatoria por dominio y subdominio
- `aeat-priority-model-closeout.md` — cierre auditable de modelos AEAT prioritarios por estado
- `cdi-coverage-prd.md` — PRD para cerrar CDI como familia fiscal propia por pais, articulo y tipo de renta
- `doctrina-coverage-prd.md` — PRD para cerrar DGT/TEAC como familia de lineas de criterio fiscal con evidencia y fail-closed
- `doctrina-production-audit-20260521.md` — auditoria productiva DGT/TEAC y lote piloto de lineas de criterio
- `doctrina-operational-coverage-matrix.md` — matriz operativa viva de lineas D-01..D-09, relaciones persistidas, gaps y siguiente accion
- `reference/model-expansion-spec.md` — guia para nuevos modelos, leyes y organismos
- `reference/v1-feature-inventory.md` — inventario activo de features, superficies y gaps para v1.0
- `reference/mcp-remediation-plan.md` — plan activo para endurecer trazabilidad, grounding y completitud del MCP
- `reference/mcp-2026-07-28-compatibility-audit.md` — auditoria de compatibilidad dual MCP `2025-03-26` / `2026-07-28` sin romper `/mcp` legacy
- `reference/mcp-official-conformance-baseline-20260523.md` — baseline ejecutado contra la suite oficial `@modelcontextprotocol/conformance`; MCP legacy parcialmente conforme, no optimo oficial
- `reference/source-compliance-register.md` — restricciones de scraping, licencias y validacion real por fuente
- `repository-structure.md` — mapa del repo

## Historico

Todo material de Railway, snapshots de sesion, handoffs antiguos, postmortems y planes cerrados debe vivir en `docs/archive/` o tratarse como historico.

## Regla practica

Si una referencia no existe, no es activa o contradice el roadmap, no debe aparecer en este indice.
