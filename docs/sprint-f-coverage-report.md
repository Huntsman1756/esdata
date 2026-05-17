# Sprint F Coverage Report

Fecha: 2026-05-17  
Rama: `feat/sprint-f-evidence-limited`  
Fuente: SQL real de VPS (`docker compose exec postgres psql`)

## Cobertura Por Perfil

| perfil | total | verified | evidence_limited | pct_verified |
|---|---:|---:|---:|---:|
| agencia_valores | 26 | 26 | 0 | 100.0 |
| eaf | 20 | 20 | 0 | 100.0 |
| empresa_servicios_pago | 10 | 10 | 0 | 100.0 |
| entidad_credito | 27 | 27 | 0 | 100.0 |
| sgiic | 21 | 21 | 0 | 100.0 |
| sociedad_valores | 28 | 28 | 0 | 100.0 |

## Totales

| metrica | valor |
|---|---:|
| perfiles activos con obligaciones | 6 |
| obligacion_perfil total | 132 |
| verified total | 132 |
| evidence_limited total | 0 |

## Correcciones Confirmadas

| bloque | correccion aplicada | fuente primaria |
|---|---|---|
| Prudencial ESI | `sociedad_valores` y `agencia_valores` usan IFR `32019R2033 art. 11`, no CRR | EUR-Lex `CELEX:32019R2033` |
| IFD complementaria | cargada `32019L2034` en `norma` | EUR-Lex `CELEX:32019L2034` |
| Conflictos/mejor ejecucion | texto vigente usa `LIVMC art. 208 bis` y `arts. 221 y 222` | BOE `BOE-A-2015-11435` |
| Modelo 187 | base confirmada en `RD_1082_2012 art. 150`, no art. 24 | BOE `BOE-A-2012-9716` |
| Modelo 198 | base confirmada en `LGT art. 93`, no LIRPF art. 93 | BOE `BOE-A-2003-23186` |
| Modelo 289 CRS | base confirmada en `LGT DA 22. ap. 1`, no art. 93 bis | BOE `BOE-A-2003-23186` |
| Modelo 290 FATCA | base confirmada en `LGT DA 22. ap. 8` | BOE `BOE-A-2003-23186` |
| Certificacion MiFID II | `32014L0065 art. 25.1` | EUR-Lex `CELEX:32014L0065` |
| SGIIC Annex IV | duplicado consolidado; queda una obligacion `art. 24 + Annex IV` | EUR-Lex `CELEX:32011L0061` |
| Empresa servicios pago PBC/FT | `LEY10_2010 art. 2.1.h` | BOE `BOE-A-2010-6737` |

## SQL Ejecutado Para Diagnostico

```sql
SELECT perfil_codigo,
       COUNT(*) total,
       SUM(CASE WHEN verified THEN 1 ELSE 0 END) verified,
       SUM(CASE WHEN NOT verified THEN 1 ELSE 0 END) evidence_limited,
       ROUND(100.0 * SUM(CASE WHEN verified THEN 1 ELSE 0 END)
         / NULLIF(COUNT(*), 0), 1) pct_verified
FROM obligacion_perfil
GROUP BY perfil_codigo
ORDER BY perfil_codigo;
```

Consulta residual:

```sql
SELECT id, perfil_codigo, descripcion, norma_codigo, articulo_referencia,
       verified, completeness, notas
FROM obligacion_perfil
WHERE verified = false
ORDER BY perfil_codigo, id;
```

Resultado residual: `0` filas.
