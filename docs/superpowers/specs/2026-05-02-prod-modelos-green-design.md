# Produccion Modelos Green Design

## Objetivo

Llevar a verde verificable el worker productivo de modelos AEAT corrigiendo los errores reales que siguen ensuciando `sync_log`, validar el runtime afectado y desplegar el fix al VPS con revalidacion operativa fresca.

## Alcance aprobado

Incluye:

- corregir en `apps/workers/aeat_models.py` la normalizacion de `url_info` antes de descargar detalle
- evitar que recursos externos no oficiales del detalle AEAT se traten como errores operativos del worker
- mantener trazabilidad en `sync_log` y verificar que el siguiente run productivo de `worker-modelos` cierre las alertas activas
- validar tests/lint del scope afectado y ejecutar deploy Compose al VPS

No incluye:

- rediseno general del sistema de alertas
- hardening general del host fuera de `esdata`
- resolver suites historicamente rotas fuera del scope `modelos`

## Root Cause

La investigacion apunta al worker activo `apps/workers/aeat_models.py`, no al worker legacy `modelos.py`.

Problemas concretos:

1. `url_info` puede quedar persistida como `ttps://...` y el worker no la normaliza antes de `fetch_detail()`.
2. `_extract_model_resources()` recoge enlaces externos desde paginas AEAT y el loop de sync los descarga como si fueran recursos oficiales; cuando fallan, incrementan `stats["errores"]`.
3. La regla `WorkerSyncErrors` alerta sobre el ultimo `errors > 0` de `sync_log`, asi que cualquier run parcial reciente deja el entorno en rojo.

## Enfoque recomendado

Aplicar un fix minimo y defensivo en dos capas:

- normalizar siempre `url_info` al entrar en `_fetch_model_metadata()`
- filtrar recursos descargables a una allowlist de hosts oficiales (`sede.agenciatributaria.gob.es`, `www1.agenciatributaria.gob.es`, `www.boe.es`) y volver a comprobarlo en `run_sync()` antes de descargar

Con eso, el siguiente run productivo debe registrar `errors = 0` salvo fallo real de recurso oficial.

## Verificacion

- tests dirigidos de `apps/workers/tests/test_aeat_models.py`
- lint de `apps/workers`
- si no rompe contrato, smoke de API relacionado con modelos
- deploy Compose al VPS y revalidacion de `sync_log`, alertas, `health`, `status` y `modelo 303`
