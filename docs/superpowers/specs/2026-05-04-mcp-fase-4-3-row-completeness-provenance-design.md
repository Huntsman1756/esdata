# Diseno: MCP Fase 4.3 - Completeness y provenance por fila

## Objetivo

Persistir senales minimas de completeness y provenance por fila para las superficies de datos que controlan los workers tocados en `4.2`, sin mezclar esa semantica con el estado transitorio del run ni con el estado de revision.

La fase es deliberadamente estrecha:

- afecta primero a `AEAT`, `CNMV` y `DGT`
- es `persistence-first`
- no cambia todavia el contrato observable de `/v1/sources/manifest` ni `/v1/sources/freshness`

El objetivo exacto es dejar un contrato persistido y reutilizable que permita distinguir, fila a fila, entre `artefacto completo para uso operativo` y `artefacto parcial o con provenance debil`, sin volver a sobrecargar `source_revision`.

## Contexto

El plan MCP fija en `4.3` que hace falta materializar completeness y provenance por fila.

Estado actual confirmado tras `4.2`:

- `sync_log` ya distingue mejor entre `ok`, `partial` y `error`, pero esa semantica sigue siendo de run, no de fila.
- `source_revision` ya vuelve a tener una responsabilidad unica: guardar la ultima revision real conocida para change detection.
- `source_manifest` y `source_freshness_snapshot` hoy operan a nivel de fuente/worker, no a nivel de fila.
- `modelo_recurso` ya guarda senales fuertes de fuente oficial y versionado por hash para AEAT.
- `documento_interpretativo` es la superficie persistida usada por `CNMV` y `DGT`, pero hoy no deja una senal pequena y uniforme de completeness/provenance por fila.

El hueco real es que hoy una fila persistida puede existir y ser tecnicamente usable por retrieval o por una API futura sin dejar claro si representa:

- una captura oficial y completa
- una captura oficial pero parcial
- una fila best-effort o con evidence/provenance insuficiente

## Decisiones de diseno

Se adopta un enfoque de columnas minimas en las tablas duenas de la fila, no una tabla generica nueva y no `source_revision`.

La fase se apoya en cuatro reglas:

1. completeness por fila y status de sync son cosas distintas
2. provenance por fila y revision por hash son cosas distintas
3. la semantica debe vivir junto a la fila a la que describe
4. el primer slice debe cubrir solo `AEAT`, `CNMV` y `DGT`

## Alcance aprobado

Archivos obligatorios:

- nueva migracion Alembic
- `apps/workers/aeat_models.py`
- `apps/workers/cnmv.py`
- `apps/workers/dgt.py`
- `apps/api/services/source_manifest.py`
- `apps/api/routers/source_manifest.py`
- tests de workers/API afectados
- `docs/master-execution-roadmap.md`
- `docs/operations/agent-notes.md`

Archivos documentales de esta fase:

- `docs/superpowers/specs/2026-05-04-mcp-fase-4-3-row-completeness-provenance-design.md`

## Enfoques considerados

### Opcion 1 - columnas minimas en tablas existentes

Anadir columnas pequenas de completeness/provenance en:

- `modelo_recurso`
- `documento_interpretativo`

Ventajas:

- cambio pequeno y alineado con los owners actuales de cada fila
- evita crear una capa paralela de joins para saber si una fila es util
- mantiene `source_revision` limpio y con una sola responsabilidad

Inconvenientes:

- la agregacion futura para `source_manifest` tendra que consultar tablas por fuente
- la semantica se replica en dos superficies persistidas distintas

### Opcion 2 - tabla generica de row-quality

Crear una tabla nueva tipo ledger con llave generica por worker/entidad y poner ahi completeness/provenance.

Ventajas:

- futura agregacion mas uniforme
- posible extension a mas workers sin tocar cada tabla base

Inconvenientes:

- slice mas grande
- facil introducir drift entre la fila real y su fila de calidad
- riesgo de recrear el problema de responsabilidad mezclada que `4.1` acaba de corregir

### Opcion 3 - extender `source_revision`

