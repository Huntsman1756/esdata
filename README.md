# esdata

Infraestructura fiscal espanola para consultar norma vigente, doctrina y modelos AEAT con trazabilidad hasta el articulo aplicable. Incluye API y workers de ingesta, versionado por articulo, busqueda full-text y superficies pensadas para consumo por aplicaciones y agentes.

## Estado actual

- Produccion operativa en Railway.
- API publica en `https://esdata-production.up.railway.app`.
- Frontend publico en `https://web-production-ecb5.up.railway.app`.
- Ingesta BOE con soporte de codigo y configuracion para `LGT`, `LIRPF`, `LIS`, `LIVA`, `ITPAJD`, `IRNR`, `IIEE`, `HL`, `DAC6` y `DAC6RD`, con `DAC6EU` registrada como referencia UE desde `EUR-Lex`.
- Doctrina DGT activa para consultas objetivo de `LIVA` y `LIS`, con enlazado a articulos via `documento_articulo`.
- Doctrina TEAC activa en produccion con ingesta real desde DYCTEA y enlazado a articulos via `documento_articulo`.
- Cadena norma -> doctrina -> modelo AEAT disponible con relaciones verificables y fuente oficial por enlace.
- Busqueda full-text activa en produccion con `ts_rank`, `ts_headline` y fragmentos con `<mark>`.

## Cobertura y foco

- Cobertura normativa actual verificada en el repo: `LGT`, `LIRPF`, `LIS`, `LIVA`, `ITPAJD`, `IRNR`, `IIEE`, `HL`, `DAC6`, `DAC6RD` y `DAC6EU`.
- Cobertura doctrinal actual: DGT y TEAC con enlazado a articulos via `documento_articulo`.
- Cobertura documental adicional: `BDNS` con convocatorias públicas de subvenciones almacenadas como fuente documental específica.
- Cobertura regulatoria documental inicial: `CNMV` con circulares y documentos de reporting/indexación operativa.
- Cobertura regulatoria documental inicial: `SEPBLAC` con formularios y documentación operativa PBC/FT.
- Cobertura societaria inicial: `BORME` con actos societarios públicos almacenados como fuente documental mercantil.
- Base inicial de entidades: `empresa` y `documento_empresa` para empezar a cruzar fuentes públicas alrededor de una sociedad.
- Capa de cumplimiento y presentacion: modelos AEAT con relaciones verificadas a articulos concretos.
- Foco del producto: ofrecer criterio fiscal trazable para trabajo real de despachos, productos y agentes.
- Normas y marcos tambien relevantes para una herramienta de gestion fiscal, pero fuera de cobertura actual:
  - `UNE 19602`
- `PLACE`

Planificación permanente relacionada:

- `docs/regulatory-compliance-expansion-plan.md`: plan maestro para la siguiente expansión regulatoria (`CNMV`, `SEPBLAC`, `BOE`, `UE`) orientada a compliance operativo.
  Incluye también la tabla maestra de canonización del corpus para cerrar la Fase 0.

## Modelos AEAT registrados

- **IRPF** (13 modelos): `100`, `111`, `115`, `123`, `130`, `180`, `187`, `189`, `190`, `193`, `194`, `196`, `198`
- **IVA** (3 modelos): `303`, `349`, `390`
- **IRNR** (3 modelos): `124`, `216`, `296`
- **CENSAL** (1 modelo): `036`
- **INFORMATIVO** (3 modelos): `289` (DAC2/CRS), `290` (FATCA), `347`
- **FORMATO** (1 modelo): `299` (diseño registro electrónico)
- **HISTÓRICO** (1 modelo): `110` (obsoleto → `111`)

> Total: 25 modelos. Los modelos IRNR `124`, `216` y `296` ya quedan enlazados a articulos de `IRNR` (RDL 5/2004) en seeds y tests del repo.

### Contenido por modelo (v2)

Cada modelo tiene, desde la campaña 2025:

