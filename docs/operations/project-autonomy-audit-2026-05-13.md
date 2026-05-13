# ESData Project Autonomy Audit - 2026-05-13

Estado: auditoria de proyecto completa, con verificaciones read-only en VPS y subauditorias paralelas por dominios, infraestructura, API/MCP, SQL, seguridad y skills.

## Verificacion Ejecutada

Entorno VPS: `212.227.227.64`, usuario `deploy`, repo `/srv/esdata`, Docker Compose prod.

Evidencia operativa:

- VPS repo desplegado: `57445f3` (`[W-06] close worker cadence hardening`).
- Repo local: `90194aff` antes de esta auditoria; los commits posteriores al VPS son paquete de skills/config OpenAI, no runtime API.
- Compose: `api`, `postgres`, `web`, Prometheus, Grafana, Alertmanager, backup y workers persistentes levantados.
- `/status`: `api=ok`, `database=ok`, `workers_total=36`, sin workers stale.
- `weekly-accuracy-check.sh`: PASS, `worker_cadence_declared=37/37`, `worker_cadence_missing=0`.
- `mcp_validation_suite.py --read-only --base-url http://api:8000`: `ok=true`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=true`, `tools_returned=70`, `expected_operations=70`, OpenAPI GPT `path_count=72`, `operation_count=72`, `ApiKeyAuth`.
- OpenAPI GPT en repo VPS: `docs/openapi-gpt.json=72 paths`, `docs/openapi-gpt-3.0.json=72 paths`, `ApiKeyAuth`.
- DB productiva: `aeat_modelo=219`, `modelo_campana=232`,
  `modelo_casilla=31101`, `norma=37`, `articulo=1062`,
  `version_articulo=2345`, `documento_interpretativo=18799`,
  `query_audit_log=1299`, `sync_log=873`.
- Distribucion por fuente en `documento_interpretativo`: `dgt=18631`, `cnmv=72`, `borme=51`, `aepd=25`, `teac=10`, `boe_diario=3`, `bde=3`, `sepblac=2`, `bdns=1`, `cendoj=1`.
- VPS hardening observado: `PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, UFW activo con 22/80/443 permitidos y 8080/8501/8502 denegados, fail2ban `sshd` activo.
- Backup local valido: ultimo gzip verificado en `/srv/backups/esdata/esdata_20260510_201552.sql.gz`.

## Estado De Produccion

El MCP esta operativo y autonomo para las superficies verificadas. La afirmacion correcta no es "todo esta cubierto", sino:

- ESData puede responder con autoridad cuando `verified=true` y `completeness` es `completa`, `no-casillas-expected` o `deprecated`.
- ESData responde con limite honesto cuando la fuente esta parcial, no cargada o no se puede parsear sin riesgo.
- El VPS tiene workers, cadencias, validacion MCP, alertas y revision semanal operativas.
- GPT Actions y MCP comparten contratos de verdad; las Actions usan `X-API-Key`.

## Gaps P0 Cerrados En Esta Auditoria Local

1. Workflow Railway obsoleto seguia activo en `push main`.
   - Riesgo: despliegue accidental fuera del stack Docker Compose canonico.
   - Accion: `.github/workflows/deploy.yml` queda inerte y solo manual, con job explicativo sin secretos ni `railway up`.

2. Endpoints directos de retrieval sin auditoria.
   - Evidencia VPS: llamada a `/v1/boe-diario?limit=1` con `X-Request-ID` no escribia en `query_audit_log`.
   - Accion: se cablean `/v1/boe-diario`, `/v1/bde`, `/v1/bdns`, `/v1/sepblac` y `/v1/cendoj` al helper comun `record_retrieval_query_audit`.

3. `/v1/ai/query-audit` devolvia todo el historico sin paginacion.
   - Accion: se anaden `limit<=100`, `offset`, `has_more` y conteo total.

## Gaps P1 Pendientes

1. `webhook_events` se crea desde runtime si se usa el servicio de webhooks.
   - VPS actual: `to_regclass('public.webhook_events') = NULL`, por tanto no existe hoy.
   - Accion recomendada: mover la tabla a Alembic, aplicar RLS y eliminar DDL runtime de `apps/api/services/webhook_verification.py`.

2. `boe_modelos_worker.py` aun contiene DDL runtime defensivo sobre `sync_log`.
   - Accion recomendada: sustituir por verificacion de esquema/migracion y fallar claro si la migracion no esta aplicada.

3. Backup solo local al VPS.
   - Hay restore drill y gzip valido, pero falta replica offsite/inmutable.
   - Accion recomendada: copia diaria cifrada a S3-compatible o storage externo, con restore drill mensual automatizado.

4. Weekly accuracy cubre frescura fuerte de BOE, AEAT, EUR-Lex, CNMV y ESMA/MiCA, pero no todos los dominios.
   - Faltan checks explicitos para BORME, DGT/TEAC, AEPD, BDE, BDNS, SEPBLAC, CENDOJ, FATCA/GIIN, OFAC, CDI y PGC.
   - Accion recomendada: extender `scripts/weekly-accuracy-check.sh` o crear `source_freshness_snapshot` por dominio completo.

