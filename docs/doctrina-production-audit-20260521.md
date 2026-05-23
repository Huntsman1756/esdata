# Auditoria produccion DGT/TEAC y lote piloto de lineas de criterio

## Estado

- Fecha: 2026-05-21.
- Entorno auditado: VPS `steamcases-vps`, repo `/srv/esdata`, commit productivo `30154a3`.
- API health: `https://api.desuscribir.es/health` devuelve `status=ok`, `database=ok`.
- Metodo inicial: consultas SQL read-only via `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec -T postgres psql`.
- Actualizacion posterior 2026-05-21: despliegue acotado de `api` y escritura productiva minima en `documento_articulo` para persistir el enlace auditado D-01 `V0166-25` -> `TRLIRNR art. 31`.

## Estado inicial read-only

DGT/TEAC existian en produccion como corpus doctrinal parcial y consultable, pero no como familia de lineas de criterio completa.

Hallazgos iniciales contra el VPS antes del despliegue del contrato doctrinal:

- DGT tiene `18.631` consultas vinculantes cargadas, todas con URL oficial PETETE y texto.
- TEAC tiene `558` resoluciones DYCTEA cargadas, todas con URL oficial; `290` estan `complete` y `268` `partial`.
- `source_revision` conserva hash SHA-256 para `18.631` consultas DGT y `558` documentos TEAC, pero `documento_interpretativo` no tiene columnas directas `source_hash` ni `capture_date`.
- En el commit productivo inicial `30154a3`, produccion aun no tenia desplegado el endpoint local nuevo `/v1/doctrina/lineas/coverage`: devolvia `404` por caer en el router legacy `/{referencia:path}`.
- En ese estado inicial existian `7` filas activas en `linea_criterio`, pero eran editoriales/genericas y ninguna tenia referencia DGT/TEAC cargada con URL oficial. No habia ninguna linea completa.

## Estado tras despliegue y curacion

Tras el despliegue acotado de `api` y la curacion D-01, el contrato doctrinal responde en produccion, pero la familia completa sigue `implemented_partial`.

- `/v1/doctrina/lineas/coverage` devuelve HTTP 200 con `estado=implemented_partial`, `lineas_total=16`, `lineas_complete=3` y `safe_to_answer=false`.
- D-01 queda como primera linea piloto `complete` para consulta factual acotada porque ya tiene fuente oficial, hash/captura, anclaje persistido `TRLIRNR art. 31`, vigencia historica explicita y relacion modelo/supuesto persistida en `criterio_relacion`.
- La relacion con modelos 216/296 esta auditada por curacion del supuesto en `V0166-25` y queda persistida como relacion especifica de modelo/supuesto; no debe extrapolarse fuera de ese supuesto.
- El resto del lote sigue `partial` o `target` hasta completar la misma curacion.

Conclusion: la familia debe seguir `implemented_partial`. La diferencia entre estado inicial y estado final es el despliegue del contrato y el cierre acotado de D-01, no una cobertura doctrinal completa.

## Corpus real de produccion

| Fuente | Tipo | Total | Con URL | Complete | Partial | Con texto | Rango fechas |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| DGT | `consulta_vinculante` | 18.631 | 18.631 | 18.621 | 10 | 18.631 | 2017-01-02 a 2026-02-05 |
| TEAC | `resolucion_teac` | 558 | 558 | 290 | 268 | 552 | 2018-01-16 a 2026-04-30 |

## Hashes y captura

| Fuente revision | Tipo entidad | Total | Con SHA-256 | Con URL registrada | Rango `fetched_at` |
| --- | --- | ---: | ---: | ---: | --- |
| `worker-dgt` | `consulta` | 18.631 | 18.631 | 0 | 2026-05-10 a 2026-05-12 |
| `cron-dgt-weekly` | `consulta` | 10 | 10 | 10 | 2026-05-10 |
| `cron-teac-weekly` | `documento` | 558 | 558 | 0 | 2026-05-17 a 2026-05-20 |
| `worker-teac` | `documento` | 10 | 10 | 0 | 2026-05-19 |

