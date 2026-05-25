# Obligacion perfil evidence recovery - Modelo 200 - 2026-05-25

Estado: COMPLETADO LOCAL / PENDIENTE VPS

Alcance Ralph: recuperar evidencia primaria normalizada para filas `obligacion_perfil` que estaban fail-closed, sin tocar contratos ni promover por analogia.

## RED productivo

Entorno: VPS `steamcases-vps`, commit `eebcf2b`, stack Docker Compose productivo.

Consulta read-only sobre filas fail-closed:

- `173` filas tienen `source_url`, `capture_date`, `source_hash=NULL`, `verified=false` y `safe_to_answer=false`.
- Matches exactos `obligacion_perfil.source_url = source_revision.dgt_url` con hash unico:
  - Modelo `200`: `6` filas, `source_entity_id='AEAT-MODELO-200'`, hash unico `e836e7b8c52e3411...`.
  - Modelo `303`: `5` filas, `source_entity_id='AEAT-MODELO-303'`, hash unico `1652be7bb6dce592...`.
  - Modelo `290`: `3` filas, misma URL con dos evidencias distintas (`FATCA` y `FATCA_IGA_ES`), por tanto no univoco.

## Decision

Se recupera solo Modelo 200:

- La URL persistida coincide exactamente con `source_revision.dgt_url`.
- `source_revision.source_entity_id='AEAT-MODELO-200'`.
- Hay un unico `content_hash_sha256` para esa fuente.
- Las filas ya estaban modeladas como `LIS art. 124`, `AUTOLIQUIDACION`, periodicidad anual y perfil entidad.

No se recupera Modelo 303:

- Aunque existe hash unico para la pagina AEAT del procedimiento, la aplicabilidad de IVA por perfil tiene caveats de actividad, exenciones o revision del supuesto concreto.
- La evidencia de pagina/modelo no convierte por si sola la fila de perfil en aplicabilidad exacta.

No se recupera Modelo 290:

- La URL FATCA tiene dos hashes distintos en `source_revision` (`FATCA` y `FATCA_IGA_ES`).
- No hay base univoca para poblar `obligacion_perfil.source_hash`.

## Cambio local

Revision Alembic:

```text
20260525_0099_obligacion_perfil_recover_200
```

La migracion:

- busca solo `source_entity_tipo='obligacion_regulatoria'`;
- exige `source_entity_id='AEAT-MODELO-200'`;
- exige `COUNT(DISTINCT content_hash_sha256)=1`;
- actualiza solo `modelo_aeat='200'` en los seis perfiles esperados;
- carga `source_hash` y conserva/usa `capture_date`;
- restaura `verified=true`, `safe_to_answer=true`, `completeness='completa'`;
- deja nota de recuperacion.

## Criterio de salida

- VPS aplica `alembic upgrade head`.
- Las `6` filas Modelo 200 quedan con `source_hash`, `verified=true`, `safe_to_answer=true`, `completeness='completa'`.
- Modelos `303` y `290` permanecen fail-closed.
- `mcp_validation_suite.py` y `mcp_deep_contract_audit.py` siguen `ok=true`.
