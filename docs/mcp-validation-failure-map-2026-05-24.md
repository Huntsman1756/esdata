# MCP validation failure map - 2026-05-24

Estado: DIAGNOSTIC

Alcance Ralph: clasificar los 12 fallos vivos de `mcp_validation_suite.py` en VPS sin mutar datos, workers ni contratos MCP. Este documento no cierra ningun fallo; solo separa transporte/protocolo de deuda de datos y contratos de producto.

## Evidencia de partida

- Entorno: VPS `steamcases-vps`, stack Docker Compose productivo.
- Commit productivo observado: `dc55c9f`.
- Comando: `python scripts/maintenance/mcp_validation_suite.py --read-only --base-url http://api:8000` ejecutado desde el contenedor `ops`.
- Resultado: `ok=false`, `checks=130`, `failures=12`.
- Transporte MCP: `mcp_transport_tools_list` pasa con `tool_count=83` y `missing_tools=[]`.

Veredicto tecnico: la suite no esta fallando por transporte MCP ni por descubrimiento de herramientas. Los 12 fallos son de datos, evidencia verificada o contratos REST/API usados por la capa MCP.

## Mapa de fallos

| Check | Observado | Esperado | Contrato que valida | Interpretacion actual | Siguiente slice Ralph |
| --- | ---: | ---: | --- | --- | --- |
| `sociedad_valores_verified_ge_24` | `4` | `>=24` | SQL sobre `obligacion_perfil` para `perfil_codigo='sociedad_valores' AND verified=true` | Deuda global de evidencia verificada para el perfil. No prueba fallo de MCP; prueba que el control-plane ya no puede reclamar cobertura verificada amplia para `sociedad_valores`. | `MCP-DATA-01`: decidir si el umbral sigue siendo valido o si debe sustituirse por checks por dominio con fail-closed explicito. |
| `all_profiles_pct_verified_ge_70` | `8` | `0` | SQL de porcentaje verificado por perfil | Hay 8 perfiles por debajo del 70% verificado. Es deuda transversal de datos/contratos, no de transporte. | `MCP-DATA-01`: inventario por perfil, umbral justificable y excepciones documentadas. |
| `modelo_289_uses_lgt_da22_ap1` | `4` | `0` | SQL de obligaciones Modelo 289 con norma/articulo/verificacion distinta de LGT DA22 ap. 1 verificada | La auditoria documental 289 esta fuerte, pero las obligaciones de perfil siguen sin evidencia/promocion suficiente. | `MCP-DATA-02`: auditoria separada de `obligacion_perfil` CRS/DAC2 para 289. |
| `modelo_289_profile_obligations_verified_4` | `0` | `>=4` | SQL de perfiles verificados para Modelo 289 entre sociedad/agencia/eaf/entidad_credito | Ninguno de los 4 perfiles esperados esta promovido como `verified=true`. | `MCP-DATA-02`: localizar fuente primaria por sujeto obligado y promover solo con hash/captura suficiente. |
| `modelo_289_profile_obligations_no_unverified_or_extra` | `4` | `0` | SQL de obligaciones 289 no verificadas o fuera del set esperado | Las 4 obligaciones presentes permanecen como deuda fail-closed. | `MCP-DATA-02`: limpiar extras o mantenerlos no verificados con contrato que lo refleje. |
| `modelo_289_obligation_context_contract` | `None` | contrato JSON OK | `/v1/modelos/aeat/289` debe exponer `obligation_context` con `sociedad_valores` verificado y notice de verificacion | El endpoint responde, pero no cumple el contrato de contexto verificado. Coincide con la auditoria 289 de 2026-05-24: no promover. | `MCP-DATA-02`: cerrar primero la capa `obligacion_perfil`; despues revalidar contrato API. |
| `modelo_202_all_profiles_loaded` | `0` | `>=6` | SQL de perfiles con `modelo_aeat='202' AND verified=true` | Modelo 202 no tiene perfiles verificados suficientes en produccion. No hay cierre documental especifico equivalente a modelos completos. | `MCP-DATA-03`: mini-auditoria Modelo 202 por perfiles, fuente, plazo y aplicabilidad. |
| `perfil_sociedad_valores_fiscal_routing_contract` | `None` | contrato JSON OK | `/v1/perfil/sociedad_valores/obligaciones?dominio=FISCAL` debe incluir Modelo 202, excluir 123/124 y tener algun 202 verificado | El routing fiscal existe, pero falla el requisito de Modelo 202 verificado. Esta acoplado al fallo anterior. | `MCP-DATA-03`: resolver/verificar Modelo 202 antes de tocar el contrato. |
| `rts1_rts2_obligations_all_verified` | `12` | `0` | SQL de obligaciones RTS1/RTS2 no verificadas | Hay obligaciones RTS1/RTS2 cargadas pero no verificadas. La deuda es de evidencia/promocion, no de corpus ausente. | `MCP-DATA-04`: recuperar hashes/capturas EUR-Lex o ajustar el contrato a `parcial` si la politica es fail-closed. |
| `casp_obligations_all_verified` | `0` | `>=6` | SQL de obligaciones MiCA CASP `verified=true` | Las obligaciones CASP existen en la superficie de producto, pero no alcanzan el nivel verificado que la suite exige. | `MCP-DATA-05`: reconciliar MiCA CASP contra fuente primaria y estado real de `verified`. |
| `emisor_token_obligations_all_verified` | `0` | `>=8` | SQL de obligaciones MiCA `emisor_token` `verified=true` | El perfil existe, pero la suite no encuentra obligaciones verificadas. Mantener respuesta parcial/fail-closed. | `MCP-DATA-05`: recuperar evidencia ART/EMT y corpus supervisor antes de promocion. |
| `emisor_token_art_base_obligations_completa` | `0` | `>=3` | SQL de obligaciones `emisor_token` MiCA arts. 18/19/35 con `completeness='completa'` | Las obligaciones base ART no estan completas segun el contrato actual. | `MCP-DATA-05`: verificar articulos base y separar ART completo de EMT parcial. |

