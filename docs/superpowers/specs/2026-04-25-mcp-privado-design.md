# Diseno: MCP Privado Fiable para uso personal e interno

## Objetivo

Reforzar `esdata` como backend fiscal consumible por LLMs en dos modos principales: `stdio` local para uso personal y `HTTP privado` para uso interno en empresa. El objetivo de este corte no es vender el producto ni abrirlo al publico, sino hacerlo consistente, seguro en lo basico y facil de operar.

## Alcance de este corte

Incluye:
- unificar la definicion de herramientas MCP entre `HTTP` y `stdio`
- proteger `HTTP /mcp` con `API key`
- aplicar `rate limit` basico en la superficie MCP HTTP
- automatizar tests MCP basicos en lugar de depender de scripts manuales
- aclarar en documentacion los modos `stdio local`, `HTTP privado` y `GPT Actions`

No incluye:
- autenticacion avanzada (OAuth, SSO, scopes, multi-tenant)
- permisos por herramienta
- producto publico para terceros
- rediseño del dominio fiscal o de los endpoints REST
- observabilidad avanzada o billing

## Contexto actual

El repo ya tiene una superficie MCP real en `HTTP` montada con `fastapi-mcp` y una implementacion separada para `stdio`.

Problemas detectados en el estado actual:
- `HTTP` y `stdio` no exponen la misma superficie funcional
- la implementacion `stdio` define herramientas a mano y deriva con facilidad
- no hay proteccion minima explicita en `/mcp` para uso interno por red
- parte de la validacion MCP vive en scripts manuales en vez de tests automatizados
- la documentacion mezcla `MCP`, `GPT Actions` y despliegue historico, generando ambiguedad para consumidores LLM

## Usuarios y modos de uso

### Modo 1: stdio local
- uso principal para trabajo personal
- sin auth adicional
- pensado para ejecutar el servidor MCP junto al cliente LLM en la misma maquina

### Modo 2: HTTP privado
- uso interno en empresa o red privada
- requiere `API key`
- protegido con `rate limit` basico
- no se diseña para exposicion publica abierta a internet

### Modo 3: GPT Actions
- integracion secundaria basada en OpenAPI
- se mantiene separada conceptualmente del modo MCP
- sirve como camino practico para ChatGPT, pero no define la arquitectura principal del servidor MCP

## Principios de diseno

1. Una sola verdad para herramientas MCP.
2. Dos transportes, misma semantica: `stdio` y `HTTP`.
3. Seguridad minima pero realista para uso privado.
4. Cero sobreingenieria: nada de auth compleja en esta fase.
5. La documentacion debe dejar claro que `GPT Actions` y `MCP` son superficies distintas.

## Arquitectura propuesta

### Nucleo MCP compartido

Se introduce un nucleo compartido responsable de:
- definir el catalogo de herramientas
- declarar descripcion y esquema de entrada
- resolver la ejecucion de cada herramienta
- normalizar la respuesta estructurada y textual

Ese nucleo debe ser consumido por:
- `apps/api/mcp_server.py` para el transporte HTTP
- `apps/api/mcp_stdio.py` para el transporte stdio

### Responsabilidades por fichero

Estructura objetivo minima:

```text
apps/api/
├── main.py
├── mcp_server.py
├── mcp_stdio.py
├── mcp_catalog.py         # catalogo compartido de herramientas y metadata
├── mcp_executor.py        # ejecucion de herramientas sobre la app/API
├── security/
│   └── mcp_guard.py       # api key + rate limit basico para /mcp
└── tests/
    ├── test_mcp_http.py
    └── test_mcp_stdio.py
```

Si el repo ya tiene otra convencion de ubicacion para tests o seguridad, se mantendra la convencion existente y solo se introduciran nuevos ficheros si mejora la claridad.

## Transporte HTTP MCP

`apps/api/mcp_server.py` sigue usando `fastapi-mcp`, pero deja de ser la fuente primaria de definicion funcional. Su responsabilidad pasa a ser:
- montar MCP en `/mcp`
- exponer solo las operaciones permitidas
- apoyarse en el catalogo compartido para mantener paridad documental y operativa con `stdio`
- aplicar guardas de seguridad al acceso HTTP

Resultado esperado:
- la lista de herramientas documentadas para LLMs no diverge segun transporte
- el modo HTTP queda claramente orientado a uso privado

## Transporte stdio MCP

`apps/api/mcp_stdio.py` deja de declarar herramientas manualmente como una lista mantenida a mano.

Su responsabilidad pasa a ser:
- anunciar el mismo catalogo compartido que el modo HTTP
- delegar ejecucion en el mismo nucleo
- mantener el handshake MCP y framing stdio

Resultado esperado:
- `tools/list` y `tools/call` en stdio reflejan la misma superficie que HTTP
- el modo local sigue siendo ergonomico para uso personal

