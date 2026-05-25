# Release v1.14.0 - MCP product-data validation

Fecha: 2026-05-25

Estado: RELEASE TAG `v1.14.0`

## Claim permitido

ESData queda en estado de validacion semantica/product-data verde con fail-closed explicito para el scope soportado.

Es correcto comunicar:

- `mcp_validation_suite.py` verde.
- `mcp_deep_contract_audit.py` verde.
- Contratos de producto reconciliados para evidencia fuerte o fail-closed explicito.
- VPS healthy.

No es correcto comunicar:

- cobertura verificada completa de todos los perfiles.
- conformidad oficial MCP completa.
- promocion de obligaciones sin `source_hash` y `capture_date`.

## Baseline productivo

Baseline previo validado en VPS:

- Commit de cierre: `0bd40f4`.
- Stack: Docker Compose productivo en `/srv/esdata`.
- API health: `status=ok`, `database=ok`.
- `mcp_validation_suite.py --read-only --base-url http://api:8000`: `ok=true`, `checks=133`, `failures=0`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=true`, `checks=12`, `failures=0`.

## Secuencia cerrada

| Slice | Resultado |
| --- | --- |
| `MCP-REG-01` | Registry Ralph alineado con `criterio_relacion`. |
| `MCP-OPS-01` | OpenAPI GPT Actions alineado con operaciones HTTP MCP de lineas de criterio. |
| `MCP-DATA-02` | Modelo 289 aceptado como evidencia fuerte o fail-closed explicito. |
| `MCP-DATA-03` | Modelo 202 y routing fiscal de `sociedad_valores` aceptados como presencia + verified/fail-closed. |
| `MCP-DATA-04` | RTS1/RTS2 aceptado como evidencia fuerte o fail-closed explicito. |
| `MCP-DATA-05` | MiCA/CASP y `emisor_token` aceptados como evidencia fuerte o fail-closed explicito. |
| `MCP-DATA-06` | `sociedad_valores_verified_ge_24` sustituido por `sociedad_valores_verified_or_fail_closed_ge_24`. |
| `MCP-DATA-07` | Modelo 303 de `empresa_servicios_pago` deja de exigir `completa` sin evidencia normalizada. |
| `MCP-DATA-08` | `all_profiles_pct_verified_ge_70` sustituido por `all_profiles_pct_verified_or_fail_closed_ge_70`. |

## Regla de evidencia

`verified=true` solo es admisible cuando hay evidencia normalizada:

- `source_hash` presente.
- `capture_date` presente.
- fuente primaria o revision trazable.
- aplicabilidad exacta al perfil cuando el contrato lo exige.

Fail-closed explicito es estado aceptado, no verificacion:

- `verified=false`.
- `safe_to_answer=false`.
- `source_url` presente.
- `source_hash=NULL`.
- `capture_date` presente.
- nota declarando cierre hasta cargar hash/captura.

## Backlog real post-release

Este release no recupera evidencia primaria. Deja la deuda clasificada y no bloqueante para el contrato actual:

1. Recuperar `source_hash` para obligaciones fail-closed desde fuente primaria exacta.
2. Reconciliar `source_revision` con `obligacion_perfil` cuando haya match univoco.
3. Promover filas a `verified=true` solo mediante migraciones trazables.
4. Separar cualquier trabajo de conformance oficial MCP de curacion fiscal/regulatoria.
5. Mantener el claim externo en `MCP legacy estable / validacion product-data verde`, no `MCP oficial completo`.

## Evidencia local de preparacion

Comandos ejecutados antes del tag:

| Check | Resultado |
| --- | --- |
| `python scripts/maintenance/verify-doc-contracts.py` | `docs contracts verified` |
| `python scripts/maintenance/verify-doc-artifacts.py --ci-baseline` | `docs artifacts verified` |
| `python -m pytest scripts/tests/test_maintenance_agents.py -q` | `26 passed` |
| `python -m pytest apps/api/tests/test_mcp_private.py -q` | `12 passed`, `2 warnings` |
| Host/Origin focal de `test_mcp_private.py` | `3 passed`, `2 warnings` |
| `git diff --check` | sin errores; solo warnings CRLF esperados en Windows |

`python scripts/maintenance/verify_schema.py` no se pudo ejecutar localmente porque `DATABASE_URL` no esta definido en esta sesion. Se ejecuto en VPS con el entorno productivo:

```text
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm --no-deps ops python scripts/maintenance/verify_schema.py
# Schema OK: modelo_campana_operativa, query_audit_log, dgt_queue, documento_interpretativo runtime columns present and dgt_queue uniqueness enforced
```

## Tag

`v1.14.0`