Usar `source_revision` para meter tambien completeness/provenance.

Esta opcion queda descartada.

Motivo:

- `source_revision` representa revision tecnica de contenido y deteccion de cambios
- `4.1` acaba de reforzar ese boundary
- mezclar revision y row-quality reabre el mismo problema de sobrecarga semantica

## Decision aprobada

Se aprueba la opcion 1.

`4.3` anadira columnas minimas de row-quality directamente en las tablas persistidas que ya representan el artefacto final de `AEAT`, `CNMV` y `DGT`.

## Contrato persistido aprobado

La fase introduce dos campos minimos por fila:

- `row_completeness`
- `row_provenance`

Se evita, en este slice, anadir una taxonomia rica de notas, scoring probabilistico o dimensiones extra.

### `row_completeness`

Semantica:

- `complete`: la fila representa el artefacto esperado de esta fuente sin huecos materiales conocidos para el uso operativo previsto
- `partial`: la fila existe, pero el worker sabe que la captura quedo incompleta o limitada para ese artefacto

### `row_provenance`

Semantica:

- `official_exact`: la fila proviene de un artefacto oficial recuperado de forma directa y suficiente para esa superficie
- `official_best_effort`: la fila existe y viene de fuente oficial, pero la construccion del contenido, el linking o la cobertura no alcanzan el nivel mas fuerte del contrato

La fase no introduce de momento valores `curated`, `manual`, `llm` ni taxonomias mas finas porque este slice se limita a workers con ingest oficial.

## Tablas afectadas

### `modelo_recurso`

Se anaden:

- `row_completeness TEXT NOT NULL`
- `row_provenance TEXT NOT NULL`

Contrato inicial esperado:

- recurso oficial descargado y persistido con payload util -> `complete`, `official_exact`
- esta fase no debe forzar la persistencia de filas placeholder o sinteticas para recursos que nunca se descargaron

Resultado:

- `AEAT` seguira reflejando huecos en `sync_log` via `4.2`
- y las filas efectivamente persistidas dejaran explicito si son completas y con provenance fuerte

### `documento_interpretativo`

Se anaden:

- `row_completeness TEXT NOT NULL`
- `row_provenance TEXT NOT NULL`

Contrato inicial esperado:

- `CNMV`: documento oficial recuperado y parseado -> `complete`, `official_exact`
- `DGT`: consulta oficial recuperada y parseada correctamente -> `complete`, `official_exact`
- si un futuro caso persiste una fila a partir de un recovery o construccion parcial, debera marcarse `partial` o `official_best_effort` segun corresponda

Esta fase no obliga a fabricar filas parciales nuevas solo para demostrar la taxonomia. Basta con que las columnas existan y que el path actual fuerte escriba los valores fuertes correctos.

## Migracion aprobada

La migracion debe:

1. anadir `row_completeness` y `row_provenance` a `modelo_recurso`
2. anadir `row_completeness` y `row_provenance` a `documento_interpretativo`
3. backfillear filas existentes con el valor mas conservador compatible con el estado actual
4. dejar ambos campos `NOT NULL`
5. anadir `CHECK` constraints pequenas sobre el conjunto permitido de valores

### Backfill aprobado

Para no vender mas certeza historica de la que ya existe:

- `modelo_recurso` existente -> `complete`, `official_exact`
- `documento_interpretativo` existente -> `partial`, `official_best_effort`

Justificacion:

- en `AEAT`, `modelo_recurso` ya nace de recursos oficiales versionados por hash y es una superficie mas estrecha y fuerte
- en `documento_interpretativo`, el repo mezcla varias fuentes y versiones historicas; por eso el backfill debe empezar en `partial` + `official_best_effort`, y solo los nuevos writes de `CNMV`/`DGT` podran elevarse a `complete` + `official_exact`

## Runtime aprobado

### AEAT

`apps/workers/aeat_models.py` debe escribir siempre `row_completeness='complete'` y `row_provenance='official_exact'` al insertar o rotar una fila nueva de `modelo_recurso` a partir de un recurso oficial realmente descargado.

