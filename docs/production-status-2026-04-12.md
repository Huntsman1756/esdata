# Estado operativo a 2026-04-12

## Resumen

- Produccion Railway operativa en `https://esdata-production.up.railway.app`.
- BOE, DGT y TEAC activos en produccion.
- `main` alineada con los fixes TEAC mergeados hoy.
- La tanda de linking TEAC guiada por datos reales de produccion queda cerrada.

## Lo hecho en esta sesion

### GitHub / ramas / PRs

- Se detecto que la branch `feat/teac-recargo-linking` ya estaba pusheada y su PR ya existia.
- Se verifico y mergeo la PR `#17`.
- Se abrieron, revisaron y mergearon estas PRs adicionales en `main`:
  - `#18` `feat(teac): recognize explicit art. <numero> <NORMA> references`
  - `#19` `feat(teac): resolve 'Ley del IVA' references as explicit LIVA links`
  - `#20` `fix(teac): upgrade existing doctrine links when confidence improves`
- `main` quedo actualizada hasta `50d8168` tras el merge de `#20`.

### Railway / produccion

- Se verifico acceso operativo a Railway desde CLI.
- Se consulto la base de datos de produccion usando `DATABASE_PUBLIC_URL` del servicio `Postgres`.
- Se confirmo que `worker-teac` desplego y corrio despues de los merges relevantes.
- Se uso `/status` y consultas SQL directas para validar resultados reales en produccion.

### Linking TEAC guiado por produccion

Se partio de casos reales con `confianza_enlace < 1.0` y se hizo una tanda de slices pequenos:

1. PR `#18`
   - Patron explicito `art. <numero> <NORMA>`.
   - Caso objetivo real: `00/05861/2025/00/00 -> LGT 111`.

2. PR `#19`
   - Alias `Ley del IVA -> LIVA` para matching explicito.
   - Casos objetivo reales: `00/01454/2023/00/00 -> LIVA 8` y `LIVA 104`.

3. PR `#20`
   - Fix de produccion: `ON CONFLICT DO NOTHING` impedia upgrades de `0.85 -> 1.0`.
   - Cambio aplicado: `DO UPDATE ... WHERE EXCLUDED.confianza_enlace > documento_articulo.confianza_enlace`.
   - Esto desbloqueo la mejora de enlaces ya persistidos cuando aparece un matcher mejor.

## Verificacion final en produccion

Tras desplegar `worker-teac` con los cambios y ejecutar una nueva corrida, se verifico en produccion:

| Referencia | Norma | Articulo | Confianza |
| --- | --- | --- | --- |
| `00/01454/2023/00/00` | `LIVA` | `104` | `1.00` |
| `00/01454/2023/00/00` | `LIVA` | `8` | `1.00` |
| `00/05861/2025/00/00` | `LGT` | `111` | `1.00` |

Estado: `3/3` casos reales corregidos y confirmados en produccion.

## Diagnostico relevante que no olvidar

- El problema no era solo anadir nuevos patrones.
- El bug real de produccion estaba en la persistencia del linking:
  - antes: `ON CONFLICT DO NOTHING`
  - efecto: un enlace ya insertado a `0.85` nunca podia subir a `1.0`
  - despues: update condicionado cuando la nueva confianza es mayor
- Aprendizaje: cualquier mejora futura de matching debe comprobar tambien si la ruta de upgrade de enlaces existentes sigue funcionando.

## Estado actual verificado

### API / workers

- `GET /status` responde `api=ok`.
- `worker-boe`: operativo.
- `worker-dgt`: operativo.
- `worker-teac`: operativo.
- `cron-boe-daily`: sigue figurando creado pero no era el foco de esta sesion.
- `cron-dgt-weekly`: sigue `never_run`.
- `cron-teac-weekly`: sigue `never_run`.

### Direccion del producto

- `legalize-es` se reviso como corpus/versionado de legislacion: complementario, no sustituto de `esdata`.
- `boletinclaro.es` se reviso como inspiracion de packaging/producto: util para ideas futuras, pero no prioritario ahora.
- Decisiones tomadas:
  - no mover el foco a producto todavia
  - priorizar fiabilidad operativa y precision de linking real

## Lo pendiente para la proxima sesion

### Operativo inmediato

1. Vigilar la primera ejecucion real de `cron-teac-weekly`.
2. Vigilar la primera ejecucion real de `cron-dgt-weekly`.
3. Confirmar via `/status` y, si hace falta, via consultas SQL que esas corridas no introducen regresiones.

### Proximo ciclo de mejora TEAC/DGT

1. Consultar en produccion nuevos casos con `confianza_enlace < 1.0`.
2. Agruparlos por patron real.
3. Elegir un solo slice pequeno.
4. Implementar matcher/fix minimo.
5. Verificar el resultado en produccion.

### Decision de producto (solo despues de lo anterior)

- Revisar si tiene sentido abrir la primera capa de producto ligera sobre `esdata`, probablemente una de estas:
  - alertas tematicas fiscales
  - resumen accionable por cambio normativo o doctrina nueva
  - herramienta gratuita simple sobre el motor fiscal

## Consultas utiles para la proxima sesion

### Casos TEAC con confianza menor de 1.0

```sql
SELECT di.referencia, di.fecha, n.codigo, a.numero, da.confianza_enlace, da.metodo_enlace, da.nota
FROM documento_articulo da
JOIN documento_interpretativo di ON di.id = da.documento_id
JOIN articulo a ON a.id = da.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE di.organismo_emisor = 'TEAC' AND da.confianza_enlace < 1.0
ORDER BY da.confianza_enlace ASC, di.fecha DESC;
```

### Casos DGT con confianza menor de 1.0

```sql
SELECT di.referencia, di.fecha, n.codigo, a.numero, da.confianza_enlace, da.metodo_enlace, da.nota
FROM documento_articulo da
JOIN documento_interpretativo di ON di.id = da.documento_id
JOIN articulo a ON a.id = da.articulo_id
JOIN norma n ON n.id = a.norma_id
WHERE di.organismo_emisor = 'DGT' AND da.confianza_enlace < 1.0
ORDER BY da.confianza_enlace ASC, di.fecha DESC;
```

## Notas practicas

- Los siguientes archivos locales siguen sin trackear y no forman parte de esta tanda:
  - `apps/workers/tests/fixtures/V1923-24.html`
  - `apps/workers/tests/fixtures/V2274-22.html`
  - `dgt_cookies.txt`
  - `tmp_fetch_dgt.py`
- Si aparece un nuevo caso real con `0.85`, repetir exactamente el mismo patron de trabajo:
  - producir muestra real
  - agrupar
  - escoger un solo patron
  - slice pequeno
  - deploy
  - verificacion SQL en produccion
