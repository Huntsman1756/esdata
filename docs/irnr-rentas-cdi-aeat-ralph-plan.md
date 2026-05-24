# IRNR Rentas, CDI y Siguiente AEAT

Estado: `planned`.

Este bloque arranca despues del cierre de AEAT IRNR `216/296`. No intenta aumentar cobertura por volumen; separa tres historias para desbloquearlas con metodo Ralph, una por iteracion.

## Orden

| historia | objetivo | salida aceptable |
|----------|----------|------------------|
| O-01 | Granularizar `216/296` por tipo de renta IRNR, empezando por dividendos e intereses | Reglas/relaciones persistidas si hay evidencia, o `partial` documentado |
| O-02 | Preparar CDI despues de una renta domestica trazada | Relacion CDI estrecha si hay pais/articulo/fuente, o bloqueo documentado |
| O-03 | Elegir siguiente modelo AEAT limpio | Un candidato defendible para sprint posterior, o ningun candidato si falta evidencia |

## Regla De Producto

`216/296` estan completos como modelos/formularios, pero no como respuesta universal sobre retenciones no residentes. La aplicabilidad sigue condicionada por tipo de renta, residencia, convenio, protocolo, certificado y supuesto exacto.

## Metodo Ralph

Archivos activos:

- `prd.json`
- `scripts/ralph/sprint-o-irnr-rentas-cdi-aeat.md`
- `progress.txt`

Cada iteracion debe:

1. Leer `prd.json`, `progress.txt` y `git log --oneline -20`.
2. Escoger la historia pendiente con menor `priority`.
3. Auditar antes de escribir.
4. Hacer solo esa historia.
5. Validar con tests/comandos focales.
6. Commitek con prefijo `[O-XX]`.
7. Marcar `passes=true` solo si se cumplen todos los criterios.
8. Registrar el resultado en `progress.txt`.

## No Objetivos

- No calcular retenciones.
- No cerrar tipos de renta por similitud textual.
- No usar CDI como fuente de obligacion domestica.
- No tocar MCP salvo que una nueva superficie fiscal requiera exposicion.
- No abrir Modelo 100 por defecto.

## Criterio De Salida Del Sprint

El sprint termina cuando:

- O-01 queda cerrado como persistencia real o `partial` documentado.
- O-02 queda cerrado como relacion CDI estrecha o bloqueo documentado.
- O-03 deja un candidato AEAT siguiente o explica por que no hay candidato limpio.
