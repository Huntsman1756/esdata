# Sociedad valores profile threshold audit - 2026-05-24

Estado: COMPLETADO VPS

Alcance Ralph: reconciliar el umbral historico `sociedad_valores_verified_ge_24` sin promover obligaciones por analogia ni usar `all_profiles_pct_verified_ge_70` como objetivo directo.

## RED productivo

Entorno: VPS `steamcases-vps`, commit `6cb1ca5`, stack Docker Compose productivo.

Comandos read-only ejecutados desde `ops`:

```text
python scripts/maintenance/mcp_validation_suite.py --read-only --base-url http://api:8000
python scripts/maintenance/mcp_deep_contract_audit.py --base-url http://api:8000
```

Resultados:

- `mcp_validation_suite.py`: `ok=false`, `checks=133`, `failures=2`.
- Fallos semanticos: `sociedad_valores_verified_ge_24` con `value=4`, `minimum=24`; `all_profiles_pct_verified_ge_70` con `value=8`.
- `mcp_deep_contract_audit.py`: `ok=false`, `checks=12`, `failures=3`.
- `eu_norm_contracts`: `sociedad_valores_verified_count=4`, `minimum=20`.
- `profile_applicability_contracts`: fallo residual no relacionado `empresa_servicios_pago_modelo_303_completa`.

## Inventario de `sociedad_valores`

Consulta de clasificacion:

```sql
WITH classified AS (
  SELECT *,
    CASE
      WHEN verified IS TRUE AND source_hash IS NOT NULL AND capture_date IS NOT NULL THEN 'verified_with_evidence'
      WHEN verified IS NOT TRUE
        AND safe_to_answer IS NOT TRUE
        AND source_url IS NOT NULL
        AND source_hash IS NULL
        AND capture_date IS NOT NULL
        AND notas ILIKE '%fail-closed until source_hash and capture_date are loaded%'
        THEN 'fail_closed_explicit'
      WHEN verified IS TRUE THEN 'verified_without_full_evidence'
      ELSE 'other_unverified'
    END AS state
  FROM obligacion_perfil
  WHERE perfil_codigo='sociedad_valores'
)
SELECT state, count(*) FROM classified GROUP BY state ORDER BY state;
```

Resultado productivo:

| Estado | Filas |
| --- | ---: |
| `verified_with_evidence` | 4 |
| `fail_closed_explicit` | 34 |
| Total | 38 |

Conteos adicionales:

| Metrica | Valor |
| --- | ---: |
| `verified=true` | 4 |
| `safe_to_answer=true` | 3 |

Las 4 filas verificadas tienen `source_hash` y `capture_date`: Modelos 111, 115, 216 y 296.

Las 34 filas restantes tienen `verified=false`, `safe_to_answer=false`, `source_hash=NULL`, `capture_date` presente y nota fail-closed. Incluyen obligaciones CNMV/LIVMC, PBC/FT, DORA, RTS1/RTS2, MiFID/MiFIR, IFR y AEAT 187/193/198/200/202/289/290/303.

## Decision de contrato

No hay base para promover las 34 filas a `verified=true`: tienen URL y fecha de captura, pero les falta hash normalizado de fuente primaria y prueba exacta de aplicabilidad al perfil.

El contrato historico `sociedad_valores_verified_ge_24` era mas optimista que el estado fail-closed real. El contrato honesto queda:

- `verified=true` cuenta solo con `source_hash` y `capture_date`.
- `fail-closed` cuenta solo si `verified=false`, `safe_to_answer=false`, `source_url` existe, `source_hash=NULL`, `capture_date` existe y las notas declaran el cierre hasta cargar hash/captura.
- El umbral no baja: sigue exigiendo al menos `24` obligaciones aceptadas, pero el estado aceptado se llama explicitamente `verified_or_fail_closed`.

## No-objetivos

- No modificar datos productivos.
- No tocar CASP, `emisor_token` ni MiCA.
- No resolver `all_profiles_pct_verified_ge_70` por manipulacion agregada.
- No cerrar Modelo 303 de `empresa_servicios_pago`.

## Criterio de salida

- `mcp_validation_suite.py` deja de fallar por `sociedad_valores_verified_ge_24` y usa `sociedad_valores_verified_or_fail_closed_ge_24`.
- `mcp_deep_contract_audit.py` mantiene `sociedad_valores_verified_count` como detalle, pero falla solo si `sociedad_valores_verified_or_fail_closed_count` queda bajo el minimo.
- La metrica `all_profiles_pct_verified_ge_70` queda separada para un slice global posterior.

## Validacion local

```text
python -m pytest scripts/tests/test_maintenance_agents.py -q
# 24 passed

python -m py_compile scripts/maintenance/mcp_validation_suite.py scripts/maintenance/mcp_deep_contract_audit.py
# OK

python scripts/maintenance/verify-doc-contracts.py
# docs contracts verified

python scripts/maintenance/verify-doc-artifacts.py --ci-baseline
# docs artifacts verified
```

## Validacion VPS

Despliegue:

- Commit `3e8092a` en `/srv/esdata` por `git pull --ff-only`.
- Imagen `ops` reconstruida correctamente.
- API y Postgres permanecen `healthy`; `/health` devuelve `status=ok`, `database=ok`.

Suite principal:

```text
python scripts/maintenance/mcp_validation_suite.py --read-only --base-url http://api:8000
# ok=false
# checks=133
# failures=1
# failure_names=['all_profiles_pct_verified_ge_70']
# sociedad_valores_verified_or_fail_closed_ge_24: ok=true, value=38, minimum=24
```

Deep audit:

```text
python scripts/maintenance/mcp_deep_contract_audit.py --base-url http://api:8000
# ok=false
# checks=12
# failures=2
# failure_names=['profile_applicability_contracts', 'semantic_fail_closed_and_pagination_suite']
# eu_norm_contracts: ok=true
# sociedad_valores_verified_count=4
# sociedad_valores_fail_closed_count=34
# sociedad_valores_verified_or_fail_closed_count=38
```

Resultado: el bloque `sociedad_valores` deja de ser fallo semantico y de `eu_norm_contracts`. La deuda restante queda separada en Modelo 303 de `empresa_servicios_pago` y en la metrica agregada de perfiles.