## Priorizacion

1. `MCP-DATA-02` debe ir antes que cualquier reclamo sobre Modelo 289. La documentacion actual ya dice que los checks documentales pasan, pero las obligaciones de perfil no.
2. `MCP-DATA-03` desbloquea dos fallos a la vez: `modelo_202_all_profiles_loaded` y `perfil_sociedad_valores_fiscal_routing_contract`.
3. `MCP-DATA-01` es una decision de politica de suite: los umbrales globales solo son utiles si reflejan el modelo fail-closed actual.
4. `MCP-DATA-04` y `MCP-DATA-05` son recuperacion de evidencia regulatoria, no cambios de MCP.

## Reclamo permitido

- Permitido: "MCP legacy estable con transporte/listado de herramientas operativo; conformance oficial y semantica de producto parcial".
- No permitido: "MCP oficial completo" o "suite MCP productiva verde".

## Estado de deep audit

Reintento ejecutado en VPS con timeout controlado:

```text
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml --profile ops run --rm --no-deps ops sh -lc 'timeout 420s python scripts/maintenance/mcp_deep_contract_audit.py --base-url http://api:8000 --output /tmp/esdata_mcp_deep_20260524.json'
```

Resultado: `ok=false`, `checks=12`. El estado deja de ser `UNKNOWN`: la auditoria completa termina y falla de forma explicita. No quedo contenedor one-off `ops-run` residual tras la ejecucion.

Bloques fallidos:

| Bloque deep audit | Fallos | Lectura |
| --- | ---: | --- |
| `database_table_registry_contract` | `1` | Tabla `criterio_relacion` existe con `row_count=4`, pero falta en el registry Ralph. Es deuda de control-plane/registry. |
| `gpt_actions_openapi_contract` | `1` | Operaciones ya declaradas en `HTTP_MCP_OPERATIONS` faltan en el OpenAPI reducido GPT Actions: `buscar_lineas_criterio`, `criterio_relacionado_con_modelo`, `detalle_linea_criterio`, `detalle_linea_criterio_doctrina`, `doctrina_coverage`, `listar_lineas_criterio`. Es drift del artefacto OpenAPI servido en `/gpt-actions/modelos/openapi.json`. |
| `profile_applicability_contracts` | `4` | Falla Modelo 303 para `empresa_servicios_pago`, contexto verificado 289, notice verificado 289 y notice RTS1 para `sociedad_valores`. |
| `eu_norm_contracts` | `4` | Coincide con deuda de evidencia: `sociedad_valores_verified_count=4<20`, CASP `0/8` verified, `emisor_token 0/8` verified, ART completa `0`. |
| `semantic_fail_closed_and_pagination_suite` | `12` | Reproduce los 12 fallos de `mcp_validation_suite.py` listados arriba. |

