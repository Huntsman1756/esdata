# Regulatory Accuracy Spot Check A-07 - 2026-05-20

## Scope

A-07 reviewed 8 production rows on VPS `root@212.227.227.64`:

- 5 deterministic LIVA article samples from `articulo` + latest `version_articulo`.
- 3 MiCA article-linked checks, including both recent `emisor_token` obligations:
  - CASP `art. 59`
  - ART issuer `art. 18`
  - EMT issuer `art. 48`

The MiCA sample was intentionally not random-only: it includes `emisor_token` because Sprint N is the newest profile and most likely to expose source or article-reference gaps.

## Source Verification

Authoritative source checks from VPS:

```text
BOE LIVA consolidated act: https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740 -> HTTP 200
BOE article anchors: a84, a170, a67, a80, a86 -> HTTP 200
EUR-Lex MiCA source_url: https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114 -> HTTP 202 WAF challenge
BOE DOUE MiCA mirror: https://www.boe.es/buscar/doc.php?id=DOUE-L-2023-80808 -> HTTP 200, contains 2023/1114 and mercados de criptoactivos
Publications Office MiCA DOC_1: http://publications.europa.eu/resource/cellar/96f8d79d-178e-11ef-a251-01aa75ed71a1.0007.02/DOC_1 -> HTTP 200
```

EUR-Lex returning `202` is the known WAF behavior. The stored `source_url` remains the canonical EUR-Lex URL; content was verified through BOE DOUE and Publications Office official URLs.

## LIVA Articles

All 5 LIVA rows have:

- `boe_reference = BOE-A-1992-28740`
- authoritative BOE source URL
- latest `version_articulo.vigente_desde` populated
- non-empty text
- valid `boe_bloque_id`

| article | DB ids | vigente_desde | source | text status | spot-check |
|---|---:|---:|---|---|---|
| `84` | articulo `363`, version `376` | `2023-01-01` | BOE `BOE-A-1992-28740#a84` | `8549` chars | Text starts with `Articulo 84. Sujetos pasivos`; matches VAT subject-passive content. |
| `170` | articulo `899`, version `898` | `2015-01-01` | BOE `BOE-A-1992-28740#a170` | `3092` chars | Text starts with `Articulo 170. Infracciones`; source page contains article heading. |
| `67` | articulo `245`, version `244` | `2002-01-01` | BOE `BOE-A-1992-28740#a67` | `237` chars | Text starts with exemption general rules; source page contains article heading. |
| `80` | articulo `339`, version `346` | `2023-01-01` | BOE `BOE-A-1992-28740#a80` | `9982` chars | Text starts with `Articulo 80. Modificacion de la base imponible`; source page contains article heading. |
| `86` | articulo `384`, version `382` | `2011-01-01` | BOE `BOE-A-1992-28740#a86` | `1158` chars | Text starts with `Articulo 86. Sujetos pasivos`; source page contains article heading. |

Result: PASS.

## MiCA Article-Linked Checks

The three MiCA checks join:

- `obligacion_perfil`
- `norma`
- `eurlex_act`
- `eurlex_article`

All 3 have:

- `norma_codigo = 32023R1114`
- `celex = 32023R1114`
- `tipo_norma = reglamento_ue`
- `verified = true`
- `source_url = https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1114`
- matching article text in `eurlex_article`
- non-empty `eurlex_article.url_eurlex`
- `eurlex_article.capture_date = 2026-05-20`

| profile | obligation | article | completeness | article text status | spot-check |
|---|---|---|---|---:|---|
| `casp` | CASP authorization | `art. 59` | `completa` | `2894` chars | Article text starts with `Autorizacion`; contains CASP/service provider authorization rule. |
| `emisor_token` | ART authorization | `art. 18` | `completa` | `6159` chars | Article text starts with `Solicitud de autorizacion`; matches ART issuer authorization context. |
| `emisor_token` | EMT issuer notification/requirements | `art. 48` | `parcial` | `2069` chars | Article text starts with EMT public offer/admission requirements; conditionality correctly reflected as `parcial`. |

Result: PASS.

## Findings

No blocking data accuracy findings.

Non-blocking notes:

- MiCA `source_url` is canonical EUR-Lex, but simple curl receives WAF `202`; official content was verified through BOE DOUE and Publications Office.
- MiCA obligations are profile obligations, not `version_articulo` rows. For MiCA, equivalent article text/source validation uses the dedicated `eurlex_article` table.

## Conclusion

A-07 passes:

- 8 rows reviewed.
- BOE/CELEX references are correct.
- Source URLs are authoritative.
- LIVA `version_articulo.vigente_desde` is populated.
- MiCA article text exists for CASP and `emisor_token` ART/EMT samples.
