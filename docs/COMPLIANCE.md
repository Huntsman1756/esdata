# Compliance

## Objetivo

Este documento resume el estado de cumplimiento operativo y normativo de `esdata` para handoff tecnico.

No sustituye asesoramiento juridico ni convierte el sistema en cumplimiento automatico. Su objetivo es dejar claro que esta `[IMPLEMENTED]`, que esta `[PARTIAL]` y que sigue siendo `[TARGET]`.

## Estado de lectura

- `[IMPLEMENTED]` presente en codigo, configuracion o documentacion activa y verificado durante esta auditoria
- `[PARTIAL]` presente solo en parte, o dependiente de datos/secretos/entorno no incluidos en el repo
- `[TARGET]` direccion deseada, no desplegada todavia

## Marco regulatorio contemplado

### Fiscal AEAT / Hacienda

- `[IMPLEMENTED]` infraestructura de modelos AEAT: `aeat_modelo`, `modelo_campana`, `modelo_casilla`, `modelo_clave`, `modelo_instruccion`, `modelo_normativa`, `modelo_campana_operativa`
- `[IMPLEMENTED]` API de modelos: `/v1/modelos/*`
- `[IMPLEMENTED]` cobertura documental y operativa de modelos ya cargados en DB o seeds del repo
- `[PARTIAL]` no existe evidencia en esta auditoria de que todos los modelos fiscalmente relevantes para una operacion real esten poblados con datos productivos en una DB vacia

Modelos explicitamente contemplados por arquitectura y tablas:

- `[IMPLEMENTED]` `Modelo 303` si se carga en `aeat_modelo` y sus tablas relacionadas
- `[IMPLEMENTED]` `Modelo 347` si se carga en `aeat_modelo` y sus tablas relacionadas
- `[IMPLEMENTED]` `Modelo 190` si se carga en `aeat_modelo` y sus tablas relacionadas
- `[PARTIAL]` la presencia de la infraestructura no implica que el modelo este poblado en una instalacion nueva sin seeds o sync especifico

### RGPD / GDPR / LOPDGDD

- `[IMPLEMENTED]` ADR y documentacion de DPIA/GDPR en `docs/adr/`
- `[IMPLEMENTED]` principios de minimizacion y no exposicion de secretos en `AGENTS.md` y `docs/environment-variables.md`
- `[IMPLEMENTED]` proteccion de `/mcp` y API key obligatoria fuera de test
- `[PARTIAL]` no se verifica en esta auditoria un inventario de tratamientos, base juridica, retention policy ni procedimiento DSAR operativo extremo a extremo

### SEPBLAC / PBC-FT

- `[IMPLEMENTED]` worker `sepblac.py`
- `[IMPLEMENTED]` modelos y migraciones de Ley 10/2010 / PBC-FT en Alembic
- `[PARTIAL]` el corpus y tablas existen, pero la completitud real de sujetos obligados, alertas, SAR/MAR y procedimientos depende de carga de datos productiva y reglas operativas del cliente

### CNMV / MiFID / MAR / DORA / PRIIPs / Transparencia

- `[IMPLEMENTED]` tablas y migraciones sectoriales en Alembic
- `[IMPLEMENTED]` worker `cnmv.py` con versionado y enlaces regulatorios/obligacionales
- `[PARTIAL]` la estructura regulatoria existe, pero una DB vacia no queda plenamente poblada solo con migraciones; necesita seeds y/o ejecuciones reales de ingestion

### ISO 27001

- `[PARTIAL]` existen controles tecnicos alineables: segregacion de runtime/tooling, secrets fuera del repo, hardening de contenedores, backups documentados, logs y runbooks
- `[TARGET]` no existe certificacion ISO 27001 ni un SGSI completo dentro del repo

## Controles tecnicos verificados en esta auditoria

### Seguridad de runtime

- `[IMPLEMENTED]` `ESDATA_API_KEY` obligatoria fuera de `APP_ENV=test`
- `[IMPLEMENTED]` `MCP_API_KEY` obligatoria fuera de `APP_ENV=test`
- `[IMPLEMENTED]` `CORSMiddleware` con lista explicita; `*` prohibido
- `[IMPLEMENTED]` middleware de rate limiting, request logging y security headers
- `[IMPLEMENTED]` `/mcp` exige handshake y API key

### Despliegue

- `[IMPLEMENTED]` despliegue de referencia por Docker Compose
- `[IMPLEMENTED]` Postgres con volumen persistente
- `[IMPLEMENTED]` contenedores `api` y `web` en modo `read_only` con `tmpfs`
- `[IMPLEMENTED]` `ops` separado para Alembic y verificacion de esquema
- `[PARTIAL]` los cron containers existen, pero el scheduler corporativo final y las URLs reales `HC_PING_URL_CRON_*` siguen fuera del repo

### Integridad y trazabilidad

- `[IMPLEMENTED]` `sync_log` como contrato operativo de workers
- `[IMPLEMENTED]` `source_revision` para change detection incremental
- `[IMPLEMENTED]` versionado CNMV y tablas auxiliares de relacion regulatoria
- `[PARTIAL]` el 100% de tablas pobladas no esta garantizado automaticamente tras bootstrap limpio

## Gaps que no deben venderse como cerrados

- `[PARTIAL]` una instalacion nueva con solo `alembic upgrade head` deja el esquema creado, pero no el corpus completo cargado
- `[PARTIAL]` la DB temporal auditada quedo con pocas tablas pobladas tras migracion limpia; eso confirma que el bootstrap estructural no equivale a dataset productivo
- `[PARTIAL]` la validacion API en contenedor tuvo salida opaca en esta interfaz; no hay evidencia textual final tan fuerte como en workers
- `[TARGET]` certificaciones formales o cumplimiento legal integral del cliente final

## Roadmap minimo de cierre para handoff legal-tecnico

1. Cargar `infra/deploy/.env.prod` real fuera del repo.
2. Ejecutar `alembic upgrade head` y `verify_schema.py`.
3. Ejecutar seeds y/o workers necesarios para poblar corpus minimo operativo.
4. Verificar `/v1/legislacion/cobertura`, `/v1/modelos`, `/health`, `/status`, `/mcp`.
5. Confirmar con Legal/Compliance del cliente:
   - base juridica de tratamiento
   - retention policy
   - responsables de revision humana
   - alcance exacto de modelos AEAT exigidos
   - alcance CNMV/SEPBLAC exigido para la entidad operada

## Declaracion final de esta auditoria

- `[IMPLEMENTED]` plataforma tecnicamente transferible y desplegable
- `[PARTIAL]` cumplimiento material dependiente de datos productivos, secretos reales y configuracion del entorno
- `[TARGET]` declaracion de cumplimiento legal integral del cliente final
