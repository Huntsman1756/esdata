# Superficies disponibles

## Principio general

`esdata` expone capacidades por superficies backend. La logica de negocio y el acceso a datos viven en servidor.

## API

La `API` es la superficie principal para integraciones backend y consultas estructuradas.

Puntos de entrada relevantes segun el codigo actual:

- `/health`
- `/status`
- `/metrics` si el soporte Prometheus esta disponible
- `/openapi.json`

Dominios y prefijos relevantes montados en la API:

- `/v1/buscar`
- `/v1/legislacion`
- `/v1/materias`
- `/v1/doctrina`
- `/v1/modelos`
- `/v1/cambios`
- `/v1/compliance`
- `/v1/cnmv`
- `/v1/obligaciones`
- `/v1/empresas`
- `/v1/entidades`
- `/v1/cendoj`
- `/v1/eurlex`
- `/v1/bde`
- `/v1/aepd`
- `/v1/pgc`
- `/v1/screening`
- `/v1/xbrl`
- `/v1/banking`
- `/v1/domain-availability`
- `/v1/sources`
- `/v1/observability`
- `/v1/ai/audit-log`
- `/v1/ai/human-review`
- `/v1/ai/models`
- `/v1/data`

Nota de estado: existen routers definidos en codigo para `/v1/bdns`, `/v1/borme`,
`/v1/sepblac`, `/v1/chunks`, `/v1/connectivity`, AI risk/fairness, GDPR y XAI,
pero no estan montados en `apps/api/main.py` en la superficie activa v1.0. No
deben documentarse como disponibles hasta cablearlos, probarlos y exponerlos en
OpenAPI/MCP.

Algunos endpoints funcionales especialmente importantes hoy:

- `GET /v1/compliance/workflow`
- `GET /v1/cambios`
- `GET /v1/obligaciones`
- `GET /v1/obligaciones/aplicables`
- `GET /v1/obligaciones/operativas`
- `GET /v1/obligaciones/deadlines`
- `GET /v1/entidades/lei/{lei}`
- `GET /v1/entidades/buscar`
- `POST /v1/screening/`
- `GET /v1/screening/entries`
- `GET /v1/screening/matches/{empresa_id}`
- `GET /v1/pgc/cuentas`
- `GET /v1/pgc/buscar`
- `GET /v1/pgc/normas-valoracion`
- `GET /v1/pgc/estados-financieros`
- `GET /v1/pgc/referencias-fiscales`
- `GET /v1/pgc/referencias-aeat`

### Reporting estructurado

- `GET /v1/xbrl/facts`
- estado actual: slice MVP fixture-first con XBRL local persistido; no incluye detalle de filing, iXBRL remoto ni taxonomias completas

### Bancario utilitario (Fase 17)

- `POST /v1/banking/iban/validate`
- `GET /v1/banking/iban/countries`
- estado actual: validacion IBAN stateless (formato + mod-97 + longitud por pais); sin persistencia en DB

Consultar tambien:

- `../openapi-gpt.json`
- `../openapi-gpt-3.0.json`
- `../openapi-gpt-minimal-modelos.json`
- `../environment-variables.md`

## MCP

`MCP` se trata como superficie principal para uso personal con `OpenCode` y modelos LLM locales.

En el estado actual, el endpoint HTTP MCP se monta en `/mcp`.

La exposicion HTTP del MCP esta protegida por un guard especifico y rate limiting para esa ruta.

Ademas existe una implementacion `stdio` en `apps/api/mcp_stdio.py` y un modulo de catalogo MCP en `apps/api/mcp_catalog.py` que hoy separa explicitamente la superficie HTTP de la superficie stdio.

Regla importante:

- `HTTP MCP` y `stdio` no comparten el mismo catalogo funcional
- `HTTP MCP` expone operaciones REST estructuradas del backend
- `stdio` expone tools de alto nivel como `consulta_fiscal` y `agente_consulta`

Herramientas MCP compartidas relevantes hoy:

- HTTP MCP: operaciones de legislacion, doctrina, materias y modelos AEAT definidas en `HTTP_MCP_OPERATIONS`
- stdio MCP: `consulta_fiscal`, `listar_obligaciones_operativas`, `listar_obligaciones_aplicables`, `listar_deadlines`, `get_obligacion_completa`, `agente_consulta`, `agente_monitoreo_status`, `agente_compliance_resumen`

Regla permanente del repo:

- `MCP` personal se documenta separado de `ChatGPT Business` via `OpenAPI/Actions`
- no mezclar ambos flujos en una misma guia salvo comparacion explicita

## UI interna

El repositorio contempla UI interna minima para ciertos workflows. La UI no sustituye la capa backend ni debe contener logica de negocio o acceso directo a DB.

Pantallas visibles en el repo actual:

- home de consulta
- buscador con resultados de legislacion y doctrina
- detalle de articulo
- detalle de doctrina
- detalle de modelo AEAT
- admin de cambios
- admin de workflow

## Artefactos tecnicos relacionados

- `../architecture.md`
- `../database.md`
- `../repository-structure.md`
- `../operations/README.md`

## Regla de evolucion

Cuando se anada una nueva superficie de uso o cambie el contrato de una ya existente, este capitulo debe actualizarse en la misma tarea.
