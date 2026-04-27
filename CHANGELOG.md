# Changelog

## [sin fecha] - en progreso

### Cambia
- `/status` expone ahora un contrato operativo comun por worker con `rows_processed`, `errors` y `duration_ms`, ademas de los contadores legacy ya existentes.
- CI verifica que la base llegue a `alembic head` antes de ejecutar la bateria principal de Python.

### Anade
- Smoke coverage dedicada para stale detection en `/status` y para invariantes basicos de transporte `/mcp`.
- Contrato aditivo minimo en `sync_log` para distinguir volumen procesado, errores y duracion por ejecucion.

### Pendiente
- Extender el mismo contrato operativo a mas superficies AI/retrieval y a alertas activas fuera del endpoint `/status`.
