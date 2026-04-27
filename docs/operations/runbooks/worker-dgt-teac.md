# Runbook: worker-dgt y worker-teac

## Función

Sincronizan doctrina interpretativa y enlazan documentos con articulos.

## Variables clave

### DGT

- `DATABASE_URL`
- `DGT_SSL_VERIFY`
- `SYNC_INTERVAL_SECONDS`

### TEAC

- `DATABASE_URL`
- `TEAC_SEED_URLS`
- `SYNC_INTERVAL_SECONDS`

## Síntomas típicos

1. no aparecen nuevos documentos doctrinales
2. baja calidad de enlaces en `documento_articulo`
3. `cron-dgt-weekly` o `cron-teac-weekly` no generan actividad en `sync_log`

## Comprobaciones

1. revisar logs de worker y cron
2. validar conectividad a Petete o URLs TEAC
3. ejecutar manualmente:
   - `python apps/workers/dgt.py --run-once`
   - `python apps/workers/teac.py --run-once`
4. validar con:
   - `python scripts/maintenance/validate-cron-run.py --db-url ...`

## Recuperación básica

1. verificar variables y seeds
2. revisar cambios en HTML de origen
3. aislar si el fallo es de scraping o de enlace doctrinal