Nuevo veredicto: `mcp_deep_contract_audit.py` no esta bloqueado por timeout. El bloqueo real es mayor que la suite semantica: incluye registry Ralph, drift de operaciones GPT Actions/MCP y contratos de aplicabilidad.

## Issue drafts

Estos borradores estan listos para crear como issues. No deben ejecutarse como un unico PR: cada uno tiene artefacto responsable y criterio de salida propio.

### Issue MCP-REG-01 - Registrar `criterio_relacion` en el registry Ralph

Estado local: IMPLEMENTED. `scripts/ralph/table-remediation-registry.json` incluye `criterio_relacion`, `summary.total_tables=181` y `summary.populated=90`.

Impacto: bloquea `database_table_registry_contract` en `mcp_deep_contract_audit.py`.

Owner propuesto: control-plane/schema.

Artefactos a cambiar:

- `scripts/ralph/table-remediation-registry.json`
- Docs de registry si la clasificacion de `criterio_relacion` requiere explicacion.

Descripcion:

La tabla productiva `criterio_relacion` existe y tiene `row_count=4`, pero no esta declarada en el registry Ralph. El deep audit falla porque no puede clasificarla como `populated`, `workflow_empty`, `allowed_empty` o `configured_but_unavailable`.

Checklist de salida:

- [ ] Clasificar `criterio_relacion` en el registry Ralph con estado y ownership explicitos.
- [ ] Confirmar que no se crea ninguna tabla en runtime ni se modifica schema productivo.
- [ ] Ejecutar `python scripts/maintenance/mcp_deep_contract_audit.py --base-url http://api:8000` en VPS o entorno equivalente y verificar que `database_table_registry_contract` pasa.

### Issue MCP-OPS-01 - Alinear lineas de criterio con HTTP MCP/OpenAPI

Estado local: IMPLEMENTED. `docs/openapi-gpt.json` y `docs/openapi-gpt-3.0.json` se regeneran desde `HTTP_MCP_OPERATIONS`; ambas specs incluyen las 6 operaciones de lineas de criterio.

Impacto: bloquea `gpt_actions_openapi_contract` en `mcp_deep_contract_audit.py`.

Owner propuesto: API/MCP surface.

Artefactos a cambiar:

- `apps/api/mcp_catalog.py`
- Router/esquemas de lineas de criterio, si los endpoints existen pero no estan expuestos como operaciones MCP.
- `docs/openapi-gpt.json`, si la regeneracion aplica.

Descripcion:

El deep audit detecta operaciones de lineas de criterio presentes en `HTTP_MCP_OPERATIONS` pero ausentes del OpenAPI reducido de GPT Actions: `buscar_lineas_criterio`, `criterio_relacionado_con_modelo`, `detalle_linea_criterio`, `detalle_linea_criterio_doctrina`, `doctrina_coverage` y `listar_lineas_criterio`. Hay que mantener la paridad entre el catalogo MCP HTTP y el artefacto servido por `/gpt-actions/modelos/openapi.json`.

Checklist de salida:

- [ ] Decidir por endpoint: exponer en MCP/GPT Actions o excluir del contrato con razon documentada.
- [ ] Si se exponen, anadir operaciones read-only con parametros acotados y descripcion no ambigua.
- [ ] Regenerar/verificar OpenAPI GPT si cambia la superficie.
- [ ] Ejecutar deep audit focal o completo y verificar que `gpt_actions_openapi_contract` pasa.

### Issue MCP-DATA-01 - Reconciliar umbrales globales de perfiles verificados

Estado VPS read-only: DIAGNOSED. No hay filas no verificadas con evidencia completa: las `173` obligaciones `verified=false` tienen `source_url` y `capture_date`, pero les falta `source_hash`.

Conteo productivo por perfil:

| Perfil | Total | Verified | Safe | Missing evidence | Pct verified |
| --- | ---: | ---: | ---: | ---: | ---: |
| `casp` | 8 | 0 | 0 | 8 | 0.00 |
| `emisor_token` | 8 | 0 | 0 | 8 | 0.00 |
| `sgiic` | 26 | 2 | 2 | 24 | 7.69 |
| `eaf` | 25 | 2 | 2 | 23 | 8.00 |
| `entidad_credito` | 34 | 3 | 2 | 31 | 8.82 |
| `agencia_valores` | 38 | 4 | 3 | 34 | 10.53 |
| `sociedad_valores` | 38 | 4 | 3 | 34 | 10.53 |
| `empresa_servicios_pago` | 13 | 2 | 2 | 11 | 15.38 |

