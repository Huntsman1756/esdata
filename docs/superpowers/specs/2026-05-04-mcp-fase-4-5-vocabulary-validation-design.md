# Diseno: MCP Fase 4.5 - Activar validacion real de vocabularios

## Objetivo

Activar validacion real del vocabulario controlado en los workers que escriben `documento_interpretativo`, de modo que los valores persistidos en campos clasificados no dependan de convenciones informales del worker.

La fase es deliberadamente estrecha:

- activa primero la validacion en los upserts de `documento_interpretativo`
- mantiene a los workers como runtime no bloqueante
- corrige por fallback explicito los valores fuera de vocabulario ya conocidos
- deja `norma` y otras tablas para un slice posterior

El objetivo exacto es que la capa de ingestion deje de escribir valores fuera de `apps/workers/vocabulary.py` en campos como `tipo_documento`, `organismo_emisor`, `tipo_fuente`, `ambito`, `jurisdiccion` y `estado_vigencia` cuando exista una degradacion segura al vocabulario aprobado.

## Contexto

El plan MCP fija en `4.5` que hace falta activar validacion real de vocabularios.

Estado actual confirmado tras `4.4`:

- `apps/workers/vocabulary.py` ya es la fuente de verdad de vocabulario controlado.
- `apps/workers/vocabulary_validation.py` ya existe, con `safe_payload_value(...)` y `sanitize_payload(...)`.
- `apps/workers/tests/test_vocabulary_validation.py` ya cubre el helper en aislamiento.
- los workers no usan aun ese helper en sus upserts reales.
- `safe_payload_value(..., fallback=...)` expone un parametro `fallback`, pero hoy no lo aplica en runtime; si no hay mapping explicito, deja pasar el valor original.

El hueco real no es de ausencia de vocabulario. El hueco es de activacion:

- el repositorio ya tiene un contrato de vocabulario, pero los writers lo sortean
- varios workers emiten hoy valores fuera del vocabulario aprobado
- mientras la validacion no viva en el boundary de escritura, el contrato es solo documental y de tests unitarios

Valores fuera de vocabulario confirmados en esta rama:

- `bde.py` usa `organismo_emisor='Banco de España'` mientras el vocabulario actual admite `Banco de Espana`
- `cnmv.py` usa tipos y ambitos especificos no presentes en `VOCABULARY`, por ejemplo `general_cnmv`, `mercados_cnmv`, `reporting_regulatorio_cnmv`, `resolucion_cnmv`, `informe_cnmv`
- `cendoj.py` ya tiene un caso conocido (`TSJ`) que el helper resuelve por fallback, pero ese fallback no se activa aun desde el write path real

## Alcance aprobado

Primera activacion de `4.5`:

- activar validacion en los upserts de `documento_interpretativo`
- aplicar mappings explicitos a valores emitidos hoy por workers cubiertos
- registrar warning cuando un fallback se aplique
- no romper workers ni convertir invalidaciones de vocabulario en excepciones fatales

Archivos obligatorios del slice:

- `apps/workers/vocabulary_validation.py`
- `apps/workers/tests/test_vocabulary_validation.py`
- call sites de `upsert_documento_interpretativo(...)` en workers del slice
- tests de workers afectados
- `docs/master-execution-roadmap.md`
- `docs/operations/agent-notes.md`

Call sites previstos para esta primera activacion:

- `apps/workers/aepd.py`
- `apps/workers/bde.py`
- `apps/workers/bdns.py`
- `apps/workers/cendoj.py`
- `apps/workers/cnmv.py`
- `apps/workers/dgt.py`
- `apps/workers/sepblac.py`
- `apps/workers/teac.py`

## Enfoques considerados

### Opcion 1 - activar validacion en el boundary de cada upsert real

Cada worker materializa primero el payload final que va a persistir, lo sanea con un helper compartido y solo despues ejecuta el `INSERT ... ON CONFLICT`.

Ventajas:

- cambio pequeno y reversible
- corrige el problema donde realmente nace: el write boundary
- no exige refactor estructural ni migracion
- permite usar fallbacks especificos por worker cuando haga falta

Inconvenientes:

- toca varios archivos de workers
- la disciplina de llamada debe mantenerse en futuros workers nuevos

### Opcion 2 - introducir un helper central nuevo de upsert para `documento_interpretativo`

Crear una capa compartida que construya y persista todos los writes de `documento_interpretativo` desde un solo punto.

Ventajas:

- frontera unica de validacion
- menos riesgo de drift futuro