Interpretacion: hay hash equivalente en `source_revision`, pero no esta proyectado directamente en las respuestas legacy de doctrina ni en `linea_criterio`. Para marcar una linea `complete`, el contrato debe unir `documento_interpretativo` con `source_revision` o persistir `source_hash`/`capture_date` normalizados.

## Enlaces a articulos

| Fuente | Documentos | Enlaces `documento_articulo` | Articulos distintos | Enlaces exactos | Enlaces debiles |
| --- | ---: | ---: | ---: | ---: | ---: |
| DGT | 18.631 | 49.676 | 479 | 49.647 | 29 |
| TEAC | 558 | 87 | 63 | 40 | 47 |

Interpretacion: DGT tiene una base operativa fuerte para curacion por articulo; TEAC existe pero necesita revision manual porque casi la mitad de sus enlaces son debiles o parciales.

## Estado de lineas existentes

Produccion contiene `7` lineas activas en `linea_criterio`.

| ID | Titulo | Refs totales | Refs DGT/TEAC declaradas | Refs DGT/TEAC cargadas | Con URL oficial | Enlaces articulo |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | IVA reducido en restauracion | 3 | 1 | 0 | 0 | 0 |
| 2 | Comisiones preferencia e indiferencia | 2 | 0 | 0 | 0 | 0 |
| 3 | Ejecucion preferente de ordenes | 3 | 1 | 0 | 0 | 0 |
| 4 | Adecuacion y conveniencia de productos | 3 | 1 | 0 | 0 | 0 |
| 5 | Informacion privilegiada y listas insider | 3 | 0 | 0 | 0 | 0 |
| 6 | Gobierno de productos | 2 | 0 | 0 | 0 | 0 |
| 7 | Comunicacion de indicios de LP | 3 | 0 | 0 | 0 | 0 |

Estas lineas no son el lote piloto doctrinal fiscal. Son lineas editoriales historicas y deben tratarse como `target` o `partial` hasta reemplazar referencias desnudas por documentos oficiales cargados.

## Cobertura por temas prioritarios

Busqueda refinada sobre texto/titulo DGT/TEAC, contando solo corpus productivo. Los conteos son senal de disponibilidad para curacion, no cobertura doctrinal completa.

| Tema | DGT total | DGT complete | DGT con articulo | TEAC total | TEAC complete | TEAC con articulo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Retenciones no residentes | 1.808 | 1.807 | 1.808 | 4 | 2 | 2 |
| IVA intracomunitario | 2.006 | 2.002 | 2.006 | 1 | 0 | 0 |
| Operaciones vinculadas | 65 | 65 | 65 | 12 | 12 | 3 |
| CRS/FATCA | 3 DGT candidatos estrictos | 3 | 3 | 0 | 0 | 0 |
| Criptoactivos | 90 | 89 | 90 | 0 | 0 | 0 |
| Dividendos/intereses | 4.232 | 4.231 | 4.229 | 22 | 19 | 5 |
| Canones | 135 | 135 | 135 | 6 | 2 | 1 |
| Establecimiento permanente | 2.192 | 2.190 | 2.192 | 2 | 2 | 1 |
| Servicios profesionales | 960 | 960 | 960 | 0 | 0 | 0 |

## Lote piloto seleccionado

Estado inicial del lote: `target_for_curation`. Las referencias existen en produccion y tienen URL oficial; varias tienen texto `complete` y enlaces a articulos. No estan aun normalizadas como lineas `complete`.

Estado local y VPS tras curacion piloto 2026-05-21: la API read-only reconoce codigos `D-01` a `D-09`, resuelve sus referencias contra `documento_interpretativo`, `source_revision` y `documento_articulo`, y expone `source_hash`/`capture_date` cuando existen. D-01 queda `complete` y `safe_to_answer=true` por cumplir los cierres auditados; las otras lineas siguen fail-closed. Esto demuestra el contrato doctrinal, pero no cambia la familia a `complete`.

