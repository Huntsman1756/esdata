# Checklist Sprint 1: Modelo 289 documental

## Objetivo de la revision

Determinar si el `Modelo 289` puede pasar a `complete` solo como contrato
documental. Si cualquier check obligatorio queda sin evidencia formal, el modelo
debe seguir `partial` con el gap documentado.

Este checklist no cierra CRS/DAC2 operativo y no autoriza cambios en
`obligacion_perfil`.

## Preflight

| Check | Comando | Criterio |
| --- | --- | --- |
| Arbol controlado | `git status --short` | Solo deben aparecer archivos del sprint o cambios ya reconocidos. |
| Reglas docs | `python scripts\maintenance\verify-doc-contracts.py` | Debe devolver OK. |
| Artefactos docs | `python scripts\maintenance\verify-doc-artifacts.py --ci-baseline` | Debe devolver OK. |
| Whitespace | `git diff --check` | Sin errores. |

## Inventario de fuentes aceptables

Cada fuente que se use para promover el contrato documental debe tener
`source_url`, `source_hash` y `capture_date`.

| Fuente | Uso permitido | Check |
| --- | --- | --- |
| Orden HAP/1695/2016 | Aprobacion del modelo, alcance anual, forma/plazo y marco de presentacion | Confirmar URL BOE, hash y captura. |
| Real Decreto 1021/2015 | Obligacion CRS y reglas base de identificacion/informacion | Confirmar URL BOE, hash y captura. |
| AEAT GI42 | Procedimiento AEAT vigente del modelo | Confirmar URL AEAT, hash y captura. |
| Manual CRS / servicio web AEAT | Reglas de presentacion, respuestas y validaciones operativas del formulario | Confirmar URL/PDF, hash y captura. |
| XSD/WSDL o diseno logico oficial | Campos tecnicos del mensaje y estructura | Confirmar archivo oficial, hash y captura. |

No aceptar como prueba de cierre:

- ejemplos XML sin contrato oficial determinista,
- resumenes legacy reformulados,
- inferencias desde CRS general,
- hashes de una fuente general para probar una regla mas especifica.

## Checks documentales por pieza

| Pieza | Prueba requerida | Resultado permitido |
| --- | --- | --- |
| Periodo y plazo | Fuente oficial que pruebe periodicidad anual y ventana de presentacion | `complete` solo si fuente exacta esta trazada. |
| Presentacion por servicio web | Fuente AEAT o BOE que pruebe canal y reglas | `partial` si solo hay referencia indirecta. |
| Operaciones `OECD1/OECD2/OECD3` | Manual, XSD/WSDL o diseno oficial con codigo y descripcion | `partial` si falta descripcion oficial por codigo. |
| Jurisdiccion reportable | Fuente oficial que conecte pais/jurisdiccion con cuenta reportable | `partial` si solo hay CRS generico. |
| `ResidenceCountryCode` | Campo oficial y regla de uso | `partial` si solo aparece como nombre de campo sin regla. |
| `AcctHolderType` | Campo oficial y valores/uso | `partial` si falta descripcion deterministica. |
| Cuentas no documentadas | Regla oficial de tratamiento | `partial` si falta supuesto. |
| Aceptado parcial/rechazado parcial/total | Regla oficial de respuesta o estado | `partial` si solo consta comportamiento observado. |
| Reglas de inclusion | Fila `modelo_regla_inclusion` con fuente literal trazable | No reutilizar fuente por proximidad. |
| Instrucciones | Fila `modelo_instruccion` con fuente literal trazable | No normalizar resumen legacy por solapamiento tematico. |
| Claves/codigos auxiliares | Codigo + descripcion probados por fuente oficial | Si falta, mantener fuera de `complete`. |

## Checks de API y MCP

Ejecutar local o contra entorno configurado. Si requiere API key, usar
`ESDATA_API_KEY`/`MCP_API_KEY` sin imprimir secretos.

| Check | Comando | Criterio |
| --- | --- | --- |
| Contrato focal API 289 | `python -m pytest apps\api\tests\test_modelo_obligation_context.py apps\api\tests\test_evidence_notice_separation.py -q` | Debe probar separacion formulario/obligacion y fail-closed contextual. |
| Metadata auxiliar 289 | `python -m pytest apps\api\tests\test_alembic_integrity.py -q` | Debe conservar revision 0097, validar 0098 y prohibir promociones de obligacion/completeness. |
| Suite read-only API/MCP | `python scripts\maintenance\mcp_validation_suite.py --read-only --base-url http://localhost:8000` | Deben pasar checks `modelo_289_*` y `aeat_catalogo_modelo_289_crs_counts` en entorno con corpus completo. |
| Auditoria profunda opcional | `python scripts\maintenance\mcp_deep_contract_audit.py --base-url http://localhost:8000 --database-url %DATABASE_URL%` | No debe detectar contaminacion entre catalogo 289 y `obligation_context`. |

## Checks fail-closed

Estos checks bloquean cualquier promocion a `complete` documental:

1. `/v1/modelos/aeat/289` no debe marcar obligaciones de perfil seguras por el
   simple hecho de que el formulario mejore.
2. `obligation_context` debe mantener `safe_to_answer=false` cuando falte
   sujeto obligado, supuesto, `source_hash` o `capture_date`.
3. El catalogo AEAT no debe incluir `obligation_context`.
4. `CRS/DAC2 operativo` debe seguir `implemented_partial` en matriz y PRD.
5. El estado documental del `289` no debe mejorar ni degradar automaticamente
   `Modelo 290`/FATCA IRS.

## Decision final

| Resultado de auditoria | Estado permitido | Accion docs |
| --- | --- | --- |
| Pasa las ocho condiciones de hecho y todos los checks bloqueantes | `complete` solo contractual/documental | Actualizar `docs/aeat-priority-model-closeout.md`, matriz y manual con la salvedad CRS/DAC2. |
| Falla cualquier condicion obligatoria | `partial` | Documentar gap exacto y siguiente accion. |
| Hay evidencia de formulario pero no de perfil/supuesto | `complete` documental posible, `obligation_context` fail-closed | No tocar `obligacion_perfil`. |
| La evidencia exige procedimiento CRS/DAC2 | Fuera de Sprint 1 | Mover a `docs/crs-dac2-coverage-prd.md`. |

## Archivos esperados si se implementa

Cambios permitidos en Sprint 1:

- `docs/aeat-289-documental-closeout-prd.md`
- `docs/aeat-289-sprint-1-checklist.md`
- `docs/aeat-priority-model-closeout.md`
- `docs/fiscal-regulatory-coverage-matrix.md`
- tests focales de API/MCP si el checklist exige nuevos contratos
- migracion de datos documental si solo normaliza fuentes/campos y no promueve
  `obligacion_perfil`, `safe_to_answer`, `verified` ni `completeness_estado`

Cambios no permitidos sin auditoria separada:

- `obligacion_perfil`
- migraciones que promuevan `safe_to_answer`
- runtime de CRS/DAC2 operativo
- semillas FATCA IRS o `Modelo 290`
