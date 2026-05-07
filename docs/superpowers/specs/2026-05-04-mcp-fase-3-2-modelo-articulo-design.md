# Diseno: MCP Fase 3.2 - Endurecer modelo_articulo

## Objetivo

Endurecer `modelo_articulo` para que el runtime solo exponga enlaces de articulo exactos y trazables, eliminando del API/MCP los mappings legacy que hoy se resolvieron por `numero` de articulo solamente.

## Contexto

Hoy `modelo_articulo` sigue teniendo una forma demasiado debil para una superficie MCP que promete trazabilidad:

- la tabla solo guarda `modelo_id`, `articulo_id`, `casilla`, `nota`, `fuente` y `url_fuente`
- `scripts/data/seed_modelo_articulo.py` resuelve `articulo_id` por `articulo.numero` sin exigir `(norma, numero)`
- `apps/api/services/modelos.py` devuelve cualquier fila existente de `modelo_articulo` sin distinguir linking fuerte de linking legacy
- `list_modelos_summary()` cuenta esos enlaces como si tuvieran el mismo nivel de verdad que los enlaces verificados

En paralelo, la ruta canonica ya definida en 3.1 (`scripts/seed-modelos.py`) dispone de la informacion exacta que falta en la tabla legacy: cada relacion ya nace como `(modelo_codigo, norma, numero, casilla, nota, fuente, url_fuente)`.

Decision ya aprobada por producto para 3.2:

- los enlaces legacy debiles no deben aparecer en runtime como `unverified`
- deben quedar ocultos del API/MCP
- la tabla actual se endurece in-place, sin crear una tabla nueva

## Decision de diseno

Se adopta endurecimiento in-place sobre `modelo_articulo`.

La tabla mantiene `articulo_id` como FK canonica al corpus, pero pasa a almacenar tambien la clave exacta y la provenance explicita del enlace.

La forma objetivo por fila es:

- `modelo_id`
- `articulo_id`
- `norma`
- `numero`
- `casilla`
- `nota`
- `fuente`
- `url_fuente`
- `metodo_enlace`
- `confianza_enlace`

La semantica operativa sera binaria:

1. fila fuerte y visible en runtime
2. fila legacy y oculta en runtime

No se elimina la tabla ni se crea una proyeccion paralela. El gating sucede sobre la misma tabla mediante columnas nuevas y una politica de lectura conservadora.

## Modelo de datos aprobado

La nueva migracion debe:

1. anadir a `modelo_articulo` las columnas `norma`, `numero`, `metodo_enlace` y `confianza_enlace`
2. rellenar `norma` y `numero` desde el `articulo_id` ya persistido mediante join con `articulo` + `norma`
3. marcar las filas existentes heredadas como linking debil con:
   - `metodo_enlace = 'legacy_numero_only'`
   - `confianza_enlace = 0.0`
4. dejar las nuevas columnas en estado obligatorio tras el backfill
5. anadir un guardarrail de rango para `confianza_enlace` en `0..1`
6. anadir un indice o constraint de unicidad por `(modelo_id, norma, numero)` para evitar duplicados exactos en nuevas inserciones

Razon del backfill:

- incluso una fila legacy debe quedar autoexplicativa y auditable dentro de la propia tabla
- el dato legacy no se promueve a fuerte por llevar `(norma, numero)` rellenado; sigue siendo legacy por su `metodo_enlace` y `confianza_enlace`

## Politica de provenance

Para 3.2 se fija una unica clase de enlace fuerte visible en runtime:

- `metodo_enlace = 'manual_official'`
- `confianza_enlace = 1.0`
- `fuente` no vacia
- `url_fuente` no nula
- `(norma, numero)` consistente con el `articulo_id` enlazado

Cualquier otro metodo o confianza queda fuera del runtime de modelos hasta que exista una decision explicita para ampliarlo.

Esto incluye, de forma intencionada:

- `legacy_numero_only`
- filas antiguas sin URL oficial suficiente
- cualquier insercion nueva que no complete el contrato fuerte

## Politica de lectura en runtime

`apps/api/services/modelos.py` pasa a tratar `modelo_articulo` como un conjunto filtrado, no como una bolsa de relaciones equivalentes.

La lectura fuerte debe aplicar el mismo predicado en todos los call sites relevantes:

- `list_modelo_articulos()`
- `list_modelos_summary()`

Predicado operativo aprobado:

- `ma.metodo_enlace = 'manual_official'`
- `ma.confianza_enlace = 1.0`
- `ma.url_fuente IS NOT NULL`
- `ma.norma = n.codigo`
- `ma.numero = a.numero`

Efectos esperados:

- `/v1/modelos/{codigo}` solo devuelve `articulos` fuertes
- `/v1/modelos/{codigo}/articulos` solo devuelve `articulos` fuertes
- `articulos_count` deja de contar enlaces legacy ocultos
- la doctrina derivada desde `articulos` solo se construye a partir de enlaces fuertes visibles

La forma externa del payload no cambia en 3.2. Cambia la seleccion de filas, no el contrato JSON.

## Politica de seeds

### scripts/seed-modelos.py

Aunque el plan de fase no lo listara explicitamente, este archivo debe tocarse porque es la via canonica que seguiria creando filas debiles si no escribe las columnas nuevas.

Cada insercion canonica debe pasar a persistir:

- `norma`
- `numero`
- `metodo_enlace = 'manual_official'`
- `confianza_enlace = 1.0`

La resolucion del `articulo_id` debe seguir siendo por `(norma, numero)` como ya hace hoy.

