# Casos de uso por perfil

## Analista o investigador regulatorio

Objetivo tipico:

- localizar una norma o articulo aplicable
- revisar doctrina relacionada
- ver la trazabilidad a fuente oficial

Recorrido recomendado:

1. `buscar` o UI de busqueda
2. detalle de articulo
3. detalle de doctrina si aplica
4. contraste con modelos u obligaciones relacionadas

Superficies recomendadas:

- UI web
- `API`

## Responsable de compliance interno

Objetivo tipico:

- ver obligaciones aplicables
- revisar cambios regulatorios
- consultar workflow de seguimiento

Recorrido recomendado:

1. `GET /v1/obligaciones/aplicables`
2. `GET /v1/cambios`
3. `GET /v1/compliance/workflow`
4. detalle de obligacion concreta si hace falta evidencia

Superficies recomendadas:

- UI administrativa
- `API`

## Integrador backend

Objetivo tipico:

- consumir datos estructurados desde otra aplicacion o servicio

Recorrido recomendado:

1. leer `03-superficies-disponibles.md`
2. usar `06-api-y-ejemplos.md`
3. modelar integracion a partir de OpenAPI
4. verificar salud y estado antes de automatizar procesos criticos

Superficie recomendada:

- `API`

## Usuario de agentes o LLMs

Objetivo tipico:

- consultar normativa y obligaciones desde un cliente MCP o un agente local

Recorrido recomendado:

1. revisar `07-mcp-y-clientes.md`
2. decidir entre MCP HTTP o `stdio`
3. si el cliente usa `stdio`, usar herramientas como `consulta_fiscal` o `listar_obligaciones_aplicables`
4. si el cliente usa `HTTP MCP`, usar las operaciones estructuradas expuestas en `/mcp`

Superficie recomendada:

- `MCP`

## Operador tecnico

Objetivo tipico:

- levantar stack
- ejecutar migraciones
- lanzar workers
- diagnosticar incidencias

Recorrido recomendado:

1. `04-operacion-tecnica.md`
2. `08-faq-y-troubleshooting.md`
3. `docs/operations/README.md`

Superficies recomendadas:

- Docker Compose
- runbooks

## Usuario que solo quiere una consulta rapida

Objetivo tipico:

- buscar una referencia, un modelo o un articulo sin entrar en integraciones

Recorrido recomendado:

1. abrir la home
2. lanzar consulta o usar `/buscar`
3. abrir detalle de articulo, doctrina o modelo segun el resultado

Superficie recomendada:

- UI web
