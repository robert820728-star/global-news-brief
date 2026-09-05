# Source Row Admission Ledger Implementation Plan

**Objective:** Make the complete discovery-row universe durable before source-scan completion and require exact row-level conservation through candidate audit and same-run recovery.

**Execution budget:** 40 minutes expected, 44-minute warning, 48-minute hard stop. Maximum three repair attempts. Two clean final-state audit passes are required.

## Task 1 — Freeze the row identity and ledger contract (8 minutes)

- Add failing tests for deterministic unique `row_id`, lossless relevance decisions, 132-row ledger conservation, duplicate/missing evidence rejection, and schema requirements.
- Evidence: focused tests fail for the intended missing behavior.
- Completion: RED failures identify the absent ledger boundary, not fixture mistakes.

## Task 2 — Implement the durable source-row ledger (10 minutes)

- Modify source candidate and relevance gate materializers.
- Add the row-admission schema and canonical ledger builder/validator.
- Evidence: Task 1 focused tests pass.
- Completion: all rows join one-to-one and incomplete article evidence fails closed.

## Task 3 — Bind audit and recovery to the ledger (10 minutes)

- Require `source_row_admissions` at source-scan checkpoint completion.
- Include it in pre-manifest recovery bundles.
- Require latest candidate audit dispositions to conserve ledger identities and model evidence.
- Evidence: checkpoint, recovery, and candidate-audit focused tests pass.
- Completion: downstream stages can resume from artifacts without discovery replay.

## Task 4 — Update runtime contracts and records (5 minutes)

- Update INSTALL, prompts, skills, schema/runtime inventories, and bilingual version record.
- Evidence: contract tests pass and no old three-artifact completion contract remains.
- Completion: repository instructions invoke and preserve the ledger consistently.

## Task 5 — Verify and audit (7 minutes)

- Run frozen focused tests, full suite, capsule verification, and two project-final-state-audit passes.
- Evidence: command outputs, clean worktree, source/capsule binding, bilingual audit report.
- Completion: no P0/P1 findings and all frozen acceptance checks pass.

