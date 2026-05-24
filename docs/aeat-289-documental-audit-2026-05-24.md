# Auditoria documental Modelo 289 - 2026-05-24

## Resultado

Estado final de la auditoria: `partial`.

No se promueve `Modelo 289` a `complete` documental en esta ejecucion. La base
CRS/DAC2 es solida, pero no pasan todas las condiciones de hecho para cierre
contractual/documental.

Se anade la revision local
`20260524_0098_aeat_289_documental_source_refresh` para normalizar evidencia
documental fresca y corregir dos campos XSD. No se toca runtime, datos
productivos ni `obligacion_perfil`.

## Evidencia ejecutada

### Tests locales

Comando:

```powershell
python -m pytest apps\api\tests\test_modelo_obligation_context.py apps\api\tests\test_evidence_notice_separation.py apps\api\tests\test_alembic_integrity.py -q
```

Resultado actualizado tras 0098: `34 passed, 1 warning`.

Cobertura probada:

- Separacion entre `form_completeness` y `obligation_context`.
- Fail-closed de obligaciones sin `source_hash` o `capture_date`.
- Revision `20260524_0097_aeat_289_metadata_evidence` normaliza evidencia
  auxiliar del `289` sin actualizar `obligacion_perfil`, sin promover
  `safe_to_answer`, sin `verified=true` y sin `completeness='completa'`.
- Revision `20260524_0098_aeat_289_documental_source_refresh` normaliza HAP
  1695/2016, GI42 actual, manual CRS y ZIP XSD/WSDL como recursos
  documentales, sin promover obligaciones ni `completeness_estado`.

### Validaciones documentales

Comandos:

```powershell
python scripts\maintenance\verify-doc-contracts.py
python scripts\maintenance\verify-doc-artifacts.py --ci-baseline
git diff --check
```

Resultado: OK.

### API/MCP live VPS

Ejecutado contra `steamcases-vps`.

La revision 0098 queda aplicada en VPS desde el contenedor `ops` con la
migracion montada explicitamente en `/workspace`. Despues se reconstruye la
imagen `ops`, por lo que `alembic heads/current` ya reconoce 0098 sin montaje
manual. `alembic current` confirma:

```text
20260524_0098_aeat_289_documental_source_refresh (head)
```

Verificacion DB post-migracion:

- `modelo_normativa` HAP/1695/2016 para `289`: `count=1`.
- `modelo_recurso` documental activo para `289`: `5` recursos
  (`normativa_rd_1021`, `normativa_hap_1695`, `procedimiento_gi42`,
  `manual_crs_servicio_web`, `xsd_wsdl`).
- Instruccion GI42 con hash actual `1c00efed...`: `count=1`.
- Campos XSD corregidos: `SendingCompanyIN=1`, `SendingEntityIN=0`,
  `PaymentAmnt=1`, `AmntEndsmnt=0`.
- `obligacion_perfil` 289: `total=4`, `safe_true=0`, `verified_true=0`,
  `missing_hash=4`.

API VPS `/v1/modelos/aeat/289`:

- `form_completeness='parcial'`.
- `verified=false`.
- `evidence_status='evidence_limited'`.
- `obligation_context_count=4`.
- `safe_true=0`.
- `verified_true=0`.

`mcp_validation_suite.py` ejecutado desde `ops` contra `http://api:8000`.
Resultado: `ok=false`.

Hallazgos relevantes para este cierre:

- `aeat_catalogo_modelo_289_crs_counts`: OK, devuelve `289` con 5
  instrucciones y 6 reglas.
- Checks documentales 289 OK: normativa >=4, instrucciones >=5, reglas >=6,
  keywords >=8, casillas >=20, NilReport e inclusion/exclusion.
- `modelo_289_obligation_context_contract`: FAIL esperado para cierre
  documental; `form_completeness='parcial'`, 4 contextos de obligacion, y
  `sociedad_valores` queda `verified=false`, `safe_to_answer=false`,
  `source_hash=null`.
- `modelo_289_profile_obligations_verified_4`: FAIL, valor `0`.
- `modelo_289_profile_obligations_no_unverified_or_extra`: FAIL, valor `4`.

`mcp_deep_contract_audit.py` ejecutado desde `ops` termina con `ok=false` por
la suite MCP anidada. No bloquea la migracion, pero si bloquea cualquier
promocion a `complete`.

Nota local: `http://localhost:8000/health` no se usa como evidencia porque
responde `service=vpro-api`, no ESData.

