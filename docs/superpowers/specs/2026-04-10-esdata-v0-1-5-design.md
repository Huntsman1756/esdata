# esdata v0.1.5 Design

## Goal

Construir una primera API fiscal española utilizable por humanos y agentes de IA, centrada en legislación fiscal estatal y doctrina tributaria, pero con un esquema y contratos que no obliguen a rehacer la base del sistema cuando entren nuevas fuentes regulatorias.

## Scope

### Entra en v0.1.5

- Legislación fiscal estatal desde BOE, con foco inicial en `LIVA`, `LIS`, `LIRPF` y `LGT`.
- Modelo de norma y artículo versionado por fecha.
- Modelo genérico de documento interpretativo para DGT y TEAC.
- API HTTP mínima ejecutable en local.
- Búsqueda preparada para crecer sin romper contrato.
- Estado operativo básico con `/health` y `/status`.
- Seeds/fixtures mínimos para demostrar el flujo extremo a extremo.

### No entra en v0.1.5

- Ingesta real de EUR-Lex.
- Ingesta real de CNMV, ESMA o Banco de España.
- Endpoints editoriales tipo `/v1/obligaciones/{slug}`.
- Ranking cross-fuente avanzado.
- Webhooks y sincronización completa de múltiples dominios de datos públicos no jurídicos.

## Product Positioning

El wedge de `esdata` no es competir desde el día 1 con un agregador horizontal de datos públicos como `ptdata`. El wedge es una API fiscal española con fundamento legal artículo por artículo, apta para agentes de IA mediante REST y MCP.

La ampliación a otros dominios o a otras fuentes supervisoras queda permitida por el modelo, pero no forma parte del primer entregable.

## Current Repository Reality

El repositorio no implementa todavía la arquitectura descrita en `STRUCTURE.md`. Ahora mismo solo existen un router `status`, un test smoke que referencia piezas inexistentes y un worker de Cloudflare. `docker-compose.yml` apunta a archivos y servicios que aún no están presentes.

Por tanto, el primer objetivo técnico no es “ajustar una API ya existente”, sino crear una base mínima arrancable y coherente con el diseño de v0.1.5.

## Architecture Decision

Se adopta una arquitectura de arranque simple:

- `apps/api`: FastAPI como servicio principal.
- `infra/sql/init.sql`: esquema inicial de PostgreSQL para entorno local.
- `docker-compose.yml`: arranque de `postgres`, `redis` y `api`.
- `infra/cloudflare/worker.js`: gateway conservador, mantenido separado del backend local.

El diseño deja espacio para extraer luego librerías comunes y workers independientes, pero no fuerza esa complejidad antes de tener el producto mínimo funcionando.

## Data Model

### Norma

La entidad `norma` debe incluir desde el inicio:

- `codigo`
- `titulo`
- `boe_id`
- `eli_uri`
- `jurisdiccion`
- `tipo_fuente`
- `ambito`
- `vigente_desde`

Decisiones:

- `jurisdiccion` arranca con valor `es`.
- `tipo_fuente` arranca con valores como `boe` y después permitirá `eur_lex`, `cnmv`, `esma`, `bde`.
- `ambito` arranca con `fiscal`, pero el contrato admite `mercados`, `resiliencia`, `gestion_activos`, `criptoactivos`.

### Versionado legislativo

Se mantiene el modelo de `version_norma` y `version_articulo` del PRD, porque es el núcleo del valor del producto.

Requisitos:

- consulta por `vigente_en`
- historial por artículo
- unicidad por norma y fecha de versión
- capacidad de búsqueda sobre texto vigente o histórico

### Documento interpretativo

La tabla no debe nacer sesgada a fiscalidad aunque sus primeras fuentes sí lo sean. En lugar de una tabla pensada solo para DGT/TEAC, el diseño usa una entidad genérica de documento interpretativo.

Campos mínimos:

- `tipo_documento`
- `organismo_emisor`
- `jurisdiccion`
- `tipo_fuente`
- `ambito`
- `referencia`
- `fecha`
- `titulo`
- `texto`
- `url_fuente`

Ejemplos de `tipo_documento`:

- `consulta_vinculante`
- `resolucion_teac`
- `criterio_supervisor`
- `guia`
- `qa`

### Enlace entre norma y documento interpretativo

La relación entre artículo y documento interpretativo debe capturar evidencia, no solo existencia del vínculo.

Campos mínimos en la tabla intermedia:

- `articulo_id`
- `documento_id`
- `metodo_enlace`
- `confianza_enlace`
- `nota`

Valores iniciales sugeridos:

- `metodo_enlace`: `manual`, `regex`, `heuristico`
- `confianza_enlace`: decimal de `0` a `1`

### Confianza de respuesta

Se adopta desde el inicio el nivel `0`, además de los niveles posteriores.

Contrato inicial:

- `0`: existe criterio o resultado recuperado, pero no se ha podido anclar de forma suficiente a norma base.
- `1`: norma encontrada y citada.
- `2`: norma encontrada y al menos un documento interpretativo relacionado.
- `3`: resultado útil pero con advertencia relevante, por ejemplo modificación reciente o conflicto.

El cálculo vive en la capa de servicio, no en una tabla cerrada de base de datos.

## API Contract

El contrato debe dejar de estar acoplado a `/legislacion/buscar` como único eje futuro.

### Endpoints iniciales

- `GET /health`
- `GET /status`
- `GET /v1/legislacion`
- `GET /v1/legislacion/{codigo}`
- `GET /v1/legislacion/{codigo}/articulos/{numero}`
- `GET /v1/legislacion/{codigo}/articulos/{numero}/historial`
- `GET /v1/materias/{slug}`
- `GET /v1/doctrina/{referencia}`

### Búsqueda

Se introduce una capa más genérica:

- `GET /v1/buscar`

Filtros iniciales:

- `q`
- `fuente`
- `ambito`
- `tipo`
- `norma`
- `vigente_en`

Notas:

- internamente puede delegar al buscador legislativo inicial
- se puede mantener compatibilidad temporal con `/v1/legislacion/buscar`
- el contrato público nuevo debe ser el que crezca

## Execution Baseline

El primer entregable ejecutable de v0.1.5 será:

- FastAPI arrancando en local.
- PostgreSQL inicializable con el schema mínimo.
- Fixtures/seed con al menos una norma, un artículo versionado, una materia y un documento interpretativo.
- Smoke tests que validen `/health`, `/status`, `GET /v1/legislacion/LIVA/articulos/91` y `GET /v1/buscar`.

No se exige en este corte la ingesta real desde fuentes externas. Esa fase se puede construir encima de una base que ya corre.

## Delivery Phases

### Fase A

Base ejecutable:

- `main.py`
- conexión a base de datos
- schema SQL
- rutas mínimas
- seeds
- tests básicos

### Fase B

Contratos jurídicos:

- modelo ampliado de `norma`
- modelo genérico de documento interpretativo
- relación con `metodo_enlace` y `confianza_enlace`
- cálculo de `confianza` con nivel `0`

### Fase C

Búsqueda y compatibilidad:

- `/v1/buscar`
- compatibilidad con ruta de búsqueda legislativa anterior
- filtros `fuente`, `ambito` y `tipo`

### Fase D

Preparación para ingesta:

- estructura de workers
- tablas de `sync_log`
- contrato de estado operativo

## Risks

- El mayor riesgo actual no es de producto sino de base técnica: el repositorio todavía no arranca.
- Si se intenta meter ingesta real BOE y scraping DGT/TEAC antes de estabilizar el backend mínimo, el proyecto se ralentizará y se mezclará validación de arquitectura con validación de fuentes.
- Si `doctrina` nace demasiado fiscal-específica, habrá deuda de migración cuando entren supervisores financieros.

## Decision Summary

`esdata v0.1.5` será una API fiscal española mínima, ejecutable y demostrable, con estructura multi-fuente desde el schema y desde el contrato de búsqueda, pero sin ampliar aún el alcance funcional más allá de BOE + DGT/TEAC.

## Blockers

- El repositorio no está inicializado como git en `G:\_Proyectos\esdata`, así que no se puede cumplir el paso de commit del flujo de diseño hasta que exista un repositorio git real o se indique otro directorio raíz.