Despliegue VPS 2026-05-21: se reconstruyo solo `api`; no hubo migraciones en esa fase. Se persistio en produccion `documento_articulo` para `V0166-25` -> `TRLIRNR art. 31` con `metodo_enlace='manual_official'`, `confianza_enlace=1.00` y nota de curacion D-01. Validacion productiva con API key: `/v1/doctrina/lineas/coverage` devuelve HTTP 200 con `estado=implemented_partial`, `lineas_total=16`, `lineas_complete=1`, `lineas_con_articulo=2`, `safe_to_answer=false`; `/v1/doctrina/lineas/D-01` devuelve HTTP 200 con URL PETETE, SHA-256, `capture_date`, `articulo_referencia=TRLIRNR art. 31`, `modelo_aeat_referencia=216/296`, `estado_vigente=historico_a_fecha_consulta`, `completeness=complete`, `safe_to_answer=true` y `review_required=false`. Follow-up local: se anade migracion aditiva `criterio_relacion` para persistir la relacion modelo/supuesto D-01 y habilitar lineas genericas con evidencia completa.

| Linea piloto | Estado ahora | Fuente base | Evidencia productiva | Motivo de seleccion | Siguiente accion |
| --- | --- | --- | --- | --- | --- |
| D-01 Retenciones no residentes | `complete` | DGT `V0166-25`; TEAC `00/02188/2017/00/00` como soporte parcial | DGT complete con URL PETETE, SHA-256, `capture_date`, enlace persistido `TRLIRNR art. 31`, vigencia historica explicita y modelos 216/296 persistidos en `criterio_relacion` por curacion del supuesto. TEAC mantiene URL/hash pero sin anclaje TRLIRNR propio | Tema frecuente, alto riesgo de sobreafirmar, conecta IRNR/modelos | No extrapolar fuera del supuesto de `V0166-25`; curar D-02 como siguiente linea |
| D-02 IVA intracomunitario | `complete` | DGT `V0963-25`; `V0236-26` descartada; TEAC `00/02766/2015/00/00` soporte parcial | DGT `V0963-25` complete con URL PETETE, SHA-256, `capture_date`, supuesto de adquisicion intracomunitaria de bienes, `LIVA art. 13` y modelo 349; la migracion 0086 persiste `documento_articulo` y `criterio_relacion` como `complete`. `V0236-26` sigue descartada porque trata tipo impositivo/`LIVA art. 91`. TEAC ROI es partial y sin articulo trazable | Alto volumen DGT y utilidad fiscal | Cierre acotado a adquisicion intracomunitaria; no extrapolar a entregas ni a otros supuestos IVA |
| D-03 Operaciones vinculadas | `partial` | DGT `V0144-26`; TEAC `00/06460/2019/00/00` | DGT complete con URL/hash y `LIS art. 18` persistido como relacion parcial en `criterio_relacion`; TEAC soporte procedimental LGT. La auditoria 2026-05-23 no localiza DGT cargada con `modelo 232` y operaciones vinculadas | Buen volumen y trazabilidad suficiente para curacion | Cerrar solo si aparece relacion documental con modelo 232 por supuesto; `LIS art. 18` solo no basta |
| D-04 CRS/FATCA | `complete` | DGT `V0138-24` | Complete, URL PETETE, hash, CRS/FATCA, RD 1021/2015, LGT disposicion adicional vigesimo segunda y modelo 289; la migracion 0087 persiste `documento_articulo` y `criterio_relacion` como `complete` | Bajo volumen y buen candidato para curacion controlada | Cierre acotado; no usar como procedimiento completo de reporte |
| D-05 Criptoactivos | `partial` | DGT `V0162-26` | Complete, URL PETETE, hash y texto sobre monedas virtuales; no confirma modelo 721 ni articulo fiscal operativo suficiente | Tema prioritario con corpus DGT suficiente | Elegir anclaje normativo exacto y modelo si aparece en fuente oficial |
| D-06 Dividendos/intereses | `partial` | DGT `V0187-26`; TEAC `00/00185/2017/00/00` | DGT complete con URL/hash y dividendos IRNR; texto menciona TRLIRNR arts. 13/14/31, pero no hay modelo 216/296 ni cierre para intereses | Alta frecuencia internacional y conectada con retenciones | Separar dividendos de intereses; persistir articulo solo tras decidir supuesto y modelo |
| D-07 Canones | `partial` | DGT `V0228-26` | Complete, URL PETETE y LIVA servicios/arrendamiento; no prueba canon IRNR ni modelo 216 | Lote acotado y con URL oficial | Descartar como cierre D-07 salvo que se redefina el supuesto; buscar fuente de canon IRNR real |
| D-08 Establecimiento permanente | `partial` | DGT `V0235-26`; TEAC `00/03519/2022/00/00` | DGT complete con obligaciones censales/fiscales y menciones de EP; TEAC trata IRPF art. 7.p. No hay modelo 200 ni convenio/supuesto IRNR cerrado | Tema estructural para IRNR/CDI | Buscar fuente EP IRNR/CDI o mantener abstencion por hechos/convenio |
| D-09 Servicios profesionales | `partial` | DGT `V0191-26` | Complete, URL PETETE, LIVA art. 20 y LGT art. 89; no prueba servicios profesionales IRNR/no residente ni modelo 216 | Buen candidato fiscal/IVA | Reubicar como IVA si procede o buscar fuente IRNR de servicios profesionales |