### scripts/data/seed_modelo_articulo.py

Este script sigue siendo `LEGACY / NO AUTORITATIVO` como flujo, pero deja de ser peligroso como estructura.

Su dataset debe migrar a la misma forma de 7 campos del flujo canonico:

- `(modelo_codigo, norma, numero, casilla, nota, fuente, url_fuente)`

Su escritura debe persistir tambien:

- `metodo_enlace = 'manual_official'` para filas verificadas que sobrevivan en el archivo
- `confianza_enlace = 1.0`

Regla operativa:

- el script no puede volver a resolver por `numero` solamente
- si no puede resolver por `(norma, numero)`, debe saltar la fila
- el archivo puede seguir no siendo la ruta productiva canonica, pero ya no puede contaminar la tabla con linking ambiguo

## Contrato API

`apps/api/schemas.py` se toca solo para alinear la documentacion del contrato, no para cambiar la forma JSON.

En particular, `ModeloArticulo` debe seguir exponiendo:

- `norma`
- `numero`
- `titulo`
- `casilla`
- `nota`
- `fuente`
- `url_fuente`

Pero sus descripciones deben reflejar que el endpoint devuelve un enlace verificado visible en runtime, no cualquier relacion historica persistida en DB.

## Estrategia de tests aprobada

El cambio se implementa con TDD y con foco en el comportamiento visible.

### Scripts

`scripts/tests/test_seed_modelo_articulo.py` debe volverse rojo primero para fijar:

- nueva aridad de tuple: `7`
- presencia obligatoria de `modelo`, `norma`, `numero`, `fuente`, `url_fuente`
- desaparicion del modelo mental legacy de `impuesto` como pseudo-fuente

Si `scripts/seed-modelos.py` cambia de contrato interno visible, tambien debe mantenerse verde `scripts/tests/test_aeat_seed_canonical_flow.py`.

### API

`apps/api/tests/conftest.py` debe reflejar el schema endurecido y sembrar dos tipos de filas:

- una fila fuerte visible en runtime
- una fila legacy oculta en runtime

Fixtures concretos recomendados:

- mantener un enlace fuerte para `modelo 100` que permita seguir probando doctrina derivada
- sembrar un enlace legacy para `modelo 303` de forma que `/v1/modelos/303/articulos` siga devolviendo `0`

`apps/api/tests/test_modelos_truth_contract.py` debe anadir un caso que demuestre que el detalle de modelo no filtra enlaces debiles como si fueran verdad operativa.

`apps/api/tests/test_smoke.py` debe seguir fijando el comportamiento de `/v1/modelos/303/articulos` con filas legacy ocultas.

## Implementacion minima aprobada

Archivos obligatorios del slice:

- nueva migracion en `alembic/versions/`
- `scripts/seed-modelos.py`
- `scripts/data/seed_modelo_articulo.py`
- `scripts/tests/test_seed_modelo_articulo.py`
- `apps/api/services/modelos.py`
- `apps/api/schemas.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_modelos_truth_contract.py`

Archivos opcionales solo si el rojo lo exige:

- `apps/api/tests/test_smoke.py`
- `apps/api/routers/modelos.py`
- `scripts/tests/test_aeat_seed_canonical_flow.py`

## Fuera de alcance

3.2 no debe:

- crear una tabla nueva para enlaces verificados
- cambiar la forma publica del payload de modelos
- reabrir 3.1 ni cambiar la ruta canonica AEAT de dos pasos
- introducir heuristicas nuevas para considerar fuerte un enlace dudoso
- completar todavia el gating global de `verified/completeness` de modelos mas alla del ocultamiento de enlaces debiles

Ese gating transversal queda para 3.3.

## Verificacion prevista

Verificacion minima secuencial aprobada para Windows:

- `python -m pytest scripts/tests/test_seed_modelo_articulo.py -q`
- `python -m pytest scripts/tests/test_aeat_seed_canonical_flow.py -q`
- `python -m pytest apps/api/tests/test_modelos_truth_contract.py -q`
- `python -m pytest apps/api/tests/test_smoke.py -q -k "test_modelo_articulos_endpoint"`
- `python -m pytest apps/api/tests/test_alembic_integrity.py -q`

Si alguno de esos tests obliga a ampliar el scope, la expansion debe seguir siendo minima y quedar justificada por fallo real, no por anticipacion.

## Riesgos y decisiones explicitas

- los conteos de `articulos_count` pueden bajar tras ocultar filas legacy; eso es una correccion, no una regresion
- cualquier doctrina relacionada que dependiera de enlaces debiles dejara de aparecer; tambien es una correccion
- el backfill de `(norma, numero)` en filas legacy no las convierte en fuertes; solo las vuelve auditables y coherentes con el `articulo_id` guardado
- si aparecen seeds o fixtures fuera del scope listado que sigan insertando `modelo_articulo` sin provenance fuerte, deben corregirse en el mismo slice porque romperian el objetivo de 3.2

## Criterio de cierre

3.2 se podra cerrar cuando se cumpla todo esto a la vez:

- ninguna escritura nueva a `modelo_articulo` del flujo canonico o del helper legacy use resolucion por `numero` solamente
- toda fila de `modelo_articulo` tenga `(norma, numero, metodo_enlace, confianza_enlace)` persistidos
- el runtime de modelos solo devuelva filas con provenance fuerte
- los tests del slice esten verdes con evidencia fresca
- el siguiente paso exacto del roadmap quede preparado para 3.3
