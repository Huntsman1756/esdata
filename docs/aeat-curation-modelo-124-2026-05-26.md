# Modelo 124 - Curacion documental AEAT P1 - 2026-05-26

## Alcance

Revision semantica del modelo 124 para decidir si puede pasar de estado no afirmable a una campana afirmable por MCP/API.

No se han modificado datos productivos, estados en base de datos, ni recursos expuestos. Este documento es una evidencia de curacion para revision humana.

## Estado MCP observado

Informe local de Hermes:

`C:\Users\rome_\.hermes-esdata-curator\reports\aeat-campaign-curation\modelo-124.md`

Campos relevantes observados:

| Campo | Valor |
| --- | --- |
| `campana_resolution_status` | `resolved_weak` |
| `campana_verification_level` | `inferred_internal` |
| `campana_safe_to_assert` | `false` |
| `campana_afirmable` | `null` |
| `campana_assertion_code` | `NOT_ASSERTABLE_INFERRED_INTERNAL` |
| `campana_candidata` | `2013` |
| `campana_evidence` | vacia |

Diagnostico inicial: el MCP no puede afirmar campana para el modelo 124. La campana `2013` es un dato persistido o inferido internamente, sin evidencia oficial directa asociada.

## Fuentes oficiales revisadas

| Fuente | URL | Hallazgo | Valor probatorio |
| --- | --- | --- | --- |
| Ficha AEAT GH05 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH05.shtml | Pagina oficial del procedimiento "Modelo 124". Indica lugar de presentacion telematica y plazo de presentacion por periodo de declaracion. No contiene ano de campana ni ejercicio vigente. | Prueba existencia/procedimiento, no prueba campana. |
| Disenos de registro AEAT 100-199 | https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-100-199.html | La pagina oficial lista: "Modelo 124. Ejercicios 2020 y siguientes. Presentacion por lotes." Ultima actualizacion visible: 13/mayo/2026. | Prueba cobertura tecnica oficial 2020 y siguientes para presentacion por lotes. No basta por si sola para afirmar `campana_activa`, pero invalida tratar 2013 como senal actual sin marcar stale/conflicto. |
| XLSX oficial de diseno | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/archivos_20/124v01e2020_v1.07.xlsx | HEAD HTTP 200. Tamano observado: 113149 bytes. Last-Modified observado: 2021-07-13 11:37:41 GMT. | Artefacto tecnico oficial enlazado desde AEAT. El nombre de fichero no es prueba fuerte aislada; su contexto oficial si apoya la cobertura tecnica 2020+. |
| BOE-A-2013-12385 | https://www.boe.es/buscar/act.php?id=BOE-A-2013-12385 | Orden HAP/2194/2013. Incluye el modelo 124 entre modelos afectados por reglas/procedimientos de presentacion electronica. | No prueba campana activa 2013. La fecha BOE no puede usarse como campana. |

## Evaluacion semantica

La evidencia oficial no permite afirmar que la campana activa del modelo 124 sea `2013`.

La pagina principal AEAT del procedimiento no publica una campana activa ni un ejercicio vigente. La fuente AEAT mas concreta localizada es la pagina de disenos de registro, que vincula el modelo 124 con "Ejercicios 2020 y siguientes" para presentacion por lotes. Esa evidencia es oficial y directa sobre cobertura tecnica de ejercicios, pero no es equivalente a una declaracion fiscal de "campana activa".

Por tanto:

- No procede `resolved_strong`.
- No procede `ASSERTABLE_DIRECT_OFFICIAL`.
- No procede rellenar `campana_afirmable`.
- No procede usar el BOE de 2013 para sostener la campana `2013`.
- Mantener el modelo como `resolved_weak` sin marca adicional oculta una senal oficial de obsolescencia.

## Decision recomendada

```text
modelo: 124
decision: no afirmable
recommended_status: stale_suspected
campana_afirmable: null
campana_safe_to_assert: false
campana_assertion_code: NOT_ASSERTABLE_INFERRED_INTERNAL
do_not_promote_to: resolved_strong
```

Si el detector de conflicto del sistema considera los anos de diseno tecnico AEAT como anos documentales relevantes, entonces el modelo 124 deberia escalarse a `conflict` por contradiccion entre `2013` persistido y evidencia AEAT "2020 y siguientes". Si no los considera prueba de campana, el estado minimo honesto es `stale_suspected`.

## Cambios de datos no aplicados

No se ha cambiado produccion. Para una futura remediacion controlada:

1. Registrar la pagina de disenos AEAT y el XLSX oficial como evidencia tecnica del modelo 124, con `proves_campaign=false`.
2. Anadir un rol probatorio explicito equivalente a `technical_exercise_coverage`, distinto de evidencia directa de campana.
3. Marcar el modelo 124 como `stale_suspected` o `conflict`, segun la politica final sobre anos tecnicos en deteccion de conflicto.
4. Mantener `campana_afirmable=null` hasta localizar texto oficial que vincule inequivamente modelo 124 y campana/ejercicio afirmable.

## Resultado

`UNKNOWN` para campana afirmable.

El primer caso P1 confirma que el contrato fail-closed es necesario: existe evidencia oficial reciente y relevante, pero no una prueba suficiente para afirmar campana activa. La mejora correcta no es promover el modelo, sino separar cobertura tecnica documentada de verdad fiscal afirmable.
