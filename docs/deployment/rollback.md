# Rollback

## Objetivo

Definir un rollback operativo simple mientras el proyecto no tenga un sistema de migraciones formal.

## Aplicación

1. revertir a la imagen o revision estable anterior de API, web o workers
2. verificar healthchecks
3. revisar `sync_log`
4. revisar logs del servicio afectado

## Base de datos

Con Alembic ya introducido, cualquier cambio de schema debe ir acompañado de:

1. backup previo
2. validacion en entorno controlado
3. plan especifico de vuelta atras

## Recomendacion

No aplicar cambios de schema en produccion sin backup validado ni sin pasos de rollback documentados para esa entrega concreta.
