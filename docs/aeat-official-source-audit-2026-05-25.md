# Auditoria AEAT fuentes oficiales - 2026-05-25

## Resultado

Estado: `partial_with_findings`.

Se auditaron en vivo las fuentes oficiales AEAT/BOE activas cargadas para
modelos AEAT en produccion. El resultado no muestra errores duros de descarga
en los recursos oficiales activos comprobados, pero si deja un residuo
operativo importante: `15` modelos tienen `campana_activa` antigua o implausible
y tambien casillas/campos activos. Esos modelos no deben
tratarse como "ultima version validada" hasta revisar su contrato documental
modelo a modelo.

Artefacto machine-readable:

- `docs/aeat-official-source-audit-2026-05-25.json`

## Alcance

- Fecha de auditoria: `2026-05-25`.
- Modelos AEAT activos auditados: `217`.
- Modelos con casillas/campos activos: `56`.
- Recursos oficiales exportados desde produccion: `1219`.
- URLs oficiales unicas comprobadas en vivo: `718`.
- URLs oficiales comprobadas con HTTP `200`: `718`.
- Recursos activos de los `15` P1: `93`; todos quedan incluidos en el barrido
  de URLs vivas.

Fuentes consideradas oficiales en esta auditoria:

- AEAT Sede: paginas `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/...`.
- AEAT Sede: recursos enlazados desde `modelo_recurso` activo.
- BOE: normas y disposiciones BOE registradas como recursos activos.

No se uso texto LLM como fuente de verdad.

## Criterios

- `P0`: recurso oficial activo roto, inaccesible o imposible de recuperar en vivo.
- `P1`: modelo con casillas/campos activos y `campana_activa` numerica antigua
  (`< 2024`) o implausible (`< 1990` o posterior a la fecha de auditoria).
  Riesgo directo para respuestas MCP porque el usuario ve una campana
  aparentemente obsoleta junto con campos estructurados.
- `P2`: `campana_activa` numerica implausible sin casillas/campos activos.
- `P3`: modelo con `campana_activa` numerica antigua pero sin casillas/campos
  activos. Riesgo menor de metadata, no de campos publicados.

## Resumen de hallazgos

| Severidad | Total | Interpretacion |
| --- | ---: | --- |
| `P0` | 0 | No se detectaron recursos oficiales activos rotos en el alcance comprobado. |
| `P1` | 15 | Campana antigua o implausible activa en modelos con campos/casillas activos. Requiere revision antes de confiar en MCP. |
| `P2` | 1 | Campana implausible sin campos/casillas activos (`600=1927`). |
| `P3` | 97 | Campana antigua activa sin campos/casillas activos. Residuo de metadata historica. |

Tipos detectados:

| Tipo | Total |
| --- | ---: |
| `old_active_campaign_with_fields` | 14 |
| `implausible_active_campaign_with_fields` | 1 |
| `implausible_active_campaign_no_fields` | 1 |
| `old_active_campaign_no_fields` | 97 |

## Hallazgos P1

Estos son los modelos que requieren tratamiento prioritario antes de afirmar
que el corpus AEAT completo esta actualizado:

| Modelo | Campana activa | Casillas/campos activos | Pagina oficial |
| --- | ---: | ---: | --- |
| `217` | `1922` | 106 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GE06.shtml |
| `113` | `2015` | 89 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G614.shtml |
| `122` | `2015` | 54 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G617.shtml |
| `124` | `2013` | 39 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH05.shtml |
| `126` | `2013` | 44 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH06.shtml |
| `128` | `2013` | 39 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH07.shtml |
| `145` | `2015` | 59 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G603.shtml |
| `210` | `2019` | 167 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF00.shtml |
| `111` | `2020` | 63 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH01.shtml |
| `115` | `2020` | 37 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH02.shtml |
| `117` | `2020` | 43 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GH03.shtml |
| `237` | `2021` | 42 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GE08.shtml |
| `211` | `2023` | 314 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF01.shtml |
| `213` | `2023` | 294 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF03.shtml |
| `226` | `2015` | 96 | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF08.shtml |

## Interpretacion operativa

- Los modelos `172`, `173`, `289` y `290` quedan fuera de los hallazgos P1 de
  esta auditoria: las incidencias recientes de `campana_activa=2013`/ZIP obsoleto
  ya no aparecen en el barrido vivo.
- Los modelos `149`, `151`, `231`, `232` y `282` aparecen ya con
  `campana_activa=2025` en el VPS actual; estaban en una foto previa y se
  excluyen del P1 vigente tras recalcular desde produccion.
- No hay base para decir que "todo AEAT esta validado a ultima version": quedan
  `15` modelos con campos activos y campana antigua/implausible que deben revisarse uno por
  uno contra su pagina y recursos oficiales.
- Los `97` hallazgos P3 son menos urgentes porque no exponen campos activos,
  pero siguen siendo deuda de metadata si el usuario consulta campana activa.
- `217=1922` y `600=1927` confirman que el problema no es solo "campana antigua":
  son valores implausibles que el escritor no debe aceptar como campana operativa.
- La causa probable es historica: inferir `modelo_campana.campana` desde el
  primer ano libre de la pagina AEAT mezcla anos de normativa, version de
  formulario, ejercicio de presentacion y fechas de ayuda.

## Metodologia de campana

Campo auditado: `modelo_campana.campana` con `modelo_campana.activo=true`.

Escritor actual: `apps/workers/aeat_models.py::_infer_campaign`.

Orden de inferencia observado antes del guardrail:

- excepciones de ejercicio anterior para `GI38`, `GI42`, `GI53`, `GI54`;
- primer ano `19xx/20xx` en `url_info`;
- primer ano tras texto `campana`/`ejercicio`;
- primer ano libre `19xx/20xx` del texto de pagina;
- si no hay ano, `current`.

Riesgo de reintroduccion: sin validar rango, una pagina con una referencia
historica como `1922` puede volver a crear o activar una campana falsa tras el
siguiente sync.

## Siguiente paso seguro

Ejecutar una remediacion acotada sobre los `15` P1. Para cada modelo:

- comprobar pagina AEAT viva y recursos oficiales asociados;
- distinguir ejercicio de declaracion, campana operativa y version tecnica;
- migrar solo cuando exista evidencia determinista;
- si no existe evidencia suficiente, marcar el modelo como parcial/fail-closed
  en vez de inventar una campana actual.
