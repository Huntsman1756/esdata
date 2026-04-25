# External Dependencies

## Objetivo

Registrar las dependencias externas que pueden degradar `esdata` aunque la infraestructura propia este sana.

## Fuentes principales

- BOE
- DGT
- TEAC
- AEAT
- otras fuentes regulatorias o documentales adicionales segun workers activos

## Riesgos esperables

- cambio de HTML o estructura de pagina
- timeouts
- SSL anomalo
- bloqueos o rate limit externo
- documentos incompletos o inconsistentes

## Regla operativa

Una caida o cambio de una fuente externa debe tratarse como degradacion parcial del sistema, no como fallo total de toda la plataforma salvo evidencia contraria.

## Que vigilar

- ultimo ciclo correcto por worker
- ultimo error por worker
- si entran nuevos documentos o el volumen se queda congelado

## Respuesta minima

1. revisar logs del worker afectado
2. comprobar disponibilidad manual de la fuente
3. confirmar si el problema es de red, HTML o datos
4. documentar si la degradacion afecta solo a una fuente concreta
