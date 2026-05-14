# Tax Review Patterns

## Common Traps

- A returned AEAT model is not automatically applicable.
- A model with casillas is not automatically obligatory.
- A model with `claves` and `instrucciones` can support field/key explanations, but still does not prove applicability to the user's facts.
- `reglas_inclusion` can support include/exclude/conditional answers only for the exact `supuesto` covered.
- `no-casillas-expected` means absence of structured fields is verified by design.
- `parcial` means do not produce full filing procedure.
- Annual/trimestral metadata may describe periodicity, not applicability.
- FATCA/passive NFFE questions should route to Modelo 290 evidence before generic IRNR model classification.
- IRNR legal citations should prefer `TRLIRNR` / `IRNR` article endpoints when relevant.

## Useful ESData Queries

- "Lista modelos AEAT para <supuesto>, clasifica confirmado/candidato/requiere verificacion, no afirmar obligatoriedad sin evidencia explicita."
- "Devuelve casillas del modelo <codigo> con paginacion, solo inventario, no obligatoriedad."
- "Devuelve claves, instrucciones y reglas de inclusion del modelo <codigo>; no completar huecos con memoria fiscal."
- "Que evidencia devuelve ESData para aplicar modelo <codigo> a <supuesto>?"

## Human Review Gate

Require professional review when the answer affects filing, withholding, payment, penalty exposure, or client communication.
