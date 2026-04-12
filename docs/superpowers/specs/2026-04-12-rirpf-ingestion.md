# Spec: Ingesta RIRPF (Reglamento IRPF)

## Objetivo

Añadir el Reglamento del IRPF (RIRPF) como nueva norma en el corpus de esdata, usando el mismo pipeline de ingesta BOE que las leyes vigentes.

## Alcance

**Incluye:**
- Ingesta de RIRPF (RD 439/2007) desde BOE
- Código `RIRPF` en `GET /v1/legislacion`
- Búsqueda automática vía `GET /v1/buscar`
- Detalle artículo e historial via `GET /v1/legislacion/RIRPF/articulos/{numero}`
- Mismo worker BOE, sin cambios de código (solo añadir RIRPF a la config)

**No incluye:**
- Sidebars de modelos AEAT para artículos de reglamento
- Linking doctrina → artículo de reglamento (no se fuerza, si funciona naturalmente, bien)
- RIVA, RIS (siguiente tanda)

## Fuente verificable

- **RD 439/2007**, de 30 de marzo, por el que se aprueba el Reglamento del IRPF
- BOE: `BOE-A-2007-7183`
- URL: `https://www.boe.es/buscar/act.php?id=BOE-A-2007-7183`

## Verificación de fuente: BLOQUEADA

Intento de ingesta via API BOE legislación consolidada:
```
GET /id/BOE-A-2007-7183/metadatos → 404 "La información solicitada no existe"
```

Confirmado:
- La API de legislación consolidada del BOE solo expone leyes (LIVA, LIRPF, LIS, LGT)
- **No expone reglamentos** (RIRPF, RIVA, RIS)
- LIVA (BOE-A-1992-28740) → 200 OK
- RIRPF (BOE-A-2007-7183) → 404

## Opciones para desbloquear

1. **Scraping directo del RIRPF** (como hace el worker DGT con Petete)
   - Construir un nuevo worker `rirpf.py` que scrapea el texto consolidado
   - Mayor mantenimiento, pero factible

2. **Ingesta manual**
   - Cargar RIRPF como seed SQL desde un archivo fuente
   - Control total, pero sin actualización automática

3. **Esperar a que BOE exponga reglamentos en su API**
   - Cero trabajo, pero timeline indefinido

**Recomendación:** Opción 2 a corto plazo. Un seed SQL del RIRPF nos da cobertura inmediata sin construir scraping nuevo. Se puede migrar a scraping automático después si BOE no lo expone.

## Verificación en producción

El slice se considera exitoso si:

1. `GET /v1/legislacion` devuelve `RIRPF` en la lista de normas
2. `GET /v1/legislacion/RIRPF/articulos/1` (o cualquier artículo conocido) responde con texto
3. `GET /v1/buscar?q=dietas` o `GET /v1/buscar?q=retenciones` devuelve al menos un artículo de RIRPF

## Riesgos

- **BOE no tiene RIRPF como norma consolidada indexada**: el BOE consolidado no siempre incluye reglamentos con la misma estructura que las leyes. Si el BOE ID no existe o el índice de bloques devuelve 0 resultados, el worker no romperá pero sí quedará con 0 artículos ingeridos.
- **Mitigación**: verificar primero que BOE expone RIRPF en su API de legislación consolidada antes de añadirlo al worker.

## Rollback

Si la ingesta falla o produce datos inconsistentes:
- Quitar `RIRPF` de `BOE_LEGISLACION_NORMAS`
- Redeploy del worker
- Opcionalmente limpiar: `DELETE FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo = 'RIRPF')`

## Criterio de expansión

Si RIRPF funciona limpio:
- Mismo patrón para RIVA (RD 1624/1992, BOE-A-1992-28138)
- Mismo patrón para RIS (RD 634/2004, BOE-A-2004-14662)