| Contenido | Descripción | Endpoint |
|---|---|---|
| **Instrucciones** | Paso a paso para rellenar (características, quién debe, cómo, plazo) | `GET /v1/modelos/{codigo}` → `instrucciones` |
| **Casillas** | Inventario completo de todas las casillas (código, etiqueta, descripción, tipo) | `GET /v1/modelos/{codigo}/casillas` |
| **Claves** | Códigos de rendimiento, régimen, etc. | `GET /v1/modelos/{codigo}/claves` |
| **Normativa** | Órdenes BOE que regulan cada modelo | `GET /v1/modelos/{codigo}/normativa` |
| **Artículos** | Relación con legislación (LIVA, LIRPF, LIS, LGT) | `GET /v1/modelos/{codigo}/articulos` |
| **Doctrina** | Documentos DGT/TEAC que citan los artículos del modelo | `GET /v1/modelos/{codigo}` → `doctrina_relacionada` |

### Versionado

Los modelos soportan múltiples campañas (2024, 2025, etc.). Para ver una campaña específica:

```
GET /v1/modelos/303?campana=2024
GET /v1/modelos/303/casillas?campana=2024
```

Para añadir o quitar casillas en una nueva campaña, se actualiza `modelo_campana` y `modelo_casilla` con `activo=true/false`.

## Servicios desplegados

- `esdata`: API FastAPI publica.
- `worker-boe`: worker continuo que ingiere articulos desde BOE.
- `cron-boe-daily`: ejecucion diaria `python boe.py --run-once`.
- `worker-dgt`: worker continuo que sincroniza doctrina DGT y ejecuta auto-linking a articulos.
- `cron-dgt-weekly`: ejecucion semanal `python dgt.py --run-once`.
- `worker-teac`: worker continuo que sincroniza doctrina TEAC desde DYCTEA y ejecuta auto-linking a articulos.
- `cron-teac-weekly`: ejecucion semanal `python teac.py --run-once`.
- `worker-modelos`: worker continuo que escanea la sede AEAT para actualizar instrucciones, casillas, claves y detectar nuevas campañas.
- `cron-modelos-daily`: ejecucion diaria `python modelos.py --run-once` a las 05:00.
- `web`: Frontend Next.js 15 con buscador fiscal, resultados y detalle de doctrina (Fase 1).
- `Postgres`: base de datos principal.

## Superficies publicas

- Frontend: `https://web-production-ecb5.up.railway.app`
- API: `https://esdata-production.up.railway.app`
- OpenAPI completa: `https://esdata-production.up.railway.app/openapi.json`

Rutas frontend utiles:

- `GET /`
- `GET /buscar?q=iva&tab=legislacion`
- `GET /doctrina/00/01454/2023/00/00`
- `GET /articulo/LIVA/104`
- `GET /modelo/100`

## Estructura real del repo

