# Mobile Resume Contract Closure Design

## Goal

Close the remaining execution-mode and mobile resume contradictions without adding a new validator, receipt, recovery state, manifest, compatibility layer, or evidence schema.

## Decisions

1. `news-brief-settings.md` and `INSTALL.md` describe the existing full-runtime and mobile-native paths separately. Full-runtime continues to use the event manifest and local asset validators. Mobile-native continues to use the run-scoped candidate audit, structured verification/map outputs, native image evidence, and the existing structural Reader check.
2. Extend the existing mobile ledger with two nullable artifact references: `verification_artifact` at `logs/runs/<run_id>/verification.json` and `map_decisions_artifact` at `logs/runs/<run_id>/map-decisions.json`.
3. Preserve the ledger's active-stage semantics. A mobile run entering `visuals-completed` or any later stage must already bind `verification.json`; a run entering `reader-rendered` or any later stage must already bind `map-decisions.json`. The active `selection-verified` stage itself does not claim verification has completed.
4. Artifact binding proves durable identity and resumability only. It does not introduce content-level validation or claim machine verification of the artifact's semantics.
5. Release source, tests, documentation, and the final bilingual version record in one source commit. The capsule workflow may then create one generated capsule commit. Do not add an active tracked source/version commit after that capsule.

## Rejected Alternatives

- Reintroducing a mobile manifest: duplicates the full-runtime authority and creates a parallel contract.
- Embedding verification results in candidate audit: mixes pre-verification scoring ownership with post-selection verification.
- Adding verification/map evidence schemas or validators: unnecessary for the bounded resume identity defect.
- Re-running verification or maps after resume: contradicts the first-incomplete-stage contract and wastes completed work.

## Acceptance

- Active instructions are mode-aware and contain no unconditional mobile manifest/local-asset validator requirement.
- Mobile stage advancement cannot pass the durable boundary without the correct run-scoped artifact reference.
- Full-runtime behavior remains unchanged.
- Existing and new targeted tests plus the full repository suite pass.
- The capsule is rebuilt from the final source state and remote CI is reported separately from repository correctness.

