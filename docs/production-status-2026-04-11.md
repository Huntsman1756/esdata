# Estado operativo a 2026-04-11

## Resumen

- Produccion Railway operativa en `https://esdata-production.up.railway.app`.
- BOE activo en produccion.
- DGT activa en produccion.
- TEAC activa en produccion con ingesta real desde DYCTEA.
- El repo local contiene dos commits adicionales que aun no estan en `origin/main` ni en PR mergeada.

## Lo que se ha hecho hasta ahora

### BOE

- Ingesta real de articulos para `LGT`, `LIRPF`, `LIS` y `LIVA`.
- Full-text en produccion con `search_vector`, `ts_rank` y `ts_headline`.
- Auto-linking de materias y de doctrina a articulos.

### DGT

- Worker DGT operativo en Railway.
- Scraping real desde Petete con sesion/AJAX.
- `DGT_SSL_VERIFY` configurable para entornos donde Petete falle por SSL.
- Enlazado de doctrina a articulos y exposicion en `/v1/doctrina`.

### TEAC

- Topologia TEAC anadida en codigo y Railway: `worker-teac` y `cron-teac-weekly`.
- Worker corregido para usar `TEAC_SEED_URLS` por variable de entorno en lugar de `seed_urls=[]`.
- Parser corregido para soportar markup real de DYCTEA, no solo el fixture HTML.
- Enlazado compartido corregido para reconocer referencias explicitas reales tipo `articulo 89.Cinco b) de la Ley 37/1992`.
- Produccion validada con resultados TEAC reales y con un caso enlazado a `LIVA 89` con confianza `1.0`.

## Estado actual verificado

### GitHub

- Branch actual local: `feat/teac-recargo-linking`.
- Estado local frente a remoto de la branch: `ahead 2`.
- `origin/main` no incluye aun los dos ultimos commits locales.
- Ultimos commits locales pendientes de subir/mergear:
  - `56cb437` `feat(teac): make TEAC worker functional in production`
  - `0fce990` `fix(teac): link live law references with subarticle suffixes`
- Ultima PR TEAC mergeada en GitHub: `#16`.

### Railway

- Proyecto: `supportive-warmth`.
- API publica: `https://esdata-production.up.railway.app`.
- Servicios operativos verificados:
  - `esdata`
  - `worker-boe`
  - `worker-dgt`
  - `worker-teac`
  - `cron-boe-daily`
  - `cron-dgt-weekly`
  - `cron-teac-weekly`
  - `Postgres`
- Variables verificadas en TEAC:
  - `DATABASE_URL`
  - `WORKER_CMD`
  - `APP_ENV`
  - `LOG_LEVEL`
  - `WORKER_RETRY_MAX`
  - `TEAC_SEED_URLS`

### Snapshot de produccion

Estado observado en `/status`:

- `worker-boe`
  - `status=ok`
  - `bloques_processed=1008`
  - `articulos_upserted=1008`
- `worker-dgt`
  - `status=ok`
  - `documentos_processed=10`
  - `documentos_upserted=10`
  - `doctrina_links_created=18`
- `worker-teac`
  - `status=ok`
  - `documentos_processed=4`
  - `documentos_upserted=4`
  - `doctrina_links_created=25`
- `cron-boe-daily`
  - aparece creado
- `cron-dgt-weekly`
  - `never_run`
- `cron-teac-weekly`
  - `never_run`

## Evidencia funcional verificada

- `GET /status` responde `api=ok` y muestra los workers con metricas reales.
- `GET /v1/doctrina/buscar?q=iva&organismo_emisor=TEAC` devuelve resultados reales.
- `GET /v1/doctrina/00/01362/2024/00/00` devuelve:
  - `articulos_relacionados = [{"norma":"LIVA","numero":"89","metodo_enlace":"auto_link","confianza_enlace":1.0}]`

## Lo que falta por hacer

### GitHub

- Subir la branch actual con los dos commits locales pendientes.
- Abrir PR para:
  - `56cb437` `feat(teac): make TEAC worker functional in production`
  - `0fce990` `fix(teac): link live law references with subarticle suffixes`
- Mergear esos cambios en `main` para que GitHub refleje la realidad de produccion.

### Operativo / producto

- Revisar mas resoluciones TEAC reales para detectar patrones que aun quedan con `nivel_enlace=0.0` o `0.85` mejorable.
- Ampliar `TEAC_SEED_URLS` con una muestra mas robusta o sustituirlo por descubrimiento automatizado desde `DYCTEA/Criterios.aspx`.
- Verificar la primera ejecucion real de `cron-teac-weekly` tras su ventana programada.
- Verificar la primera ejecucion real de `cron-dgt-weekly` tras su ventana programada.

## Proximos pasos recomendados

1. `git push` de la branch actual.
2. Crear una PR pequena con los dos commits locales pendientes.
3. Tras merge, confirmar que GitHub Actions redeploya sin drift respecto al deploy manual ya aplicado en Railway.
4. Hacer otro slice pequeno de mejora de enlazado TEAC en vivo, guiado por resultados reales con confianza baja.

## Notas importantes

- La produccion actual ya incorpora cambios que aun no estan en `origin/main`.
- Esto significa que Railway esta actualizado operativamente, pero GitHub `main` no refleja todavia por completo el estado desplegado.
- Los siguientes archivos no forman parte del trabajo TEAC y siguen sin commitear:
  - `apps/workers/tests/fixtures/V1923-24.html`
  - `apps/workers/tests/fixtures/V2274-22.html`
  - `dgt_cookies.txt`
  - `tmp_fetch_dgt.py`