`sociedad_valores` por tipo de obligacion:

| Tipo | Total | Verified | Missing evidence |
| --- | ---: | ---: | ---: |
| `AUTOLIQUIDACION` | 6 | 3 | 3 |
| `COMUNICACION_INDICIO` | 1 | 0 | 1 |
| `CONTROL_INTERNO` | 8 | 0 | 8 |
| `DECLARACION_INFORMATIVA` | 6 | 1 | 5 |
| `DILIGENCIA_DEBIDA` | 3 | 0 | 3 |
| `FORMACION` | 2 | 0 | 2 |
| `REGISTRO` | 1 | 0 | 1 |
| `REPORTING` | 11 | 0 | 11 |

Lectura: no hay recuperacion segura solo con flip de flags. El siguiente paso real es recuperar `source_hash` trazable desde fuente primaria o `source_revision` para filas concretas, empezando por los bloques con mas impacto (`sociedad_valores`/`agencia_valores`, reporting/CNMV/EU y fiscal AEAT), o ajustar umbrales si la politica actual es mantener fail-closed.

Impacto: bloquea `sociedad_valores_verified_ge_24`, `all_profiles_pct_verified_ge_70`, `sociedad_valores_verified_count` y contribuye a `eu_norm_contracts`.

Owner propuesto: data quality/regulatory evidence.

Artefactos a cambiar:

- `scripts/maintenance/mcp_validation_suite.py`
- `scripts/maintenance/mcp_deep_contract_audit.py`
- Datos/migraciones solo si existe fuente primaria suficiente para recuperar `verified=true`.
- Documento de politica fail-closed si el umbral global deja de ser correcto.

Descripcion:

La degradacion fail-closed global redujo el conteo verificado de `sociedad_valores` a `4`, por debajo de los umbrales historicos de la suite. Hay que decidir si esos umbrales siguen representando producto real o si deben sustituirse por checks por dominio/perfil que respeten evidencia incompleta.

Checklist de salida:

- [ ] Extraer conteo por perfil: total, `verified=true`, `safe_to_answer=true`, `missing_hash`, dominios afectados.
- [ ] Separar filas recuperables con fuente primaria de filas que deben permanecer fail-closed.
- [ ] No promover `verified=true` sin `source_hash` y `capture_date`.
- [ ] Ajustar checks solo si el nuevo contrato refleja explicitamente fail-closed.
- [ ] Reejecutar `mcp_validation_suite.py --read-only` y confirmar los checks globales afectados.

### Issue MCP-DATA-02 - Cerrar o mantener fail-closed las obligaciones Modelo 289 por perfil

Estado local: IMPLEMENTED AS FAIL-CLOSED CONTRACT. La auditoria read-only no encontro hash exacto para la URL legacy de las 4 obligaciones. El contrato local de `mcp_validation_suite.py` y `mcp_deep_contract_audit.py` ya acepta dos estados seguros para 289: verificado con `source_hash`/`capture_date`, o fail-closed explicito con `verified=false`, `safe_to_answer=false`, `review_required=true`, `source_hash=null`, `capture_date` y notice `evidence_limited`.

Impacto: bloquea `modelo_289_uses_lgt_da22_ap1`, `modelo_289_profile_obligations_verified_4`, `modelo_289_profile_obligations_no_unverified_or_extra`, `modelo_289_obligation_context_contract`, `modelo_289_obligation_context_verified` y `modelo_289_profile_evidence_notice_verified`.

Estado de checks tras el cambio local:

- `modelo_289_uses_lgt_da22_ap1`: mantiene LGT DA 22 ap. 1, pero deja de exigir `verified=true`.
- `modelo_289_profile_obligations_verified_4`: sustituido por `modelo_289_profile_obligations_expected_4`.
- `modelo_289_profile_obligations_no_unverified_or_extra`: sustituido por `modelo_289_profile_obligations_no_extra_profiles`.
- Nuevo check: `modelo_289_profile_obligations_verified_or_fail_closed_4`.
- Deep audit: `modelo_289_obligation_context_verified_or_fail_closed` y `modelo_289_profile_evidence_notice_verified_or_fail_closed`.

Owner propuesto: AEAT CRS/DAC2 evidence.

