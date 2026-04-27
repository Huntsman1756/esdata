# Como usar esdata

## Formas de uso

`esdata` puede consumirse de varias formas segun el tipo de usuario:

- como backend consultable por `API`
- como superficie `MCP` para flujos con LLMs y agentes
- como UI web interna para consulta y paneles administrativos
- como servicios y utilidades internas del repositorio para operacion y desarrollo

## Flujo recomendado para un usuario nuevo

1. Entender que problema resuelve `esdata` en `01-que-es-esdata-y-que-incluye.md`.
2. Revisar las superficies disponibles en `03-superficies-disponibles.md`.
3. Preparar entorno y operacion minima en `04-operacion-tecnica.md`.
4. Consultar limites y cobertura en `05-limites-alcance-y-estado-actual.md`.

## Uso web actual

La UI web existente ofrece hoy, al menos, estas rutas visibles en el repo:

- `/` — pantalla principal de consulta
- `/buscar` — buscador con pestanas para legislacion, DGT y TEAC
- `/articulo/[norma]/[numero]` — detalle de articulo
- `/doctrina/[...referencia]` — detalle de doctrina
- `/modelo/[codigo]` — detalle de modelo AEAT
- `/admin/cambios` — panel interno de cambios regulatorios
- `/admin/workflow` — panel interno de workflow de compliance

## Uso por API

La forma mas estable de integracion es consumir la API HTTP y su OpenAPI.

Ejemplos de uso tipico:

1. consultar salud con `/health`
2. buscar normativa con `/v1/buscar` o `/v1/legislacion/buscar`
3. recuperar detalle de una norma o articulo
4. consultar modelos AEAT y sus casillas o instrucciones
5. consultar obligaciones, cambios o workflow de compliance

## Uso por MCP

`MCP` sirve para exponer una seleccion de operaciones a clientes compatibles con Model Context Protocol.

Es util cuando el consumidor principal es un agente o LLM y no una aplicacion backend tradicional.

## Uso operativo interno

Ademas de las superficies de usuario, el repo permite:

- ejecutar workers de ingestion
- revisar estado agregado con `/status`
- operar migraciones Alembic
- consultar runbooks de backup, restore y operacion

## Que esperar de la herramienta

- consultas y datos estructurados sobre corpus fiscal-regulatorio
- trazabilidad y separacion por fuente
- una base pensada para integraciones y workflows, no solo para lectura humana

## Que no esperar

- consejo legal o fiscal profesional automatico
- acceso directo del frontend a la base de datos
- una interfaz unica y definitiva para todos los casos de uso
- cobertura universal de cualquier ambito legal

## Regla practica

Si vas a usar `esdata` desde otra herramienta o agente, empieza por la superficie mas estable y controlada disponible para tu caso (`API` o `MCP`) en lugar de acoplarte a archivos internos del repositorio.

Si necesitas una tarea humana repetible o automatizacion de plataforma, prioriza `API`. Si necesitas una herramienta para un cliente MCP o un LLM, prioriza `MCP`.