## Hashes oficiales comprobados

Hashes calculados el 2026-05-24 desde las URLs oficiales accesibles:

| Fuente | Estado HTTP | SHA-256 actual | Decision |
| --- | ---: | --- | --- |
| BOE RD 1021/2015 `https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399` | 200 | `423708790f64e673977e020d223ee8af89e99bea7970d793c998264e0fbc7b75` | Coincide con 0097. |
| BOE Orden HAP/1695/2016 `https://www.boe.es/buscar/doc.php?id=BOE-A-2016-9834` | 200 | `502a67740152eb23bdf66a59c1a2a69d0a34d8e4054b26191bb7dcfef7d05794` | Normalizada localmente en 0098 como normativa y recurso documental. |
| AEAT GI42 `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml` | 200 | `1c00efed01d8d917591907c134abdc8dde84d87e51a6b69ca5a6acf830a26e1c` | Normalizada localmente en 0098; sustituye el hash auxiliar 0097 para nueva evidencia GI42. |
| AEAT CRS PDF `https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf` | 200 | `ce76a21a629125961efe6a1ed9800262f4d253ab55c72a7f04e358936a448be3` | Coincide con 0097. |
| AEAT XSD/WSDL ZIP `https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/XSD_WSDL/289_XSD_2.0_WSDL_2.0.1.zip` | 200 | `6948eec877d04ca637b099f59fa944996aa878c8d68181dfffde87fd056a048d` | Normalizado localmente en 0098 como recurso tecnico; auditoria detecta y corrige dos campos persistidos. |

## Piezas documentales auditadas

| Pieza | Estado | Evidencia |
| --- | --- | --- |
| Aprobacion y periodicidad anual del modelo | Probada externamente | Orden HAP/1695/2016. |
| Plazo 1 de enero a 31 de mayo | Probada externamente | Orden HAP/1695/2016 y AEAT GI42. |
| Presentacion por mensajes/servicio web | Probada externamente | Orden HAP/1695/2016 y AEAT GI42. |
| Reglas de aceptacion/rechazo de registros | Probada externamente | Orden HAP/1695/2016 y manual AEAT CRS. |
| `ResidenceCountryCode` y cuentas no documentadas | Probada externamente | Manual AEAT CRS. |
| `AcctHolderType` | Parcial | Existe como campo XSD persistido y 0098 registra hash ZIP; falta source/hash por campo o contrato equivalente de campo. |
| Operaciones `OECD1/OECD2/OECD3` | Parcial | Persistidas en descripcion XSD de `DocTypeIndic`; falta contrato API/MCP especifico que pruebe esos codigos. |
| XSD/WSDL tecnico | Parcial | ZIP oficial accesible y normalizado en 0098; se corrige `SendingEntityIN` a `SendingCompanyIN` y `AmntEndsmnt` a `PaymentAmnt`. |
| `obligation_context` por perfil | Fuera de Sprint 1 | Debe seguir separado y fail-closed si falta evidencia propia. |

## Bloqueantes para `complete` documental

1. La evidencia XSD/WSDL queda normalizada a nivel recurso, pero no existe aun
   trazabilidad por campo individual o contrato equivalente que cierre todos los
   campos sensibles.
2. La suite live VPS no pasa por contrato real: el formulario queda `parcial` y
   `obligation_context` mantiene 4 filas no verificadas/sin hash.
3. `mcp_deep_contract_audit.py` termina `ok=false` por la suite MCP anidada.
4. Los tests actuales prueban separacion formulario/obligacion y la migracion
   documental, pero no prueban cierre documental completo de API/MCP.

## Decision

`Modelo 289` permanece `partial`.

No hay base suficiente para cambiar `verified=true`, `completeness=complete` ni
`form_completeness` a `complete` en esta iteracion.

`CRS/DAC2 operativo` permanece `implemented_partial`.

## Siguiente accion exacta

1. Mantener GI42 con hash actual `1c00efed...` como evidencia 0098; no volver
   al hash auxiliar 0097.
2. No promover `289` a `complete`; los checks documentales pasan, pero los
   checks de perfil siguen fallando correctamente.
3. Si se quiere recuperar obligaciones de perfil `289`, abrir auditoria
   separada por sujeto obligado/supuesto con fuente, hash y captura propios.
4. Si se quiere cerrar CRS/DAC2 operativo, ejecutar `docs/crs-dac2-coverage-prd.md`
   como familia separada.