Historia Ralph:

Como mantenedor del contrato AEAT/CRS, quiero auditar las 4 obligaciones `obligacion_perfil` del Modelo 289 por perfil y decidir, fila por fila, si se puede recuperar `source_hash` desde fuente primaria o si debe mantenerse `fail-closed`, para que `/v1/modelos/aeat/289` no mezcle cierre documental del formulario con aplicabilidad CRS/DAC2 por sujeto obligado.

No-objetivos:

- No promover el Modelo 289 completo por tener normativa/instrucciones/casillas cargadas.
- No usar ejemplos XML, ficha general o manual CRS como prueba suficiente de obligacion por perfil si no prueban sujeto obligado y supuesto.
- No cambiar `verified`, `safe_to_answer` ni `completeness` sin `source_hash` y `capture_date`.

RED inicial:

- `mcp_validation_suite.py`: `modelo_289_profile_obligations_verified_4=0`, `modelo_289_profile_obligations_no_unverified_or_extra=4`, `modelo_289_obligation_context_contract=false`.
- VPS actual: `obligacion_perfil` 289 tiene `total=4`, `safe_true=0`, `verified_true=0`, `missing_hash=4`.
- Read-only adicional: no hay `source_revision` con match exacto para la URL legacy `https://sede.agenciatributaria.gob.es/Sede/ayuda/modelos-formularios-presentaciones/modelos-200-299/modelo-289.html`.
- Recursos activos 289 con hash existen para RD 1021/2015, HAP/1695/2016, GI42, manual CRS y XSD/WSDL, pero no prueban por si solos cada perfil operativo como sujeto obligado.

Entrada minima:

```sql
SELECT perfil_codigo, modelo_aeat, norma_codigo, articulo_referencia,
       source_url, source_hash, capture_date, verified, safe_to_answer,
       completeness, descripcion
FROM obligacion_perfil
WHERE modelo_aeat='289'
ORDER BY perfil_codigo;
```

GREEN permitido A - evidencia recuperada:

- Las filas promovidas tienen fuente primaria exacta, `source_hash`, `capture_date`, sujeto obligado y supuesto operativo defendibles.
- La migracion es idempotente y solo toca las filas probadas.
- `/v1/modelos/aeat/289` expone `obligation_context` sin notices falsamente optimistas.

GREEN permitido B - fail-closed explicito:

- Si no hay fuente primaria suficiente, las 4 filas siguen `verified=false`, `safe_to_answer=false`, `completeness='parcial'`.
- La suite se ajusta solo si el contrato esperado debe reflejar fail-closed documentado; no se baja el umbral para esconder deuda.
- El doc de auditoria 289 declara que la capa `obligacion_perfil` queda fuera del cierre documental.

Criterio de salida:

- `mcp_validation_suite.py --read-only --base-url http://api:8000` ya no falla por ambiguedad de contrato 289: o pasa por evidencia completa, o falla/espera fail-closed con razon documentada y test local equivalente.
- `mcp_deep_contract_audit.py` no reporta `modelo_289_obligation_context_verified` como `UNKNOWN`; el resultado es PASS o FAIL documentado.

Artefactos a cambiar:

- Migracion de datos solo si hay evidencia primaria por sujeto obligado/supuesto.
- `docs/aeat-289-documental-audit-2026-05-24.md`
- Tests de `obligation_context` si cambia el contrato.

Descripcion:

La capa documental del Modelo 289 pasa checks de normativa/instrucciones/reglas/casillas, pero `obligacion_perfil` sigue sin hash en 4 perfiles y no puede promocionarse. Este issue no debe mezclar cierre documental del formulario con aplicabilidad CRS/DAC2 por perfil.

Checklist de salida:

- [x] Inventariar las 4 obligaciones 289 por perfil con `source_url`, `source_hash`, `capture_date`, `verified`, `safe_to_answer`.
- [x] Localizar fuente primaria que pruebe sujeto obligado y supuesto concreto, no solo ficha/documentacion general del modelo.
- [x] Si no hay evidencia suficiente, mantener fail-closed y ajustar expectativas de suite/documentacion.
- [ ] Si hay evidencia suficiente, migrar solo filas probadas y conservar trazabilidad.
- [x] Confirmar contrato local de `/v1/modelos/aeat/289` y `mcp_validation_suite.py` sin promocion indebida.

### Issue MCP-DATA-03 - Aplicabilidad fiscal y routing de `sociedad_valores`