### Contrato local del lote piloto

- `GET /v1/doctrina/lineas/D-01` a `D-09` devuelve la linea piloto aunque el documento aun no exista localmente o en VPS; en ese caso queda `target`, sin `source_url`, sin `source_hash` y con `safe_to_answer=false`.
- Cuando la referencia esta cargada y existe `source_revision`, la respuesta proyecta `source_url`, `source_hash` y `capture_date`.
- Las lineas genericas DB-backed solo pueden pasar a `complete` si ademas de `source_revision` tienen articulo y relacion normalizada en `criterio_relacion` con impuesto, modelo/tipo de supuesto, `verified=true` y `completeness=complete`.
- Cuando la linea declara un articulo esperado, la API no sustituye ese anclaje por otro articulo detectado en el documento; si no coincide, `articulo_referencia` queda `null`.
- `/v1/doctrina/lineas/{codigo}/relaciones` declara relaciones por documento, articulo, modelo y tipo de renta. En D-01 la consulta DGT principal queda verificada, mientras TEAC sigue como soporte parcial sin articulo/modelo propio. D-03 expone relacion parcial persistida con `verified=true` y `completeness=partial`; D-04 expone la relacion principal `V0138-24` como `complete` con 0087. El endpoint conserva `safe_to_answer=false` cuando la superficie de relaciones mezcla soportes parciales.
- `/v1/doctrina/lineas?tema=...&impuesto=...&modelo=...` incluye el lote piloto en filtros exploratorios.
- `/v1/doctrina/lineas/coverage` suma las 9 lineas piloto, devuelve `lineas_complete=3` y `lineas_con_articulo=4` con 0087 desplegada, y conserva la familia como `implemented_partial`.

### Curacion D-02 a D-09 2026-05-21

Resultado: ninguna linea adicional pasa a `complete`.

