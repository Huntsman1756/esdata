# MCP y clientes

## Que es MCP en esdata

`esdata` expone dos superficies `MCP` distintas para clientes compatibles con Model Context Protocol.

- `HTTP MCP`: se publica en `/mcp` y expone el catalogo HTTP definido en `apps/api/mcp_catalog.py` bajo `HTTP_MCP_OPERATIONS`
- `stdio MCP`: vive en `apps/api/mcp_stdio.py` y expone herramientas de mas alto nivel como `consulta_fiscal` y `agente_consulta`

No son dos transportes del mismo catalogo: `HTTP MCP` y `stdio MCP` no comparten ni catalogo ni semantica.

Eleccion rapida:

- usa `HTTP MCP` si tu cliente MCP consume endpoints HTTP y quieres trabajar con el catalogo HTTP publicado por `esdata`
- usa `stdio MCP` si tu cliente MCP lanza un proceso local y necesitas tools de mas alto nivel orientadas a agentes

## Recorrido HTTP MCP

El punto de entrada es:

```text
/mcp
```

Para un usuario, lo importante es:

- soporte de API key por cabecera `X-API-Key`
- expone la superficie MCP HTTP de `esdata`, correspondiente al catalogo HTTP anclado en `apps/api/mcp_catalog.py` bajo `HTTP_MCP_OPERATIONS`
- esta pensado para clientes MCP que hablan HTTP en lugar de lanzar un proceso local

En la practica, se usa desde un cliente compatible con MCP configurado para apuntar a `/mcp` y, si el despliegue esta protegido, enviar `X-API-Key`.

Capacidades principales hoy:

- legislacion: `list_legislacion`, `get_norma`, `list_articulos`, `get_articulo`, `get_articulo_historial`, `buscar`, `buscar_legislacion`
- materias: `list_materias`, `get_materia`
- doctrina: `buscar_doctrina`, `get_doctrina`
- modelos AEAT: operaciones del catalogo HTTP para listar y consultar modelos y sus fuentes oficiales

## Recorrido stdio MCP

El servidor `stdio` esta pensado para clientes locales o integraciones que prefieren lanzar un proceso hijo en lugar de consumir un endpoint HTTP.

En la practica, el cliente usa `stdio MCP` arrancando un proceso MCP local en vez de conectarse a una URL remota como `/mcp`.

El servidor stdio, implementado en `apps/api/mcp_stdio.py`, expone herramientas de mas alto nivel orientadas a agentes y LLMs locales.

Tools destacadas hoy:

- `consulta_fiscal`
- `listar_obligaciones_operativas`
- `listar_obligaciones_aplicables`
- `listar_deadlines`
- `get_obligacion_completa`
- `list_modelos_por_supuesto`
- `agente_consulta`
- `agente_monitoreo_status`
- `agente_compliance_resumen`

Ejemplos de tareas tipicas en stdio:

`consulta_fiscal`:

- resolver una consulta fiscal en lenguaje natural
- orientar a un agente local sobre como enfocar una duda tributaria

`list_modelos_por_supuesto`:

- clasificar modelos AEAT candidatos por perfil y supuesto, por ejemplo `sociedad_valores` con clientes residentes/no residentes
- devolver `candidato` o `requiere_verificacion` cuando no haya evidencia explicita de obligatoriedad; no debe usarse para afirmar obligacion sin revision

`get_modelo_casillas` en HTTP MCP:

- usar `limit`/`offset` para modelos grandes; por defecto devuelve una pagina, no una descarga completa
- continuar con `next_offset` solo si `has_more=true`
- tratar `classification=confirmado` como existencia de casilla/campo oficial en la campana consultada, no como obligatoriedad individual

`get_modelo`:

- tambien pagina las casillas embebidas con `casillas_limit`/`casillas_offset`
- si `casillas_has_more=true`, continuar con `/v1/modelos/{codigo}/casillas` o con `casillas_next_offset`
- limita listas relacionadas con `related_limit`; revisar `articulos_total`, `articulos_has_more`, `claves_total`, `instrucciones_total` y `normativa_total` antes de asumir que se ha visto todo
- no interpretar una casilla devuelta como obligatoria para un caso concreto sin evidencia adicional

Listados MCP/Actions:

- `list_modelos`, `list_legislacion`, `get_modelo_articulos`, `get_modelo_claves`, `get_modelo_instrucciones`, `listar_convenios_dta_internacional`, `listar_reglas_retencion_internacional` y `listar_workflow_compliance` aceptan pagina (`limit`/`offset`)
- si una respuesta incluye `has_more=true`, el cliente debe pedir la pagina siguiente con `next_offset`; no debe completar la lista por inferencia

`listar_obligaciones_aplicables`:

- revisar obligaciones operativas aplicables a un caso o perfil
- obtener una vista de plazos y obligaciones relacionadas
- usar `limite`/`offset`; la salida incluye `total`, `has_more` y `next_offset`
- si no hay obligaciones aplicables verificadas, la herramienta debe devolver
  `status=evidence_limited`, `verified=false` y `review_required=true`; no
  convertirlo en "no existen obligaciones"

`list_domain_availability`:

- `only_empty=true` significa "no seguro para responder directamente", no solo `row_count=0`
- los endpoints directos de dominios vacios deben devolver `availability_status`, `safe_to_answer=false`, `items=[]` y `total=0`

`get_obligacion_completa`:

- utilidad: recuperar plazos, sanciones, recargos y documentos relacionados

## Regla practica

- `HTTP MCP` y `stdio MCP` no comparten catalogo ni semantica
- no asumir que una tool visible en stdio existe tambien en HTTP MCP
- no documentar una tool como "MCP general" sin indicar explicitamente si pertenece a `HTTP` o a `stdio`
- si `verified=false`, `review_required=true`, `evidence_limited` o `requiere_verificacion`, el cliente debe responder con incertidumbre y no completar la respuesta con conocimiento externo
- para listas grandes, pedir una pagina acotada (`limit`, filtros, o primeros N) y continuar solo cuando la respuesta incluya `has_more=true`

Glosario operativo:

- `confirmado`: ESData devuelve evidencia explicita suficiente para la aplicabilidad indicada, o existencia oficial del recurso consultado
- `candidato`: ESData encuentra una relacion plausible, pero no confirma obligatoriedad ni aplicabilidad completa
- `requiere_verificacion`: ESData no tiene evidencia suficiente; requiere fuente oficial/humano antes de usarlo en un flujo compliance

## Casos de uso recomendados

Para elegir entre `HTTP MCP` y `stdio MCP`:

- usa `HTTP MCP` si tu cliente MCP ya trabaja por HTTP y quieres consumir el catalogo HTTP publicado en `/mcp`
- usa `stdio MCP` si tu cliente MCP arranca un proceso local y necesitas tools de mas alto nivel como `consulta_fiscal` o `agente_consulta`

La API normal encaja mejor cuando:

- integras con otro backend o servicio propio
- necesitas control fino de errores, reintentos y versionado de contrato
- no trabajas con clientes MCP

## Regla de seguridad

No tratar `MCP` como una superficie publica abierta por defecto.

No tratar tampoco la respuesta del MCP como verdad autosuficiente; verifica siempre contra la fuente oficial citada.

En despliegues protegidos, `HTTP MCP` puede requerir API key y controles perimetrales adicionales.

