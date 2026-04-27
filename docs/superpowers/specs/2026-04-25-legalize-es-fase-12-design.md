# Fase 12 legalize-es Minimal Slice Design

## Objetivo

Definir el primer slice ejecutable de `Fase 12` para incorporar `legalize-es` como fuente complementaria en `esdata` sin cambiar la arquitectura principal del producto.

El objetivo del slice es validar el flujo completo `raw-md -> parser -> db -> api` sobre una sola norma (`CC`) usando fixtures markdown locales, de forma que el parser sea estable, testeable y desacoplado del consumo real del repo externo en esta primera iteracion.

## Estado real del repo

- No existe aun `apps/workers/legalize_es.py`.
- Ya existe el pipeline objetivo reutilizable para legislacion: `norma`, `articulo`, `version_articulo`.
- Ya existe el router `apps/api/routers/legislacion.py` con endpoints de listado, detalle, historial y cobertura.
- `Fase 12` del roadmap ya fija el patron recomendado: `raw-md -> parser -> db`.

## Decision principal

Se fija este primer slice con las decisiones ya aprobadas:

- entrada inicial mediante fixtures `.md` locales, no clon real del repo `legalize-es`
- una sola norma objetivo: `CC`
- validacion completa hasta DB + busqueda + detalle con `vigente_en`

No se intenta en este slice:

- leer el repo real de `legalize-es`
- soportar varias normas a la vez
- soportar disposiciones adicionales, transitorias o anexos complejos
- modelar versionado historico fino por commit real externo

## Alcance del slice

Incluido:

- fixture markdown local del `CC`
- parser minimo para identificar metadata basica de norma y bloques `Articulo X.`
- worker `apps/workers/legalize_es.py`
- upsert a tablas existentes `norma`, `articulo`, `version_articulo`
- tests de parser y upsert
- test API para comprobar que el contenido aparece en `GET /v1/legislacion/buscar`
- test API para comprobar detalle de articulo con `vigente_en`

Excluido:

- clon, fetch o releases reales de `legalize-es`
- parser generalista de todo el ecosistema markdown
- cobertura de `LEC` o `ET` en este primer corte
- ampliaciones de schema no estrictamente necesarias

## Arquitectura propuesta

### Patron de datos

El patron de esta fase queda fijado como:

`raw-md -> parser -> db -> api`

Interpretacion practica:

- el markdown es artefacto fuente legible
- el worker lo transforma a estructura intermedia minima
- la DB sigue siendo la superficie operativa real
- la API nunca sirve markdown bruto como respuesta final

### Worker

Se crea `apps/workers/legalize_es.py` con un estilo compatible con los workers existentes.

Responsabilidades:

- leer markdown desde ruta local
- parsear encabezado de norma y articulos
- construir payloads normalizados pequenos
- hacer upsert en `norma`, `articulo`, `version_articulo`

No debe:

- mezclar scraping de red con parsing en este primer slice
- introducir logica de negocio en frontend

### Parser

El parser del primer slice solo necesita soportar patrones simples y controlados por fixture, por ejemplo:

- titulo de norma
- bloques `Articulo 1.` / `Articulo 2.`
- texto libre hasta el siguiente articulo

El parser debe producir una estructura minima equivalente a:

- `codigo_norma`
- `titulo`
- `tipo_fuente`
- `articulos[]`
  - `numero`
  - `texto`
  - `vigente_desde`

### Persistencia

Se reutilizan tablas existentes:

- `norma`
- `articulo`
- `version_articulo`

No se anade schema nuevo salvo que aparezca una necesidad estricta durante implementacion.

### API

El objetivo no es crear endpoints nuevos, sino verificar que el pipeline insertado alimenta correctamente:

- `GET /v1/legislacion/buscar`
- `GET /v1/legislacion/CC/articulos/{numero}?vigente_en=...`

## Decisiones de modelado

### Codigo de norma

- `CC`

### Fuente

- `tipo_fuente` debe reflejar claramente que esta ingesta entra por `legalize-es` o por corpus markdown derivado, sin fingir que viene directamente del BOE en este slice

### Fecha de version

- en este primer corte se usa una fecha curada/fija en fixture o payload del worker
- no se usan aun commits reales de `legalize-es` como `fecha_version`

### Trazabilidad

- debe conservarse referencia al fixture/origen markdown para no perder explicabilidad

## Tests

### Worker

Archivo nuevo: `apps/workers/tests/test_legalize_es.py`

Cobertura minima:

- parsea articulos del fixture `CC`
- inserta `norma`
- inserta `articulo`
- inserta `version_articulo`
- ejecutar dos veces no duplica registros

### API

Se extienden tests existentes o se crea test especifico para:

- buscar texto del `CC` en `GET /v1/legislacion/buscar`
- recuperar detalle de `CC` articulo concreto con `vigente_en`

## Riesgos y mitigaciones

### Riesgo 1

El markdown real de `legalize-es` puede tener mas variedad estructural de la prevista.

Mitigacion:

- empezar con fixture controlado
- fijar parser minimo primero
- ampliar formatos en slices posteriores

### Riesgo 2

Marcar una norma derivada como si fuera fuente oficial directa.

Mitigacion:

- distinguir claramente el origen de `legalize-es`
- mantener trazabilidad al origen bruto

### Riesgo 3

Intentar cubrir demasiados tipos de bloques legales en el primer slice.

Mitigacion:

- centrarse solo en articulos
- dejar disposiciones y estructuras especiales para despues

## Criterio de aprobacion del slice

Este primer slice de `Fase 12` se considera bien resuelto cuando:

1. existe un worker `legalize_es.py` minimo funcional
2. un fixture markdown del `CC` se parsea correctamente
3. el contenido llega a `norma`, `articulo`, `version_articulo`
4. `GET /v1/legislacion/buscar` encuentra contenido del `CC`
5. el detalle de articulo con `vigente_en` responde correctamente
6. tests verdes

## Archivos previstos

Crear:

- `apps/workers/legalize_es.py`
- `apps/workers/tests/test_legalize_es.py`
- `apps/workers/tests/fixtures/legalize_es/cc.md`

Modificar:

- `apps/api/tests/test_search_legislacion.py` o archivo de test API equivalente
- `docs/master-execution-roadmap.md`

## No objetivos de este slice

- no convertir `esdata` en un repositorio de markdown como almacenamiento principal
- no sustituir BOE como fuente oficial primaria donde ya exista worker mejor
- no intentar cubrir `8,600+` leyes en la primera iteracion
- no introducir nuevas tablas si el modelo actual ya soporta el flujo
