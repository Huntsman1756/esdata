# Contrato minimo de campana activa AEAT - 2026-05-25

## Estado

Estado: `target_contract`.

Este documento define el contrato semantico minimo para poder tratar
`modelo_campana.campana` como `campana_activa` fiable en MCP. No declara el
dataset AEAT completo como actualizado: tras la auditoria oficial del
2026-05-25 quedan `15` P1 con campos activos y campana antigua/implausible.

## Definicion

`campana_activa` no significa "primer ano que aparece en la pagina AEAT".

Debe significar:

- el ejercicio/campana que AEAT presenta como vigente para el modelo;
- o, si AEAT no publica una campana textual unica, el ejercicio de declaracion
  que queda determinado por una fuente oficial primaria;
- o `fail_closed`/`low` si solo hay inferencia heuristica.

No debe mezclarse con:

- ano de una orden ministerial;
- ano de una norma BOE historica;
- version tecnica de XSD/WSDL/manual;
- fecha de ultima actualizacion de la pagina;
- fecha de plazo de presentacion sin relacion explicita con ejercicio.

## Niveles de confianza

| Nivel | Uso MCP | Criterio minimo |
| --- | --- | --- |
| `high` | Puede mostrarse como campana activa fiable. | Fuente AEAT explicita con texto de campana/ejercicio vigente o recurso oficial anual que identifica inequivocamente el ejercicio declarado. |
| `medium` | Puede mostrarse con aviso de revision. | Inferencia determinista desde plazo/recurso oficial + regla documentada por familia de modelo, sin conflicto con otros recursos. |
| `low` | No usar como "ultima version"; mostrar como metadata no verificada. | Ano plausible detectado por HTML/URL sin contrato documental explicito. |
| `fail_closed` | No afirmar campana vigente. | Conflicto entre fuentes, ausencia de fuente determinista o valor implausible. |

## Orden de fuentes permitido

1. Texto oficial AEAT que diga literalmente campana o ejercicio del modelo.
2. Recurso oficial AEAT del propio modelo que determine el ejercicio presentado
   (por ejemplo XSD/servicio anual con contrato documental conocido).
3. Regla familiar documentada y testeada, como declaraciones informativas
   anuales cuyo ejercicio declarado es el ano inmediatamente anterior.
4. BOE solo como fuente auxiliar: sirve para norma base, no para fijar campana
   si no enlaza inequivocamente con el ejercicio de presentacion.
5. Heuristica HTML/URL solo puede producir `low`; nunca debe promover por si
   sola `verified=true`, `completeness='completa'` ni "ultima version".

Si dos fuentes oficiales apuntan a anos distintos, el estado correcto es
`fail_closed` hasta resolver manualmente el contrato documental.

## Campos minimos a persistir

`modelo_campana` no tiene hoy columnas para procedencia/confianza de la campana.
La siguiente migracion semantica debe anadir, como minimo:

- `campana_source_type`: `aeat_explicit`, `aeat_resource_rule`,
  `family_rule`, `heuristic_html`, `manual_curated`, `fail_closed`.
- `campana_source_url`: URL oficial que sustenta el valor.
- `campana_source_hash`: hash del contenido oficial usado, si aplica.
- `campana_confidence`: `high`, `medium`, `low`, `fail_closed`.
- `campana_derivation_rule`: identificador estable de la regla usada.
- `campana_review_required`: booleano.
- `campana_review_note`: texto breve para el caveat operativo.
- `campana_verified_at`: fecha/hora de verificacion.

Hasta que esos campos existan, cualquier campana derivada automaticamente por
`apps/workers/aeat_models.py::_infer_campaign` debe tratarse como no trazada.

## Reglas de escritura

- El writer no debe persistir anos numericos fuera de `1990..ano_actual`.
- El writer no debe activar una nueva campana si solo detecta un ano plausible
  por texto libre y ya existe una campana con campos activos, salvo que la
  fuente alcance `high` o `medium`.
- Si la fuente queda en `low`, el modelo puede conservar metadata, pero las
  respuestas MCP deben marcar revision requerida.
- Las excepciones por familia deben vivir en codigo y tests, no solo en docs.
- Toda promocion de P1 a resuelto debe registrar fuente, regla y evidencia.

## Priorizacion P1

Orden de remediacion semantica recomendado:

| Prioridad | Modelos | Motivo |
| --- | --- | --- |
| 1 | `217` | `1922` es implausible y tiene `106` campos activos. |
| 2 | `124`, `126`, `128` | Campana `2013` con campos activos; muy antigua y plausible a simple vista. |
| 3 | `113`, `122`, `145`, `226` | Campana `2015` con volumen medio/alto de campos. |
| 4 | `210` | Campana `2019` pero modelo masivo (`167` campos). |
| 5 | `111`, `115`, `117`, `237` | Campanas `2020`/`2021`, menor antiguedad relativa. |
| 6 | `211`, `213` | Campana `2023`; menor distancia, pero muchos campos y uso IRNR. |

## Claim permitido

Permitido:

- "Infraestructura de fuentes oficiales AEAT/BOE validada en el barrido
  2026-05-25."
- "Pipeline de ingestion saneado contra anos implausibles."
- "Dataset AEAT parcialmente fiable, con `15` inconsistencias criticas P1
  pendientes."

Prohibido:

- "Todo AEAT esta actualizado."
- "La campana activa de todos los modelos es fiable."
- "HTTP 200 valida contenido o actualidad semantica."