- `apps/api`: API FastAPI.
- `apps/api/schemas.py`: modelos Pydantic para respuestas tipadas y OpenAPI.
- `apps/api/routers`: endpoints HTTP (`status`, `buscar`, `legislacion`, `materias`, `doctrina`).
- `apps/api/services/search.py`: logica de busqueda full-text.
- `apps/api/mcp_server.py`: monta MCP sobre la API.
- `apps/api/db.py`: conexion SQLAlchemy.
- `apps/workers/boe.py`: ingesta BOE, bootstrap de esquema y auto-linking.
- `apps/workers/dgt.py`: scraping DGT via sesion/AJAX, persistencia y relinking de doctrina.
- `apps/workers/teac.py`: scraping TEAC via DYCTEA, persistencia y relinking de doctrina.
- `apps/workers/cnmv.py`: ingesta documental inicial de CNMV desde referencias públicas canonizadas.
- `apps/workers/sepblac.py`: ingesta documental inicial de SEPBLAC con soporte HTML/PDF para operativa PBC/FT.
- `apps/workers/modelos.py`: orquestación del sync AEAT por modelo.
- `apps/workers/modelos_support.py`: scraping, campañas y persistencia del dominio de modelos AEAT.
- `apps/workers/tests/test_boe.py`: tests del worker.
- `apps/workers/tests/test_dgt.py`: tests del worker DGT.
- `apps/workers/tests/test_teac.py`: tests del worker TEAC.
- `apps/workers/tests/test_modelos.py`: tests del worker de modelos AEAT.
- `apps/web`: frontend Next.js 15 con home, busqueda, detalle de doctrina, detalle de articulo y detalle de modelo AEAT.
- `apps/api/routers/modelos.py`: endpoints `/v1/modelos` para la capa de modelos AEAT.
- `apps/api/routers/cnmv.py`: endpoints `/v1/cnmv` para la capa documental regulatoria CNMV.
- `apps/api/routers/sepblac.py`: endpoints `/v1/sepblac` para la capa documental operativa SEPBLAC.
- `apps/api/services/modelos.py`: consultas reutilizables para detalle, campañas y relaciones de modelos.
- `scripts/seed-modelos.py`: seed idempotente de metadata y relaciones `modelo_articulo` con fuente verificable.
- `scripts/seed-modelos-v2.py`: seed idempotente de campañas, instrucciones, casillas, claves y normativa AEAT.
- `scripts/export-gpt-openapi.py`: genera specs OpenAPI reducidas para GPT Actions.
- `infra/sql/init.sql`: esquema base.
- `infra/sql/003_modelos_aeat.sql`: tablas `aeat_modelo` y `modelo_articulo`.
- `infra/sql/004_modelos_v2.sql`: versionado por campaña, casillas, claves, instrucciones y normativa.
- `infra/sql/docker-init.sql`: bootstrap local secuencial para Postgres en Docker.
- `infra/sql/002_fulltext_search.sql`: migracion de `search_vector`, indices y trigger.
- `railway.toml`: configuracion monorepo para Railway.

## Endpoints principales

- `GET /health`
- `GET /status`
- `GET /v1/buscar`
- `GET /v1/legislacion/buscar`
- `GET /v1/legislacion`
- `GET /v1/legislacion/cobertura`
- `GET /v1/legislacion/{codigo}`
- `GET /v1/legislacion/{codigo}/articulos`
- `GET /v1/legislacion/{codigo}/articulos/{numero}`
- `GET /v1/legislacion/{codigo}/articulos/{numero}/historial`
- `GET /v1/materias`
- `GET /v1/materias/{slug}`
- `GET /v1/doctrina/buscar`
- `GET /v1/doctrina/{referencia}`
- `GET /v1/modelos`
- `GET /v1/modelos/{codigo}`
- `GET /v1/modelos/{codigo}/articulos`
- `GET /v1/modelos/{codigo}/casillas`
- `GET /v1/modelos/{codigo}/claves`
- `GET /v1/modelos/{codigo}/instrucciones`
- `GET /v1/modelos/{codigo}/normativa`
- `GET /mcp`

Rutas frontend:

- `GET /`
- `GET /buscar`
- `GET /doctrina/[...referencia]`
- `GET /articulo/[norma]/[numero]`
- `GET /modelo/[codigo]`

## Desarrollo local

API:

```bash
pytest apps/api/tests/test_smoke.py -q
```

Worker:

```bash
pytest apps/workers/tests/test_boe.py -q
pytest apps/workers/tests/test_dgt.py -q
pytest apps/workers/tests/test_teac.py -q
pytest apps/workers/tests/test_modelos.py -q
```

Web:

```bash
npm --prefix apps/web install
npm --prefix apps/web run dev       # http://localhost:3000
npm --prefix apps/web run test
npm --prefix apps/web run build
```

OpenAPI reducida para GPT Actions:

```bash
python scripts/export-gpt-openapi.py --output docs/openapi-gpt.json
python scripts/export-gpt-openapi.py --openapi 3.0.3 --output docs/openapi-gpt-3.0.json
```

## Deploy automatico

- `.github/workflows/deploy.yml`: despliega `esdata`, workers y cron.
- `.github/workflows/deploy-web.yml`: valida y despliega `apps/web` al servicio `web` de Railway.
- `railway.toml`: define la topologia monorepo de servicios.

