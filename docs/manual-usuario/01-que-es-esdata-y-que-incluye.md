# Que es esdata y que incluye

## Resumen

`esdata` es una capa de datos y consulta fiscal-regulatoria con trazabilidad a fuente oficial.

Su objetivo no es ser un copiloto legal generalista ni una base documental horizontal para cualquier materia. Su foco es reforzar una base fiscal y regulatoria fiable para consultas, compliance operativo y futuras capas privadas construidas sobre corpus publico.

La superficie principal hoy esta construida sobre:

- `API` FastAPI
- `MCP` montado sobre la API
- workers de ingestión por fuente
- base de datos PostgreSQL
- UI web interna para consulta y algunos flujos de operacion

## Para quien esta pensado

- usuarios internos que necesitan consultar normativa y datos regulatorios con trazabilidad
- agentes o copilots que necesitan contexto fiable y estructurado
- operadores que necesitan una base reutilizable para workflows de compliance

## Que incluye a nivel alto

- ingesta por fuentes mediante workers
- API backend sobre FastAPI
- base de datos PostgreSQL
- superficies de consumo por `API` y `MCP`
- documentacion tecnica y operativa en `docs/`

## Fuentes y dominios con cobertura cargada

Segun el estado actual del repo, `esdata` incluye capas operativas o documentales
con estos limites:

- legislacion BOE consolidada: `usable` para normas/articulos cargados, no todo BOE
- doctrina administrativa y criterios: `partial_traceable`
- modelos AEAT: `partial`, no decision automatica de obligaciones
- obligaciones regulatorias: `partial`, solo cuando hay evidencia explicita
- cambios regulatorios: `internal_support`
- workflow de compliance: `internal_support`
- empresas y entidades: superficie auxiliar, no fuente regulatoria certificada
- BORME: `partial`
- BDNS: `very_limited`
- CNMV: `partial`
- SEPBLAC: `partial`
- CENDOJ: `very_limited`
- EUR-Lex: `partial` salvo subfamilias verificadas por canary
- Banco de Espana: `partial`
- AEPD: `partial`
- PGC: `partial`
- screening: `usable` solo para listas OFAC SDN y EU sanctions cargadas

Ningun dominio se debe interpretar como cobertura exhaustiva. La matriz activa
de alcance esta en `../final-product-coverage-matrix.md`.

## Perfil regulado prioritario actual

El caso de uso regulatorio prioritario actual es `sociedad de valores` en Espana.

Eso no significa que todo el producto se limite a ese perfil, pero si que las capas de compliance y aplicabilidad regulatoria se estan ordenando con ese objetivo como referencia principal.

## Lo que aporta el producto

- consultas estructuradas en vez de texto libre sin trazabilidad
- relacion entre normas, doctrina, modelos y obligaciones
- una base apta para integrarse en agentes o aplicaciones
- una separacion clara entre fuentes crudas, normalizacion y superficie de consulta

## Principios del producto

- trazabilidad a fuente oficial
- normalizacion antes de exponer datos al usuario
- cambios pequenos y reversibles
- arquitectura backend-first
- separacion entre corpus publico base y capas privadas futuras

## Regla de interpretacion

Cuando haya diferencia entre este manual y el estado vivo del roadmap, el roadmap manda para saber que fase esta activa. Este manual describe el producto y su uso, no el estado de ejecucion de una iteracion concreta.

Referencias utiles:

- `../master-execution-roadmap.md`
- `../architecture.md`
- `../../README.md`