5. `mcp_deep_contract_audit.py` no esta programado.
   - Accion recomendada: ejecutarlo al menos diario o semanal junto al validation suite.

6. GPT Actions principales estan bien, pero conviene separar "curated GPT Actions" de "todo MCP HTTP".
   - Accion recomendada: snapshot test de paths permitidos para Actions y publicar un nombre de endpoint no limitado a `modelos`.

7. Dependencias e imagenes:
   - Accion aplicada: `.github/dependabot.yml` y `npm audit --audit-level=high`.
   - Pendiente: escaneo de imagenes/SBOM con Trivy/Grype y digests para `node-exporter`/`alertmanager`.

## Gaps P2 Pendientes

1. `X-User-ID` es identidad declarada por cliente con API key.
   - Accion recomendada: solo aceptar identidad de gateway confiable, o registrar `claimed_user_id` separado de `principal_verified=false`.

2. `regulatory_changes` sigue en SQL historico aunque `source_revision` es canonicamente la fuente de cambios.
   - VPS actual: `to_regclass('public.regulatory_changes') = NULL`.
   - Accion recomendada: limpiar SQL historico o marcarlo archivado para evitar doble fuente futura.

3. Integridad referencial incompleta en tablas regulatorias con columnas tipo `*_id` sin FK real.
   - Accion recomendada: revisar tablas `sfdr`, `csrd`, `crd/brrd/emir`, `xbrl` y decidir FK real o etiqueta `external_id`.

4. Corpus minimo en algunos dominios.
   - BDE, SEPBLAC, BDNS, CENDOJ y TEAC estan trazados pero tienen volumen pequeno.
   - Accion recomendada: mantener como parcial o abrir historias de expansion por fuente oficial estable.

5. Hermes auto-remediation esta desactivado por defecto.
   - Es prudente para evitar loops, pero no es autonomia total ante stale real.
   - Accion recomendada: allowlist limitada para reinicio de workers idempotentes, con cooldown y alerta.

## Estado Por Dominio

| Dominio | Estado | Condicion de confianza |
| --- | --- | --- |
| AEAT/Hacienda | Fuerte para modelos/casillas cargados; parcial para STATUS-D/E y procedimientos completos | Usar `verified/completeness`; no inferir obligatoriedad por entidad |
| BOE consolidado | Cubierto para corpus cargado | Texto con `boe_referencia/source_url`; versionado en `version_articulo` |
| BOE diario | Cubierto para documentos recientes cargados, separado del BOE consolidado | No tratar anuncios como legislacion consolidada |
| DGT/TEAC | DGT amplio, TEAC pequeno | Trazable, no exhaustivo |
| CNMV | Cubierto para documentos/circulares cargadas | No equivale a todo CNMV |
| ESMA/MiCA | CASP ESMA cargado; otros MiCA fail-closed | `configured_but_unavailable` cuando no hay datos |
| EUR-Lex | MiFID II con articulado; resto puede ser metadata-only | Autoridad solo por CELEX con texto parseado |
| BORME | Parcial heuristico | No usar como certificacion mercantil definitiva |
| AEPD | Guias/documentos cargados | No cubre sanciones completas |
| FATCA/CRS/GIIN/CDI | Referencias y GIIN masivo; procedimiento completo limitado | Responder `evidence_limited` para filing/how-to completo |
| OFAC/screening | OFAC cargado; otras listas fail-closed | No limpiar sanciones si la lista no esta cargada |
| BDE/BDNS/SEPBLAC/CENDOJ | Datos reales minimos | Parcial por corpus pequeno |

## MCP Best Practices Aplicadas

Criterio revisado contra la documentacion oficial de MCP y OpenAI Skills:

- Herramientas con schemas explicitos y contratos fail-closed.
- Separacion entre recursos oficiales cargados, herramientas, prompts/skills y razonamiento del agente.
- Grounding duro por fuente y `query_audit_log` para retrieval.
- Paginacion en respuestas que pueden crecer.
- Skills como workflows/gates, no como corpus ni autoridad normativa.
- Actions con `ApiKeyAuth` y contrato OpenAPI verificable.

## Siguiente Sprint Recomendado

1. `A-Webhook-RLS`: migrar `webhook_events` a Alembic + RLS y quitar DDL runtime.
2. `A-Retrieval-Audit-Complete`: test parametrizado de todas las operaciones `HTTP_MCP_OPERATIONS` y endpoints REST de retrieval contra `query_audit_log`.
3. `A-Weekly-Full-Freshness`: extender freshness semanal a todos los dominios y guardar snapshot historico.
4. `A-Backups-Offsite`: backup cifrado fuera del VPS + restore drill programado.
5. `A-Container-SBOM`: escaneo Trivy/Grype en CI y digests restantes.
6. `A-Actions-Curated`: spec GPT Actions curada y test de paths permitidos separado del catalogo MCP.
