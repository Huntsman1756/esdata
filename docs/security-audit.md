# Security Audit - Release v1.0.0

Date: 2026-05-12
Source: GitHub Dependabot alerts for `Huntsman1756/esdata`, state `open`.
Scope: R-01 release sprint dependency triage.

| pkg | severity | CVE | current | patched | action | accepted_risk |
| --- | --- | --- | --- | --- | --- | --- |
| next | high | CVE-2026-44574 / GHSA-492v-c6pp-mqqv | 15.5.15 | 15.5.16; upgraded to 15.5.18 | Fixed in `apps/web/package.json` and lockfile. Also aligned `eslint-config-next` to 15.5.18. Vector: middleware/proxy authorization bypass in affected Next.js routes. | none |
| torch | critical | CVE-2025-32434 / GHSA-53q9-r3pm-6pq6 | 2.5.1+cpu in `apps/api/requirements.txt` | 2.6.0; upgraded to 2.8.0+cpu | Fixed by upgrading CPU PyTorch pin in API requirements. Vector: unsafe deserialization/RCE via `torch.load` even with `weights_only=True`. | none |
| torch | critical | CVE-2025-32434 / GHSA-53q9-r3pm-6pq6 | 2.5.1+cpu in `apps/workers/requirements.txt` | 2.6.0; upgraded to 2.8.0+cpu | Fixed by upgrading CPU PyTorch pin in worker requirements. Vector: unsafe deserialization/RCE via `torch.load` even with `weights_only=True`. | none |
| torch | medium | CVE-2025-3730 / GHSA-887c-mr87-cxwp | 2.5.1+cpu in `apps/api/requirements.txt` | 2.8.0 | Fixed by same API upgrade to 2.8.0+cpu. Vector: local denial of service in `torch.nn.functional.ctc_loss`. | none |
| torch | medium | CVE-2025-3730 / GHSA-887c-mr87-cxwp | 2.5.1+cpu in `apps/workers/requirements.txt` | 2.8.0 | Fixed by same worker upgrade to 2.8.0+cpu. Vector: local denial of service in `torch.nn.functional.ctc_loss`. | none |
| torch | low | CVE-2025-2953 / GHSA-3749-ghw9-m3mg | 2.5.1+cpu in `apps/api/requirements.txt` | 2.7.1-rc1; upgraded to 2.8.0+cpu | Fixed by same API upgrade to 2.8.0+cpu. Vector: local denial of service in `torch.mkldnn_max_pool2d`. | none |
| torch | low | CVE-2025-2953 / GHSA-3749-ghw9-m3mg | 2.5.1+cpu in `apps/workers/requirements.txt` | 2.7.1-rc1; upgraded to 2.8.0+cpu | Fixed by same worker upgrade to 2.8.0+cpu. Vector: local denial of service in `torch.mkldnn_max_pool2d`. | none |

## Verification

- `npm install --package-lock-only next@15.5.18 eslint-config-next@15.5.18` completed with `found 0 vulnerabilities`.
- `python -m pip install --dry-run --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.8.0+cpu" "sentence-transformers==4.1.0"` resolved successfully and found the CPU wheel.
- `rg "torch.load|from_pretrained|SentenceTransformer|sentence-transformers|torch" apps libs scripts -g "*.py"` found SentenceTransformer model loading usage and no direct `torch.load` calls in first-party code.
- `npm audit --audit-level=high` in `apps/web` completed with `found 0 vulnerabilities`.
- `npm test` in `apps/web` completed with `1 passed`.
- `PYTHONPATH=apps;apps/api python -m pytest apps/api/tests/test_mcp_private.py apps/api/tests/test_modelos_truth_contract.py -q --basetemp .pytest-tmp-api` completed with `31 passed`.
- `PYTHONPATH=apps/workers python -m pytest apps/workers/tests/test_aeat_models.py -q --basetemp .pytest-tmp-workers` completed with `62 passed`.
- `python -m compileall apps\api apps\workers` completed successfully.

## Notes

Dependabot alerts are evaluated on the default branch. These fixes close the critical/high conditions once merged to `main` and re-scanned by GitHub. Until merge, default-branch alert state can still show open even though the release branch contains the remediation.
