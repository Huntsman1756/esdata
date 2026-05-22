# Matriz operativa de cobertura doctrinal DGT/TEAC

Estado: `ACTIVE`

Esta matriz describe el estado operativo de las lineas piloto DGT/TEAC. No sustituye al contrato de producto en `docs/doctrina-coverage-prd.md`; sirve para auditoria diaria de que relacion existe, que falta y por que una linea puede o no responder con `safe_to_answer=true`.

## Regla de lectura

- `complete` significa que la linea cumple fuente oficial, hash/captura, articulo o supuesto, modelo cuando aplica, vigencia explicita, relacion persistida y tests fail-closed.
- `partial` significa que hay evidencia util, pero falta una pieza contractual.
- `target` significa que la linea esta definida como objetivo, pero no tiene base suficiente cargada.
- Una relacion persistida parcial mejora trazabilidad, pero no convierte la linea en respuesta segura.

## Matriz D-01 a D-09

| Linea | Estado | Fuente principal | Relacion persistida | Modelo confirmado | Vigencia explicita | Que falta exactamente |
| --- | --- | --- | --- | --- | --- | --- |
| D-01 Retenciones no residentes | `complete` | DGT `V0166-25` | Si: `TRLIRNR art. 31`, `216/296`, `retenciones_no_residentes`, `complete` | Si: `216/296` | Si: historico a fecha de consulta | No extrapolar fuera del supuesto auditado |
| D-02 IVA intracomunitario | `partial` | DGT `V0236-26` candidata descartada para cierre | No en produccion: contrato preparado para `LIVA art. 25`, `349`, `entrega_intracomunitaria_bienes` | No: `349` bloqueado sin supuesto | No para fuente valida | Nueva fuente oficial realmente intracomunitaria; si no es entrega intracomunitaria, ajustar articulo/modelo antes de cerrar |
| D-03 Operaciones vinculadas | `partial` | DGT `V0144-26` | Si: `LIS art. 18`, `operaciones_vinculadas`, `partial` | No: `232` no trazado por supuesto | No cerrada | Relacion documental con modelo 232 y vigencia o estado historico explicito |
| D-04 CRS/FATCA | `partial` | DGT `V0138-24` | Si: modelo `289`, `crs_fatca`, `partial`; sin articulo normalizado | Parcial: `289` como evidencia documental incompleta | No cerrada | Articulo, supuesto reportable y vigencia/historico; separar doctrina, modelo y normativa internacional |
| D-05 Criptoactivos | `partial` | DGT `V0162-26` | No: falta anclaje operativo suficiente | No: `721` no trazado | No cerrada | Articulo fiscal exacto, modelo si aparece en fuente oficial y tipo de operacion |
| D-06 Dividendos e intereses | `partial` | DGT `V0187-26` | No: falta separar dividendos/intereses y decidir articulo | No: `216` no trazado por supuesto | No cerrada | Separar tipos de renta, persistir articulo correcto y validar modelo |
| D-07 Canones | `partial` | DGT `V0228-26` descartada como cierre | No: fuente actual trata LIVA/servicios, no canon IRNR | No: `216` no trazado | No cerrada | Nueva fuente canon/royalty IRNR con convenio o articulo aplicable y modelo |
| D-08 Establecimiento permanente | `partial` | DGT `V0235-26` | No: depende de hechos/convenio | No: `200` no trazado | No cerrada | Fuente EP IRNR/CDI con hechos, convenio/articulo y estado historico |
| D-09 Servicios profesionales | `partial` | DGT `V0191-26` descartada como cierre | No: fuente actual es LIVA art. 20, no servicios profesionales IRNR | No: `216` no trazado | No cerrada | Nueva fuente IRNR de servicios profesionales con articulo, pais/convenio si aplica y modelo |

## Lineas genericas DB-backed

Las lineas genericas pueden salir de `fail-closed` solo si la consulta principal tiene:

- fuente DGT/TEAC oficial,
- `row_completeness=complete`,
- `source_hash`,
- `capture_date`,
- articulo enlazado,
- fila `criterio_relacion` completa con impuesto y modelo o tipo de supuesto,
- `verified=true` y `completeness=complete`.

Si falta hash, captura o relacion suficiente, la respuesta debe seguir `partial` y `safe_to_answer=false`.

## Siguiente accion

1. Cargar o localizar fuente D-02 realmente intracomunitaria.
2. Cerrar D-03 solo si aparece relacion documental con modelo 232 y vigencia.
3. Normalizar D-04 por articulo o supuesto CRS/FATCA antes de intentar `complete`.
4. No persistir D-05..D-09 hasta tener anclaje real por articulo/modelo/supuesto.
