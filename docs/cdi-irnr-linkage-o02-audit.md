# CDI E IRNR Por Tipo De Renta - Auditoria O-02

Estado: `implemented_partial`.

Esta auditoria prepara la conexion entre la renta domestica IRNR trazada en O-01 y los convenios de doble imposicion. No crea relaciones CDI nuevas porque la evidencia productiva aun no cumple el contrato minimo por pais, articulo y tipo de renta.

## Produccion Auditada

| pieza | estado | lectura |
|-------|--------|---------|
| `irs_dta_convention` | `86` convenios | Corpus consultable, con referencias BOE y JSON de enlaces/PDF en muchos casos |
| `irs_withholding_rule` | `1` regla activa | Regla `FDAP` de origen IRS; no sirve para cerrar dividendos/intereses IRNR Espana-CDI |
| `source_revision` CDI | `0` filas con entidad CDI | No hay hash/captura normalizada para convenio o articulo CDI |
| Dividendos/intereses CDI | `partial` | No hay regla productiva por `dividends`/`interest` con pais, articulo, fuente y hash/captura |

## Decision

No se persiste `cdi_modelo_relacion` ni relacion CDI equivalente para dividendos/intereses. La base domestica existe solo en `296` como claves de renta, pero el CDI requiere cierre adicional:

- pais o residencia fiscal efectiva,
- convenio aplicable,
- articulo CDI,
- protocolo o enmienda vigente si aplica,
- fuente oficial con hash/captura,
- y separacion entre regla domestica IRNR y modulacion convencional.

## Endurecimiento Aplicado

`POST /v1/internacional/convenios/retencion` conserva la respuesta exploratoria heredada, pero ahora declara explicitamente:

- `verified=false`,
- `completeness=partial`,
- `safe_to_answer=false`,
- `review_required=true`,
- `evidence_notice` de evidencia limitada.

Esto evita presentar una tasa reducida como resultado definitivo cuando el contrato CDI por articulo/renta no esta cerrado.

## Siguiente Accion

El siguiente bloque CDI debe empezar por un pais piloto, no por una regla generica. Candidato razonable: Alemania, Francia o Estados Unidos solo si se carga o verifica:

1. convenio oficial BOE/Hacienda/AEAT,
2. articulo de dividendos/intereses,
3. protocolo/enmiendas,
4. `source_hash` y `capture_date`,
5. test de `safe_to_answer=false` cuando falte certificado/protocolo.
