# CNMV Consolidation Audit - 2026-05-14

## Contract Gap

`estado_vigencia='vigente_modificado'` means the CNMV document is still current but has been amended. It does not prove that the text stored in ESData is the current consolidated text.

Before this change, `documento_version` and `documento_cnmv_version` recorded a version row, but neither table could say whether that version was:

| situation | risk |
|---|---|
| BOE consolidated current text | none |
| original BOE publication plus modification note | high |
| latest partial amendment text | medium |

The fix adds explicit consolidation audit metadata to both version tables:

| column | meaning |
|---|---|
| `es_consolidado` | `true` only when the loaded version is verified as consolidated text |
| `consolidated_verification_status` | `consolidated`, `not_consolidated`, `unknown`, or `verification_error` |
| `consolidated_source_url` | BOE URL checked during audit |
| `consolidated_checked_at` | timestamp of the check |
| `boe_last_modified` | official last modification date if deterministically extracted |
| `consolidated_evidence_note` | concise reason for the classification |

## Operational Rule

A `documento_version` row is not evidence of consolidated text by itself. Retrieval, audits, and human review must inspect `es_consolidado` and `consolidated_verification_status`.

For compliance answers:

- `consolidated`: can be used as current consolidated evidence, subject to normal source citation.
- `not_consolidated`: cite as loaded historical/original text, not as consolidated current law.
- `unknown` or `verification_error`: return `evidence_limited` or require manual verification.

## Audit Script

Run from repo root on the VPS:

```bash
scripts/maintenance/audit_cnmv_consolidated_versions.sh --dry-run
scripts/maintenance/audit_cnmv_consolidated_versions.sh --apply
```

The script checks every CNMV `vigente_modificado` circular against the BOE `act.php` page for its `BOE-A-*` reference and updates both version tables conservatively.

Current conservative behavior: if BOE redirects/canonically links to `doc.php` and no consolidated marker is found, the row is marked `not_consolidated`. This is intentional. A false `consolidated=true` would be worse than an `evidence_limited` response.