## Seguridad para HTTP privado

### API key

Se introduce una variable de entorno dedicada, por ejemplo `MCP_API_KEY`.

Comportamiento:
- `stdio`: ignora esta variable y no requiere auth
- `HTTP /mcp` en desarrollo local: puede arrancar sin key, con aviso claro
- `HTTP /mcp` en produccion: requiere key para aceptar llamadas

Validacion propuesta:
- cabecera dedicada tipo `X-API-Key` o `Authorization: Bearer <key>`
- una unica clave compartida en esta fase
- si falta o no coincide, devolver `401`

Eleccion recomendada:
- usar `X-API-Key` por simplicidad operativa interna y menor ambiguedad

### Rate limit

Se añade rate limiting ligero sobre `/mcp`.

Objetivo:
- evitar abusos accidentales
- proteger consultas costosas
- tener una degradacion simple en entorno interno

Regla inicial recomendada:
- limite fijo por IP o por API key
- ventana corta por minuto
- respuesta `429` al superar limite

No hace falta un sistema distribuido complejo en esta fase. Un limitador sencillo en memoria es aceptable para este corte si queda claro su alcance y limitaciones.

## Configuracion y comportamiento por entorno

### Desarrollo local
- `stdio` es el camino principal
- `HTTP /mcp` puede arrancar sin `MCP_API_KEY`
- si falta la key, se emite warning visible en logs

### Produccion privada
- `HTTP /mcp` requiere `MCP_API_KEY`
- `rate limit` activo
- recomendacion de poner ademas la API detras de red privada, proxy o VPN, pero sin hacerlo requisito de app para este corte

## Tests

Se sustituyen o complementan los scripts manuales por tests automatizados reproducibles.

Cobertura minima requerida:

### HTTP MCP
- `initialize` responde correctamente
- `tools/list` devuelve herramientas
- `tools/call` sobre una herramienta representativa devuelve resultado valido
- acceso sin `API key` falla cuando la proteccion esta activa
- exceso de peticiones devuelve `429`

### stdio MCP
- handshake basico correcto
- `tools/list` devuelve el mismo conjunto esperado de herramientas clave
- `tools/call` sobre una herramienta representativa funciona

### Paridad
- al menos un test debe comprobar que las herramientas clave publicadas por `stdio` y `HTTP` no divergen en nombres

## Documentacion

La documentacion debe separar claramente tres historias:

### 1. MCP stdio local
- como arrancarlo
- como conectarlo desde un cliente local
- para que usarlo

### 2. MCP HTTP privado
- como configurarlo con `MCP_API_KEY`
- como llamar `/mcp`
- limitaciones y recomendacion de uso interno

### 3. GPT Actions
- mantenerlo como integracion OpenAPI secundaria
- dejar claro que no sustituye el servidor MCP

Cambios esperados:
- `README.md` mas claro y menos mezclado
- posible doc nueva bajo `docs/` con una guia corta de conexion MCP privada

## Compatibilidad y migracion

Este corte debe intentar mantener compatibilidad con el uso actual del repo:
- no romper endpoints REST existentes
- no romper GPT Actions existentes
- no romper el modo local stdio

Cambio visible esperado:
- el modo HTTP privado puede empezar a exigir `API key` segun entorno/configuracion

## Riesgos

1. `fastapi-mcp` puede imponer limites sobre cuanto se puede reutilizar del catalogo compartido.
2. Un `rate limit` en memoria no cubre todos los casos si luego escalas a multiples replicas.
3. Si la documentacion no separa bien `GPT Actions` y `MCP`, la confusion de consumo seguira existiendo.
4. Intentar unificar demasiado puede acabar introduciendo una refactorizacion mayor de la necesaria.

## Decisiones explicitas

- Se prioriza `MCP privado fiable`, no producto publico.
- Se mantiene `stdio` como modo principal de uso personal.
- Se mantiene `HTTP privado` como modo secundario para uso interno.
- Se elige `API key + rate limit` como seguridad minima suficiente para este corte.
- `GPT Actions` sigue existiendo, pero como superficie separada y secundaria.

## Criterio de exito

1. `stdio` y `HTTP` exponen el mismo conjunto base de herramientas MCP.
2. `HTTP /mcp` rechaza acceso sin `API key` cuando la proteccion esta activa.
3. `HTTP /mcp` aplica `rate limit` y devuelve `429` al excederlo.
4. Existen tests automatizados para `initialize`, `tools/list`, `tools/call`, auth y rate limit.
5. `README.md` explica claramente la diferencia entre `MCP stdio`, `MCP HTTP privado` y `GPT Actions`.
6. El flujo local por `stdio` sigue funcionando sin aumentar friccion innecesaria.