- D-02 no usa `V0236-26` como cierre porque el documento trata tipo impositivo (`LIVA art. 91`), no supuesto intracomunitario expreso. La curacion 2026-05-23 selecciona `V0963-25` como fuente principal solo para adquisicion intracomunitaria de bienes: `LIVA art. 13`, modelo 349, hash/captura y relacion `modelo_supuesto` completa en migracion 0086. El cierre no autoriza extrapolar a entregas intracomunitarias (`LIVA art. 25`) ni a otros supuestos IVA.
- D-03 queda como parcial fuerte: expone `LIS art. 18` desde `V0144-26` y lo persiste como relacion parcial, pero no declara modelo 232 ni `safe_to_answer=true`; la busqueda estricta en DGT cargada no localiza `modelo 232`.
- D-04 queda `complete` con 0087: `V0138-24` se acota a CRS/FATCA, LGT disposicion adicional vigesimo segunda y modelo 289; no debe usarse como procedimiento completo de reporte.
- D-05 queda parcial: hay fuente sobre monedas virtuales, pero no modelo 721 ni articulo operativo suficiente.
- D-06 queda parcial: `V0187-26` cubre dividendos IRNR y menciona TRLIRNR, pero no intereses ni modelo 216/296 trazable.
- D-07 queda parcial y no reutiliza LIVA servicios como canon IRNR.
- D-08 queda parcial por dependencia de hechos/convenio y ausencia de modelo 200 trazable.
- D-09 queda parcial y no reutiliza LIVA art. 20 como servicios profesionales IRNR.

### Inventario estable D-01 a D-09

| Linea | Estado | Fuente principal | Fuente soporte | Articulo expuesto | Modelo expuesto | Motivo exacto del estado | Siguiente evidencia necesaria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-01 Retenciones no residentes | `complete` | DGT `V0166-25` | TEAC `00/02188/2017/00/00` parcial | `TRLIRNR art. 31` | `216/296` | Cumple fuente oficial, hash/captura, enlace persistido, vigencia historica y modelo/supuesto persistido en `criterio_relacion` | No extrapolar fuera del supuesto; usar como patron de cierre |
| D-02 IVA intracomunitario | `complete` | DGT `V0963-25` | TEAC `00/02766/2015/00/00` parcial; `V0236-26` descartada | `LIVA art. 13` para adquisicion intracomunitaria de bienes | `349` por relacion `modelo_supuesto` persistida | La fuente principal trata adquisiciones intracomunitarias de bienes y obligaciones de declaracion recapitulativa; se persisten hash/captura, articulo, modelo y vigencia historica. `V0236-26` queda fuera por `LIVA art. 91` | No usar esta linea para entregas intracomunitarias ni supuestos de tipo impositivo |
| D-03 Operaciones vinculadas | `partial` | DGT `V0144-26` | TEAC `00/06460/2019/00/00` procedimental | `LIS art. 18`; relacion parcial persistida | Bloqueado: `232` ausente en DGT cargada | Hay anclaje normativo, pero falta relacion documental con modelo 232 | Fuente o relacion oficial que conecte modelo 232 con el supuesto; no completar por inferencia |
| D-04 CRS/FATCA | `complete` | DGT `V0138-24` | Ninguna | `LGT art. vigésimo segunda` | `289` por relacion `modelo_supuesto` persistida | La fuente menciona CRS/FATCA, RD 1021/2015, LGT DA 22 y modelo 289; se persisten hash/captura, articulo, modelo y vigencia historica | No usar como procedimiento completo de reporte |
| D-05 Criptoactivos | `partial` | DGT `V0162-26` | Ninguna | Bloqueado: enlaces actuales no cierran el criterio cripto fiscal | Bloqueado: `721` no consta como relacion suficiente | Hay texto sobre monedas virtuales, pero no articulo operativo ni modelo cerrado | Fuente o relacion documental con articulo/modelo exactos y tipo de operacion |
| D-06 Dividendos e intereses | `partial` | DGT `V0187-26` | TEAC `00/00185/2017/00/00` | Bloqueado hasta separar dividendos/intereses y persistir articulo correcto | Bloqueado: `216` no trazado por supuesto | La fuente cubre dividendos IRNR y menciona TRLIRNR, pero no cierra intereses ni modelo | Dividir linea o confirmar fuente que cubra ambos tipos de renta, articulo y modelo |
| D-07 Canones | `partial` | DGT `V0228-26` | Ninguna | Bloqueado: LIVA servicios no es canon IRNR | Bloqueado: `216` no trazado | La fuente trata prestaciones de servicios/LIVA, no canon IRNR | Nueva fuente de canon/royalty IRNR con convenio o articulo aplicable y modelo |
| D-08 Establecimiento permanente | `partial` | DGT `V0235-26` | TEAC `00/03519/2022/00/00` | Bloqueado: falta articulo IRNR/CDI del supuesto | Bloqueado: `200` no trazado | Depende de hechos/convenio y los documentos actuales no cierran EP IRNR | Fuente EP IRNR/CDI con hechos, convenio/articulo y estado historico |
| D-09 Servicios profesionales | `partial` | DGT `V0191-26` | Ninguna | Bloqueado: `LIVA art. 20` no es servicios profesionales IRNR | Bloqueado: `216` no trazado | La fuente actual es exencion IVA, no cierre IRNR/no residente | Nueva fuente IRNR de servicios profesionales con articulo, pais/convenio si aplica y modelo |