Inconvenientes:

- slice mas grande
- obliga a refactorizar varios workers de golpe
- mezcla activacion de vocabulario con una consolidacion arquitectonica no necesaria para esta fase

### Opcion 3 - expandir el vocabulario para aceptar los valores que hoy emiten los workers

En lugar de mapear, anadir al vocabulario los valores actuales y dejar el runtime de workers casi intacto.

Ventajas:

- menos cambios en call sites

Inconvenientes:

- debilita el objetivo de `4.5`
- convierte heuristicas locales de cada worker en contrato oficial del repo
- aplaza la normalizacion semantica que la fase quiere activar

## Decision aprobada

Se aprueba la opcion 1.

`4.5` activara validacion en los write boundaries reales de `documento_interpretativo`, reusando `apps/workers/vocabulary_validation.py` y aplicando fallbacks explicitos hacia valores ya permitidos por `apps/workers/vocabulary.py`.

## Contrato aprobado

La fase adopta una regla unica:

- si un worker produce un valor fuera de vocabulario y existe una degradacion semanticamente segura a un valor aprobado, el worker debe persistir ese valor aprobado y registrar warning

Regla complementaria:

- si el worker ya produce un valor admitido por `VOCABULARY`, la validacion debe ser no-op

Campos cubiertos en este slice cuando aparezcan en payload final:

- `tipo_documento`
- `organismo_emisor`
- `jurisdiccion`
- `tipo_fuente`
- `ambito`
- `estado_vigencia`

La validacion debe ejecutarse despues de materializar defaults y constantes del worker, no antes.

## Runtime aprobado

### `apps/workers/vocabulary_validation.py`

El helper deja de ser solo decorativo y pasa a ser utilizable en runtime real.

Cambios aprobados:

- hacer efectivo el parametro `fallback` de `safe_payload_value(...)`
- permitir que `sanitize_payload(...)` reciba fallbacks por campo para el payload concreto del worker
- anadir un wrapper pequeno para documentos, por ejemplo un conjunto `DOCUMENTO_VOCAB_FIELDS` y/o helper equivalente, para no duplicar los mismos campos en todos los call sites

Contrato aprobado de degradacion:

1. valor valido -> se conserva
2. valor invalido con mapping explicito en `WORKER_FALLBACKS` -> se usa el mapping
3. valor invalido sin mapping explicito pero con fallback por campo valido -> se usa ese fallback
4. si no existe mapping seguro en este slice -> el caso queda fuera de alcance del worker o del campo concreto y no debe forzarse un valor enganoso

La fase no aprueba convertir una clasificacion invalida en una excepcion fatal.

### Call sites `upsert_documento_interpretativo(...)`

Regla aprobada:

- cada upsert debe construir un `record` o `payload` final con todos los valores que realmente irian a DB
- ese `record` se sanea con el helper compartido
- el SQL usa placeholders y valores saneados, no literales hardcodeados fuera del proceso de validacion

Esto es especialmente importante en workers que hoy fijan literales directamente en SQL, como:

- `bde.py`
- `aepd.py`
- `bdns.py`
- `teac.py`
- `sepblac.py`

Los workers con upsert dinamico (`dgt.py`, `cnmv.py`) deben sanear el payload despues de `setdefault(...)` y antes de construir la lista de columnas.

## Mappings aprobados en este slice

### `organismo_emisor`

- `Banco de España` -> `Banco de Espana`
- `TSJ` -> `Tribunal Supremo` (mapping ya existente; ahora debe vivir tambien en call site real)

### `tipo_documento` CNMV

Tipos CNMV fuera del vocabulario especifico se degradan a buckets ya permitidos:

- `resolucion_cnmv` -> `documento_cnmv`
- `codigo_conducta_cnmv` -> `documento_cnmv`
- `codigo_autoregulacion_cnmv` -> `documento_cnmv`
- `informe_anual_cnmv` -> `documento_cnmv`
- `informe_cnmv` -> `documento_cnmv`
- `instruccion_tecnica_cnmv` -> `documento_cnmv`
- `dictamen_cnmv` -> `documento_cnmv`
- `modelo_comunicacion_cnmv` -> `documento_cnmv`
- `decision_supervision_cnmv` -> `documento_cnmv`
- `estadistica_mercado_cnmv` -> `documento_cnmv`
- `reglamento_cnmv` -> `documento_cnmv`
- `circ_asesoramiento_cnmv` -> `circular_cnmv`

`circular_cnmv`, `manual_cnmv`, `guia_cnmv` y `documento_cnmv` ya validos deben permanecer intactos.

