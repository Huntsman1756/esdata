# Runbook: worker-modelos

## Función

Sincroniza campanas, instrucciones, casillas y claves desde sede AEAT.

## Variables clave

- `DATABASE_URL`
- `MODELOS_SYNC_INTERVAL`
- `DGT_SSL_VERIFY`

## Síntomas típicos

1. no aparecen nuevas campanas
2. casillas o instrucciones quedan vacias
3. `/status` marca `worker-modelos` o `cron-modelos-daily` como `stale`

## Comprobaciones

1. revisar logs del worker
2. comprobar conectividad a sede AEAT
3. ejecutar una corrida puntual:
   - `python apps/workers/modelos.py --run-once`
4. validar tablas `modelo_campana`, `modelo_casilla`, `modelo_clave` y `modelo_instruccion`

## Recuperación básica

1. verificar que el modelo existe en `aeat_modelo`
2. revisar si ha cambiado el HTML de sede AEAT
3. relanzar el worker tras ajustar variables o parsing