### Curacion D-01 2026-05-21

Resultado: D-01 pasa a `complete` para consulta factual acotada.

- `V0223-26` queda descartada como consulta principal D-01: tiene fuente/hash/captura, pero en produccion encaja con modelo 190/IRPF y no confirma anclaje IRNR.
- `V0166-25` queda como consulta principal D-01: `row_completeness=complete`, URL PETETE, SHA-256 en `source_revision`, `capture_date`, texto oficial con referencia a Real Decreto Legislativo 5/2004, articulo 31, y modelos 216/296.
- `00/02188/2017/00/00` queda como soporte TEAC parcial: tiene URL/hash y trata IRNR/dividendos/retencion, pero su enlace `documento_articulo` productivo no confirma TRLIRNR; no se usa para completar articulo.
- Se persiste `documento_articulo` para `V0166-25` -> `TRLIRNR art. 31` con metodo `manual_official`, confianza `1.00` y nota `Curacion D-01: texto oficial auditado`.
- La API exige simultaneamente fuente/hash, referencia primaria completa, enlace persistido, `vigencia_estado=historico_a_fecha_consulta` y `modelo_evidencia=official_text_audited_by_suppuesto`; si falta cualquiera, D-01 vuelve a `partial`.
- El modelo 216/296 esta auditado por curacion del supuesto en la fuente oficial y se persiste en `criterio_relacion` como relacion `modelo_supuesto` para D-01.
- La validacion VPS confirma `completeness=complete`, `safe_to_answer=true` y `review_required=false` para `/v1/doctrina/lineas/D-01`. La familia mantiene `safe_to_answer=false` en `/coverage` porque el resto del lote no esta completo.

## Abstencion segura

Reglas confirmadas por auditoria:

- Si la linea solo existe como `linea_criterio` con referencia desnuda, debe devolver `safe_to_answer=false`.
- Si el documento existe pero no tiene articulo/impuesto/modelo normalizado, debe seguir `partial`.
- Si la relacion con modelo AEAT sale de keyword o inferencia, no se debe presentar como oficial.
- Si solo hay TEAC partial o metadata-heavy, no se debe convertir en criterio cerrado.
- Si falta proyeccion de `source_revision.content_hash_sha256` o `fetched_at`, no se cumple el punto 3 del criterio de hecho.

## Siguiente accion exacta

1. Cerrar D-03 solo si aparece relacion documental con modelo 232 y vigencia.
2. Crear una migracion aditiva o vista materializada si se decide persistir `source_hash` y `capture_date` fuera de `source_revision`.
3. Crear/actualizar lineas piloto restantes con referencias oficiales cargadas, no referencias desnudas.
4. Mantener cada linea piloto como `partial` hasta que pase los 8 puntos del criterio de hecho.