No se persistiran filas parciales de recurso solo porque el run haya acabado `partial`; los recursos faltantes siguen perteneciendo a la semantica de `sync_log`, no a una fila inventada.

### CNMV

`apps/workers/cnmv.py` debe escribir `row_completeness='complete'` y `row_provenance='official_exact'` cuando persiste o actualiza `documento_interpretativo` desde un documento oficial recuperado con exito.

Los fallos por URL que hoy degradan el run a `partial` no deben crear filas placeholder en `documento_interpretativo`.

### DGT

`apps/workers/dgt.py` debe escribir `row_completeness='complete'` y `row_provenance='official_exact'` cuando persiste una consulta oficial recuperada y parseada con exito.

Los casos `search` sin resultados o documentos fuera de target no deben crear filas placeholder solo para marcar `partial`; siguen siendo semantica de run/cola.

## `source_manifest` en 4.3

`apps/api/services/source_manifest.py` y `apps/api/routers/source_manifest.py` se mantienen funcionalmente estables en este slice.

La unica accion aprobada en esta fase es dejar claro, en codigo o comentarios si hace falta, que `source_manifest` sigue operando a nivel fuente/worker y no consume todavia las nuevas columnas row-level.

No se anaden:

- contadores agregados por `row_completeness`
- porcentajes de cobertura por fuente
- nuevos campos JSON en `/v1/sources/manifest`
- nuevos campos JSON en `/v1/sources/freshness`

Ese cableado queda para un slice posterior, una vez validada la semantica persistida.

## Estrategia de tests aprobada

La implementacion se hace con TDD.

Casos minimos a fijar:

1. migracion Alembic: existen las columnas nuevas y los `CHECK` constraints esperados
2. `AEAT`: una fila nueva de `modelo_recurso` queda con `row_completeness='complete'` y `row_provenance='official_exact'`
3. `CNMV`: una fila nueva/actualizada de `documento_interpretativo` queda con los mismos valores fuertes
4. `DGT`: una fila nueva/actualizada de `documento_interpretativo` queda con los mismos valores fuertes
5. `source_manifest`: su payload sigue estable y no incorpora todavia agregados row-level

La cobertura puede vivir en:

- `apps/api/tests/test_alembic_integrity.py`
- `apps/workers/tests/test_aeat_models.py`
- `apps/workers/tests/test_cnmv.py`
- `apps/workers/tests/test_dgt.py`
- `apps/api/tests/test_source_manifest.py`

## Fuera de alcance

`4.3` no debe:

- crear una tabla generica nueva de row-quality
- tocar `source_revision` para meter completeness/provenance
- cambiar el contrato HTTP de `source_manifest`
- crear filas placeholder para recursos o documentos faltantes
- anadir scoring fino o taxonomias amplias de provenance
- generalizar todavia a todos los workers del repo

## Riesgos y decisiones explicitas

- el backfill conservador de `documento_interpretativo` evita afirmar `official_exact` sobre historico que no fue escrito con este contrato
- el hecho de que hoy los nuevos writes de `CNMV` y `DGT` sean `official_exact` no obliga a re-etiquetar todo el historico con esa misma fuerza
- mantener `source_manifest` estable en `4.3` reduce riesgo de API drift y deja la agregacion para una fase posterior con evidencia real
- `row_completeness='partial'` queda disponible desde ya, pero este slice no necesita forzar escenarios artificiales de persistencia parcial si el runtime actual no persiste esas filas

## Criterio de cierre

`4.3` se podra cerrar cuando:

- exista la migracion con las dos columnas nuevas en `modelo_recurso` y `documento_interpretativo`
- `AEAT`, `CNMV` y `DGT` escriban esos campos en los paths de persistencia exitosos
- el historico quede backfilleado de forma conservadora
- `source_manifest` siga estable y explicitamente fuera del cableado row-level en este slice
- haya evidencia fresca de tests del scope afectado
- el roadmap deje el siguiente paso exacto hacia la agregacion/API posterior o el siguiente slice MCP decidido
