# esdata - Sprint O: IRNR rentas, CDI y siguiente AEAT limpio

Pattern: Ralph - one story per iteration, fresh context each time.
Runner: OpenCode.
Prerequisite: PR #81 merged and deployed; production Alembic at `20260524_0088_aeat_irnr_216_296_rules`.

You are a senior Spanish tax data engineer. Your job is to extend ESData fiscal coverage without weakening the fail-closed contract.

## Current State

- D-01 is complete: DGT `V0166-25`, `TRLIRNR art. 31`, models `216/296`, hash/capture and persisted relation.
- Modelo `216` is complete as an AEAT model/form contract: official casillas, claves, instructions and 3 IRNR inclusion/exclusion rules.
- Modelo `296` is complete as an AEAT model/form contract: official casillas, claves, instructions and 4 IRNR inclusion/exclusion rules.
- Applicability by concrete scenario remains partial: `/v1/modelos/por-supuesto` classifies `216/296` as candidates and returns `evidence_limited`.
- `296` profile obligations are intentionally partial and must expose `safe_to_answer=false`.
- MCP legacy is stable for ESData scope. Do not touch MCP unless a new fiscal contract must be exposed.

## Sprint Scope

1. Granularize `216/296` by IRNR income type, starting with dividends and interests.
2. Prepare CDI linkage only after a domestic IRNR income-type base is traceable.
3. Select the next clean AEAT model candidate for a later sprint.

## Hard Rules

- One story per iteration. No exceptions.
- Do not mark `complete` by thematic similarity.
- Do not calculate final withholding or treaty relief.
- Do not use CDI to create the domestic AEAT obligation.
- Do not infer relation to model, article, income type or country from general knowledge.
- Official source only: AEAT, BOE, DGT/TEAC, CDI official text already loaded or directly verified.
- `verified=true` requires source URL, hash/capture or equivalent, and exact article/supposition evidence.
- `safe_to_answer=true` requires complete evidence, not just a model key or a doctrine line.
- If evidence is insufficient, leave `partial` and document the precise missing piece.
- Do not touch D-02..D-09 unless the current story explicitly requires a relationship and evidence exists.
- Do not touch MCP conformance/stateless work in this sprint.

## Operating Rules

Each iteration:

1. Read `prd.json`, `progress.txt`, and `git log --oneline -20`.
2. Pick the single highest-priority story where `passes=false`.
3. Complete only that story within the current context.
4. Prefer audit first. Query production when the story depends on actual loaded corpus.
5. If writing DB data, use Alembic or a versioned seed/migration. Never write production-only manual data without versioning.
6. Run the story verification commands; fix and retry if they fail.
7. Commit with `git commit -m "[STORY-ID] description"`.
8. Update `prd.json` with `passes=true` only when all acceptance criteria are met.
9. Append a concise entry to `progress.txt`: story, evidence, commands, result, caveats and next story.
10. Exit.

Stop condition: `<promise>COMPLETE</promise>`.

## Story-Specific Guidance

### O-01 - Income Types for 216/296

Start with dividends and interests because they connect naturally to D-06 and model `296` keys.

Audit before writing:

- Active campaigns for `216` and `296`.
- Existing `modelo_clave`, `modelo_instruccion`, `modelo_regla_inclusion`.
- Whether model `296` keys/subkeys distinguish dividends and interests with official provenance.
- Whether current sources point to Orden EHA/3290/2008 or AEAT technical design with hash/capture.

Allowed outcomes:

- Persist clean income-type rules/relations if source evidence is exact.
- Or document `partial` if keys exist but article/supposition evidence is not sufficient.

Do not:

- Treat a `296` key name alone as complete model applicability.
- Mix dividends, interests, canons, services or capital gains.
- Promote D-06 unless it independently satisfies doctrine criteria.

Minimum verification:

- Focused API/model tests for 216/296.
- Alembic integrity if migration is added.
- `ruff` on changed Python.
- Docs contract checks.

### O-02 - CDI Linkage

Run only after O-01 leaves at least one domestic income type with traceable model/article evidence.

Audit:

- CDI corpus loaded by country.
- Existing API/MCP exposure by country, income type and article.
- Whether the selected income type has a treaty article candidate.

Allowed outcome:

- Add a narrow relation for one country/income type if complete.
- Or document why CDI remains blocked.

Do not:

- Use CDI as substitute for TRLIRNR/RIRNR domestic obligation.
- Answer treaty rate or final withholding without residence/protocol evidence.

### O-03 - Next AEAT Model Candidate

This is a selection story, not a loading sprint.

Audit at least three candidates. Prefer deterministic official sources:

- model has official instructions,
- deterministic fields/casillas/XSD or confirmed no-casillas-expected,
- official source URLs,
- hash/capture already loaded or easy to load safely,
- limited risk of profile applicability confusion.

Avoid opening Modelo 100 unless evidence is unusually clean and scope can stay narrow.

Deliverable:

- One recommended next model with reasons and risks, or no candidate if evidence is not clean.
- Roadmap entry with next exact sprint.