## Produccion

### Variables importantes

- `DATABASE_URL=postgresql+psycopg://...`
- `BOE_API_BASE=https://www.boe.es/datosabiertos/api/legislacion-consolidada`
- `APP_ENV=production`
- `BOE_LEGISLACION_NORMAS=LIVA,LIS,LIRPF,LGT,ITPAJD,IRNR,IIEE,HL,DAC6,DAC6RD,DAC6EU`
- `BDNS_SEED_URLS=https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/.../document/...`
- `BORME_SEED_URLS=https://www.boe.es/borme/dias/.../pdfs/BORME-A-....pdf`
- `MODELOS_SYNC_INTERVAL=86400` para `worker-modelos` si se quiere ajustar la cadencia del loop continuo.
- `DGT_SSL_VERIFY=false` para el worker DGT si Petete falla por SSL en produccion.
- `TEAC_SEED_URLS=https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/criterio.aspx?id=...,...` para el worker TEAC.
- `SYNC_INTERVAL_SECONDS=604800` para `worker-dgt` si se quiere ajustar la cadencia del loop continuo.
- `ESDATA_API_BASE_URL=https://esdata-production.up.railway.app` en el servicio `web` para que Next.js consulte la API publica en server-side.
- Para bootstrap SQL y seeds en Railway, usar `docs/deploy-commands.md` o `DEPLOY_CHECKLIST.md`.

### GPT Actions

- Spec completa servida por la API: `https://esdata-production.up.railway.app/openapi.json`
- Spec reducida para GPT: `docs/openapi-gpt.json`
- Fallback OpenAPI 3.0.x para el builder: `docs/openapi-gpt-3.0.json`
- Flujo operativo de deploy + bootstrap SQL: `docs/deploy-commands.md`

### Verificaciones utiles

- Health API: `https://esdata-production.up.railway.app/health`
- Estado agregado: `https://esdata-production.up.railway.app/status`
- Frontend home: `https://web-production-ecb5.up.railway.app`
- Frontend busqueda: `https://web-production-ecb5.up.railway.app/buscar?q=iva&tab=legislacion`
- Frontend detalle doctrina: `https://web-production-ecb5.up.railway.app/doctrina/00/01454/2023/00/00`
- Frontend detalle articulo: `https://web-production-ecb5.up.railway.app/articulo/LIVA/104`
- Frontend detalle modelo: `https://web-production-ecb5.up.railway.app/modelo/100`
- Doctrina DGT: `https://esdata-production.up.railway.app/v1/doctrina/buscar?q=iva&organismo_emisor=DGT`
- Doctrina TEAC: `https://esdata-production.up.railway.app/v1/doctrina/buscar?q=iva&organismo_emisor=TEAC`
- Modelos AEAT: `https://esdata-production.up.railway.app/v1/modelos`
- Detalle TEAC enlazado: `https://esdata-production.up.railway.app/v1/doctrina/00/01362/2024/00/00`
- Normas: `https://esdata-production.up.railway.app/v1/legislacion`
- Cobertura: `https://esdata-production.up.railway.app/v1/legislacion/cobertura`
- Busqueda: `https://esdata-production.up.railway.app/v1/legislacion/buscar?q=tipo+reducido&norma=LIVA`

### Verificacion full-text

La migracion `infra/sql/002_fulltext_search.sql` ya fue aplicada en produccion. Para revalidarla:

```sql
SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector,
       COUNT(*) AS total
FROM version_articulo;
```

`con_vector` debe coincidir con `total`.

## Documentacion adicional

- `DEPLOY_CHECKLIST.md`: pasos de despliegue y smoke tests.
- `docs/deploy-commands.md`: secuencia exacta de deploy en Railway, SQL y smoke tests.
- `STRUCTURE.md`: mapa actualizado del repo.
- `docs/production-status-2026-04-11.md`: estado operativo real, verificacion y siguientes pasos.
- `docs/postmortem-sprint-2.md`: incidencias, diagnostico y resolucion del sprint.
