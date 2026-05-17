# Sprint E Coverage Report

Fecha: 2026-05-17  
Rama: `feat/sprint-e-aplicabilidad-completa`  
Fuente: SQL real de VPS (`docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql`)

## Cobertura Por Perfil

| perfil | supervisor | total | verified | evidence_limited | pct_verified |
|---|---:|---:|---:|---:|---:|
| empresa_servicios_pago | BDE | 10 | 9 | 1 | 90.0 |
| entidad_credito | BDE | 27 | 24 | 3 | 88.9 |
| agencia_valores | CNMV | 26 | 18 | 8 | 69.2 |
| eaf | CNMV | 20 | 18 | 2 | 90.0 |
| sgiic | CNMV | 22 | 16 | 6 | 72.7 |
| sociedad_valores | CNMV | 28 | 20 | 8 | 71.4 |

## Totales

| metrica | valor |
|---|---:|
| perfiles activos con obligaciones | 6 |
| obligacion_perfil total | 133 |
| obligacion_fuente total | 207 |
| normas UE con CELEX | 15 |

## Herramientas MCP Relevantes

| tool | estado |
|---|---|
| `listar_perfiles_entidad` | registrada |
| `obtener_obligaciones_perfil` | registrada |
| `calendario_obligaciones_perfil` | registrada |
| `buscar_norma_eu` | registrada |

## Correcciones De Fuente

El prompt inicial incluia dos referencias BOE incorrectas. Sprint E usa las fuentes oficiales correctas:

| codigo | fuente correcta | nota |
|---|---|---|
| `LEY10_2014` | `BOE-A-2014-6726` | Ley 10/2014 de ordenacion, supervision y solvencia de entidades de credito |
| `RD19_2018` | `BOE-A-2018-16036` | Real Decreto-ley 19/2018 de servicios de pago |
| `32015L2366` | `CELEX:32015L2366` | PSD2 en EUR-Lex |

## Caveats

- `evidence_limited` se mantiene cuando la obligacion depende de actividad concreta, umbral o articulo nacional pendiente de granularidad.
- `empresa_servicios_pago` incluye PBC/FT como condicional por volumen/actividad.
- `agencia_valores` conserva caveat de no custodia conforme al contrato operativo del perfil.
- No se fuerza `verified=true` para obligaciones condicionales aunque exista fuente oficial general.