Estado local: IMPLEMENTED AS FAIL-CLOSED CONTRACT. `docs/aeat-202-profile-routing-audit-2026-05-24.md` documenta el RED productivo y la decision de no promover `verified=true` sin `source_hash`.

Impacto: bloquea `modelo_202_all_profiles_loaded` y `perfil_sociedad_valores_fiscal_routing_contract`.

Owner propuesto: AEAT fiscal profiles.

Historia Ralph:

Como mantenedor de perfiles fiscales AEAT, quiero auditar la aplicabilidad fiscal y el routing de perfil para `sociedad_valores`, usando Modelo 202 como obligacion concreta de prueba, para que el contrato distinga entre obligacion cargada, obligacion verificada y obligacion fail-closed.

No-objetivos:

- No probar aplicabilidad con casillas del formulario ni ficha generica si no prueban sujeto obligado/perfil.
- No reintroducir `safe_to_answer=true` en obligaciones 202 sin hash.
- No cambiar el endpoint de routing fiscal para ocultar que 202 esta presente pero no verificado.

RED inicial:

- `mcp_validation_suite.py`: `modelo_202_all_profiles_loaded=0` frente a minimo `6`.
- `perfil_sociedad_valores_fiscal_routing_contract=false`: `/v1/perfil/sociedad_valores/obligaciones?dominio=FISCAL` incluye `modelo_202_count=1`, pero `modelo_202_verified=[false]`.
- Produccion tiene 6 filas `obligacion_perfil` para Modelo 202 (`agencia_valores`, `eaf`, `empresa_servicios_pago`, `entidad_credito`, `sgiic`, `sociedad_valores`), todas con `verified=false`, `safe_to_answer=false`, `source_hash=NULL`, `capture_date=2026-05-17` y notas fail-closed.

Entrada minima:

```sql
SELECT perfil_codigo, modelo_aeat, norma_codigo, articulo_referencia,
       source_url, source_hash, capture_date, verified, safe_to_answer,
       completeness, plazo_descripcion
FROM obligacion_perfil
WHERE modelo_aeat='202'
ORDER BY perfil_codigo;
```

Probes API:

```text
GET /v1/perfil/sociedad_valores/obligaciones?dominio=FISCAL
GET /v1/modelos/aeat/202
```

GREEN permitido A - evidencia recuperada:

- Cada perfil promovido tiene fuente primaria con `source_hash` y `capture_date`.
- La base legal y plazo operativo de Modelo 202 quedan trazados por perfil.
- El contrato de routing fiscal pasa porque al menos el 202 de `sociedad_valores` es verificable, no porque se haya filtrado.

GREEN permitido B - fail-closed explicito:

- Si Modelo 202 no puede probarse por los 6 perfiles, mantener `verified=false` y `safe_to_answer=false`.
- `modelo_202_all_profiles_loaded` comprueba presencia de los 6 perfiles esperados.
- `modelo_202_profiles_verified_or_fail_closed_6` comprueba que cada perfil este verificado con hash/captura o fail-closed explicito.
- Documentar que el routing fiscal puede listar modelos presentes pero no verificados, y que consumidores deben respetar `verified=false`.

Criterio de salida:

- `perfil_sociedad_valores_fiscal_routing_contract` pasa con evidencia o fail-closed explicito; nunca por ocultar el 202.
- `modelo_202_all_profiles_loaded` deja de ser un umbral historico opaco: verifica presencia de los 6 perfiles esperados.
- `modelo_202_profiles_verified_or_fail_closed_6` impide que `verified=true` sin `source_hash` cuente como cierre.

Artefactos a cambiar:

- Datos/migraciones de `obligacion_perfil` Modelo 202, si procede.
- `scripts/maintenance/mcp_validation_suite.py`, si el contrato esperado cambia.
- Docs de cobertura AEAT/Modelo 202.

Descripcion:

El endpoint fiscal de `sociedad_valores` incluye Modelo 202 y excluye 123/124, pero el item 202 esta `verified=false`. La suite espera 6 perfiles verificados para 202. Hay que auditar fuente, plazo, sujeto obligado y aplicabilidad antes de recuperar seguridad.

Checklist de salida:

- [x] Inventariar perfiles con Modelo 202 y estado de evidencia.
- [x] Confirmar que existen recursos oficiales activos del Modelo 202 con hash a nivel modelo/campana, pero no reconciliados en `obligacion_perfil`.
- [ ] No usar casillas o ficha general como prueba de obligacion por sujeto si no basta.
- [x] Resolver que el contrato exige 6 perfiles cargados y estado verificado o fail-closed explicito.
- [ ] Reejecutar check focal de Modelo 202 y routing fiscal.

### Issue MCP-DATA-04 - Recuperar evidencia RTS1/RTS2 o ajustar contrato parcial

Impacto: bloquea `rts1_rts2_obligations_all_verified` y `sociedad_valores_rts1_evidence_notice_verified`.

Owner propuesto: EU markets evidence.

Artefactos a cambiar:

- Datos/migraciones de obligaciones RTS1/RTS2.
- Docs de Sprint I RTS1/RTS2 si se confirma drift.
- `mcp_validation_suite.py` solo si el contrato esperado debe aceptar parcialidad.

Descripcion:

Las obligaciones RTS1/RTS2 existen, pero 12 no estan verificadas. La decision es binaria: recuperar evidencia EUR-Lex con hash/captura suficiente o mantenerlas parciales y hacer que el contrato lo refleje sin reclamar verificacion.

Checklist de salida:

- [ ] Listar las 12 obligaciones no verificadas con norma/articulo/source.
- [ ] Verificar fuente EUR-Lex y capturar hash/fecha para cada obligacion promocionada.
- [ ] Confirmar que no se contaminan perfiles excluidos (`eaf`, `empresa_servicios_pago`).
- [ ] Reejecutar `mcp_validation_suite.py` y deep audit de `profile_applicability_contracts`.

### Issue MCP-DATA-05 - Reconciliar MiCA CASP y `emisor_token` verified/completeness

Impacto: bloquea `casp_obligations_all_verified`, `emisor_token_obligations_all_verified`, `emisor_token_art_base_obligations_completa`, `casp_all_verified`, `emisor_token_all_verified` y `emisor_token_art_completa`.

Owner propuesto: MiCA evidence.

Artefactos a cambiar:

- Datos/migraciones de obligaciones CASP y `emisor_token`, si hay evidencia suficiente.
- `docs/sprint-m-mica-report.md`, `docs/sprint-n-emisor-token-report.md` o doc de drift nuevo.
- Suite MCP/deep audit solo si el contrato actual no representa el estado fail-closed real.

Descripcion:

La suite historica espera CASP y `emisor_token` verificados, pero el estado productivo actual devuelve `0` verified y `0` ART completa. Hay que reconciliar si esto es drift de datos tras fail-closed, perdida de evidencia, o un contrato de suite que quedo mas optimista que el producto.

Checklist de salida:

- [ ] Inventariar CASP y `emisor_token`: total, verified, completeness, source hash y capture date.
- [ ] Separar ART base de EMT parcial en `emisor_token`.
- [ ] Confirmar si existe corpus supervisor suficiente o si debe mantenerse gap explicito.
- [ ] Promover solo filas con evidencia primaria completa.
- [ ] Reejecutar `mcp_validation_suite.py` y `mcp_deep_contract_audit.py` para contratos MiCA.

### Issue MCP-DATA-06 - Resolver aplicabilidad Modelo 303 en `empresa_servicios_pago`

Impacto: bloquea `empresa_servicios_pago_modelo_303_completa` dentro de `profile_applicability_contracts`.

Owner propuesto: AEAT fiscal profiles.

Artefactos a cambiar:

- Datos/migraciones de `obligacion_perfil` Modelo 303, si procede.
- Tests de aplicabilidad de perfiles.
- Docs de cobertura AEAT si se confirma parcialidad.

Descripcion:

El deep audit detecta que el contrato de aplicabilidad espera Modelo 303 completo para `empresa_servicios_pago`, pero el estado actual no lo cumple. Este fallo no aparece entre los 12 checks semanticos principales, pero si bloquea el deep audit.

Checklist de salida:

- [ ] Inspeccionar payload de `/v1/perfil/empresa_servicios_pago/obligaciones?dominio=FISCAL`.
- [ ] Confirmar fuente primaria de aplicabilidad de Modelo 303 para el perfil.
- [ ] Decidir si se recupera evidencia o si el contrato debe dejar de exigir `completa`.
- [ ] Reejecutar `mcp_deep_contract_audit.py` y confirmar que `profile_applicability_contracts` pasa o queda con un fallo distinto documentado.