### `ambito` CNMV

Ambitos CNMV fuera de `VOCABULARY` se degradan a buckets ya admitidos:

- `general_cnmv` -> `mercados`
- `mercados_cnmv` -> `mercados`
- `reporting_regulatorio_cnmv` -> `reporting_regulatorio`
- `reporting_financiero_cnmv` -> `reporting_financiero`
- `infraestructuras_cnmv` -> `infraestructuras_mercado`
- `gobierno_corporativo` -> `mercados`
- `proteccion_inversor_cnmv` -> `mercados`
- `sanciones_cnmv` -> `mercados`
- `pgc_cnmv` -> `reporting_financiero`
- `transparencia_emisores` -> `disclosure_ue`
- `mifid_ii` -> `mercados_financieros_ue`
- `mifir` -> `mercados_financieros_ue`
- `mar` -> `abuso_mercado_ue`
- `dora` -> `resiliencia_digital_ue`
- `priips` -> `mercados_financieros_ue`

`reporting_regulatorio`, `reporting_financiero`, `infraestructuras_mercado` y `mercados` ya validos deben permanecer intactos.

## Estrategia de tests aprobada

La implementacion se hace con TDD.

Casos minimos a fijar:

1. `vocabulary_validation`: `fallback=` deja de ser ignorado
2. `vocabulary_validation`: `sanitize_payload(...)` usa mappings explicitos y fallbacks por campo
3. `bde`: el upsert persiste `Banco de Espana` aunque el payload/build siga produciendo `Banco de España`
4. `cnmv`: el upsert persiste `tipo_documento` y `ambito` ya saneados hacia buckets permitidos
5. `cendoj`: el caso `TSJ` deja de depender solo del test unitario del helper y queda cubierto en un call site real
6. workers ya validos (`dgt`, `teac`, `aepd`, `sepblac`, `bdns`) siguen verdes y no cambian payloads correctos

La cobertura puede vivir en:

- `apps/workers/tests/test_vocabulary_validation.py`
- tests especificos de workers ya existentes (`test_bde.py`, `test_cnmv.py`, `test_cendoj.py`, y otros si el call site cambia)

## Fuera de alcance

Este primer slice de `4.5` no debe:

- activar validacion sobre `norma` o sus upserts (`boe.py`, `eurlex.py`, etc.)
- introducir migraciones nuevas
- cambiar el schema publico del API o de las tablas
- convertir warnings de vocabulario en errores fatales de sync
- usar `4.5` para redisenar la arquitectura de todos los upserts de workers
- expandir `VOCABULARY` para absorber valores legacy de workers en vez de normalizarlos

Caso explicitamente fuera de alcance en este primer slice:

- `borme.py` cuando cae al tipo generico `acto_societario`. Ese valor no tiene hoy un bucket permitido y semanticamente seguro dentro de `TIPOS_DOCUMENTO_BORME`, asi que no se fuerza un mapping enganoso en este slice. Los tipos BORME ya especificos (`nombramiento`, `cese`, `constitucion`, `cambio_domicilio`, `ampliacion_capital`, `reduccion_capital`, `disolucion`, `concurso`) siguen siendo validos y no requieren cambio.

## Riesgos y decisiones explicitas

- `4.5` no busca perfeccion taxonomica absoluta; busca que los writes reales respeten el vocabulario ya aprobado cuando existe una degradacion segura
- la activacion per-worker es repetitiva pero aceptable porque evita un refactor estructural mayor en la misma fase
- si aparece un nuevo valor fuera de vocabulario en un worker cubierto y no existe mapping seguro, el fix correcto no es inventar una equivalencia debil; debe quedar como follow-up explicito
- el primer slice acepta buckets amplios para CNMV (`documento_cnmv`, `mercados`, `mercados_financieros_ue`, etc.) porque son menos enganiossos que persistir taxonomias locales no aprobadas

## Criterio de cierre

`4.5` se podra cerrar en este primer slice cuando:

- `vocabulary_validation.py` deje de ignorar `fallback=` y pueda sanear payloads reales
- los upserts cubiertos de `documento_interpretativo` usen el helper en su boundary de escritura
- los valores actualmente fuera de vocabulario y dentro del scope cubierto degraden a valores ya permitidos por `VOCABULARY`
- existan tests rojos->verdes de helper y call sites reales
- la evidencia fresca del slice deje claro que el runtime sigue no bloqueante y que no se han cambiado tablas fuera del alcance aprobado
