# Sprint I RTS 1/RTS 2 MiFIR report

Fecha de cierre: 2026-05-18

## Normas cargadas

- RTS 1 `32017R0587`: Reglamento Delegado (UE) 2017/587, transparencia para instrumentos de renta variable.
- RTS 2 `32017R0583`: Reglamento Delegado (UE) 2017/583, transparencia para instrumentos distintos de los de renta variable.
- Ambas quedan vinculadas a MiFIR `32014R0600` mediante `norma_padre_celex`.

Fuentes primarias:

- https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0587
- https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0583

## Obligaciones por perfil

Las obligaciones RTS 1/2 de transparencia pre/post negociacion se cargaron como condicionales a estatus SI u operativa de centro de negociacion. La combinacion contractual es `verified=true` y `completeness='parcial'`.

Conteo VPS tras seed:

```text
agencia_valores=4/4 verified/4 parcial
entidad_credito=4/4 verified/4 parcial
sociedad_valores=4/4 verified/4 parcial
```

Exclusiones verificadas:

```text
eaf + sgiic + empresa_servicios_pago con RTS 1/2 = 0
```

## ESMA SI register

La tabla disponible para la referencia de apoyo es `documento_interpretativo`; no existen `registro_oficial`, `fuente_referencia` ni `esma_registro`.

Se cargo `ESMA_REGISTERS_MIF_SI` como `tipo_documento='registro_esma'`, `tipo_fuente='registro_oficial'`, `row_completeness='complete'`, `row_provenance='official_exact'`, y se vinculo como fuente soporte en `obligacion_fuente` con peso 2.

Fuente:

- https://registers.esma.europa.eu/publication/searchRegister?core=ESMA_REGISTERS_MIF_SI

## Verificacion

VPS `/srv/esdata-sprint-i`, commit `9491e51`:

```text
mcp_validation_suite.py --read-only --base-url http://api:8000 => ok=true
mcp_deep_contract_audit.py --base-url http://api:8000 => ok=true
/status => api=ok, database=ok
Alertmanager => 0 alertas activas listadas
```

Suite local:

```text
pytest apps/ -q --basetemp .pytest-tmp => 3124 passed, 2 skipped, 34 warnings
```

Conteo final VPS:

```text
obligacion_perfil=151, verified=151
```
