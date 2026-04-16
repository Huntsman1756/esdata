# Runbook: worker-boe

## Función

Sincroniza legislacion consolidada desde BOE y actualiza `norma`, `articulo`, `version_articulo` y enlaces auxiliares.

## Variables clave

- `DATABASE_URL`
- `BOE_API_BASE`
- `BOE_LEGISLACION_NORMAS`
- `SYNC_INTERVAL_SECONDS`

## Síntomas típicos

1. no aparecen nuevas normas o articulos
2. `/status` marca `worker-boe` o `cron-boe-daily` como `stale`
3. errores HTTP contra BOE

## Comprobaciones

1. revisar logs del worker
2. validar conectividad a `BOE_API_BASE`
3. ejecutar una corrida puntual:
   - `python apps/workers/boe.py --run-once`
4. comprobar `sync_log`

## Recuperación básica

1. verificar variables
2. relanzar el worker
3. si el problema es parcial, usar `BOE_ONLY_BLOCK_IDS` para aislar
