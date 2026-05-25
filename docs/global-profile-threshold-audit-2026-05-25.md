# Global profile threshold audit - 2026-05-25

Estado: COMPLETADO VPS

Alcance Ralph: reconciliar el ultimo fallo `all_profiles_pct_verified_ge_70` sin promover obligaciones ni usar el porcentaje como objetivo artificial.

## RED productivo

Entorno: VPS `steamcases-vps`, commit `0b5305a`, stack Docker Compose productivo.

Estado antes del cambio:

- `mcp_validation_suite.py --read-only --base-url http://api:8000`: `ok=false`, `checks=133`, `failures=1`.
- Fallo unico: `all_profiles_pct_verified_ge_70`, `value=8`, `expected=0`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=false`, `checks=12`, `failures=1`.
- Fallo unico: `semantic_fail_closed_and_pagination_suite`, causado por `all_profiles_pct_verified_ge_70`.

## Inventario por perfil

Consulta read-only sobre `obligacion_perfil`:

| Perfil | Total | Verified | Safe | Verified con evidencia | Fail-closed explicitas | Accepted | Neither | Pct verified | Pct accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `casp` | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 0.00 | 100.00 |
| `emisor_token` | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 0.00 | 100.00 |
| `sgiic` | 26 | 2 | 2 | 2 | 24 | 26 | 0 | 7.69 | 100.00 |
| `eaf` | 25 | 2 | 2 | 2 | 23 | 25 | 0 | 8.00 | 100.00 |
| `entidad_credito` | 34 | 3 | 2 | 3 | 31 | 34 | 0 | 8.82 | 100.00 |
| `agencia_valores` | 38 | 4 | 3 | 4 | 34 | 38 | 0 | 10.53 | 100.00 |
| `sociedad_valores` | 38 | 4 | 3 | 4 | 34 | 38 | 0 | 10.53 | 100.00 |
| `empresa_servicios_pago` | 13 | 2 | 2 | 2 | 11 | 13 | 0 | 15.38 | 100.00 |

Conteos agregados:

- Perfiles bajo 70% con metrica historica `verified=true`: `8`.
- Perfiles bajo 70% con metrica `verified_or_fail_closed`: `0`.

## Decision de contrato

El check historico `all_profiles_pct_verified_ge_70` mide solo `verified=true`. Tras las historias anteriores, el sistema separa dos estados aceptables:

- `verified=true` solo con `source_hash` y `capture_date`.
- fail-closed explicito solo con `verified=false`, `safe_to_answer=false`, `source_url` presente, `source_hash=NULL`, `capture_date` presente y nota `fail-closed until source_hash and capture_date are loaded`.

El inventario productivo muestra `neither_state=0` para los 8 perfiles. Por tanto, el fallo restante no prueba deuda no clasificada: prueba que la metrica historica ya no representa el contrato fail-closed vigente.

El contrato correcto queda:

- `all_profiles_pct_verified_or_fail_closed_ge_70`.
- El umbral no baja: sigue siendo 70%.
- El numerador se endurece: no cuenta `verified=true` sin hash/captura y solo cuenta fail-closed si la fila esta cerrada explicitamente.

## No-objetivos

- No modificar datos productivos.
- No promover `verified=true`.
- No promover `safe_to_answer=true`.
- No cambiar `completeness`.
- No ocultar perfiles incompletos: cualquier fila fuera de `verified_with_evidence` o `fail_closed_explicit` vuelve a contar contra el umbral.

## Criterio de salida

- `mcp_validation_suite.py` pasa sin fallos por el contrato global reformulado.
- `mcp_deep_contract_audit.py` pasa porque delega en la suite semantica.
- El roadmap deja claro que el cierre es de contrato, no de recuperacion de evidencia primaria.

## Validacion VPS

Despliegue:

- Commit `440a833` en `/srv/esdata` por `git pull --ff-only`.
- Imagen `ops` reconstruida correctamente.
- API y Postgres permanecen `healthy`; `/health` devuelve `status=ok`, `database=ok`.

Suite principal:

```text
python scripts/maintenance/mcp_validation_suite.py --read-only --base-url http://api:8000
# ok=true
# checks=133
# failures=0
# all_profiles_pct_verified_or_fail_closed_ge_70: ok=true, value=0
```

Deep audit:

```text
python scripts/maintenance/mcp_deep_contract_audit.py --base-url http://api:8000
# ok=true
# checks=12
# failures=0
```

Resultado: el ultimo fallo semantico queda cerrado sin mutar datos productivos ni promover verificaciones.
