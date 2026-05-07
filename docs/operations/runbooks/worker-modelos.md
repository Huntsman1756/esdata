# Runbook: worker-modelos

## Función

Sincroniza campanas, instrucciones, casillas y claves desde sede AEAT.

## Variables clave

- `DATABASE_URL`
- `AEAT_MODELS_SYNC_INTERVAL`
- `MODELOS_SYNC_INTERVAL` como alias usado por Compose
- `WORKER_NAME` para distinguir `worker-modelos` y `cron-modelos-daily`

## Síntomas típicos

1. no aparecen nuevas campanas
2. casillas o instrucciones quedan vacias
3. `/status` marca `worker-modelos` o `cron-modelos-daily` como `stale`

## Comprobaciones

1. revisar logs del worker
2. comprobar conectividad a sede AEAT
3. ejecutar una corrida puntual:
   - `python apps/workers/aeat_models.py --run-once`
4. validar tablas `aeat_modelo`, `modelo_campana`, `modelo_casilla`, `modelo_clave`, `modelo_instruccion` y `modelo_recurso`
5. revisar `sync_log` para diferenciar `worker-modelos` de `cron-modelos-daily`

## Recuperación básica

1. verificar que el modelo existe en `aeat_modelo`
2. revisar si ha cambiado el HTML de sede AEAT
3. si falla un recurso oficial AEAT, el sync debe quedar `partial` con mensaje `Skipped N AEAT official resources after fetch failures`, no `error` fatal
4. relanzar el worker tras ajustar variables o parsing
