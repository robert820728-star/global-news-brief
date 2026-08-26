# rc.8 Execution-Mode and Manifest Convergence Design

## Objective

Close the remaining execution-mode and policy-stage contradictions without weakening full-runtime evidence gates or adding another schema, validator, receipt, recovery state, fallback class, or compatibility layer.

## Decisions

1. The existing news-event manifest remains the full-runtime publication contract. Its local evidence, materialized asset, hash, dimension, and visual-check requirements stay fail-closed.
2. Mobile-native does not claim to create or validate that full-runtime manifest. It preserves the existing run-scoped candidate audit, image evidence, reader, and mobile ledger; structural Reader checks use selected event IDs and follow-up text from the run-scoped audit.
3. Native image cards are conversation-transport results recorded in the existing image evidence and ledger. They are not inserted into `images.assets`, which remains reserved for canonical local attachments.
4. `INSTALL.md` and the scheduling contracts explicitly state the full-runtime and mobile-native implementations at checkpoint, admission, manifest, render, and delivery stages.
5. Policy proposals and drafts may have an empty `legal_basis` when attributable proposal evidence, official action, and affected actors exist. Introduced and later formal stages retain the legal-basis requirement.
6. Lower-authority image and README prose is synchronized to the same execution-mode split. No new runtime behavior is introduced.

## Acceptance

- Old unconditional Python/manifest language fails regression tests.
- Mobile-native contracts do not claim unavailable local materialization or full-runtime manifest validation.
- Full-runtime manifest schema remains unchanged and fail-closed.
- Proposal/draft with empty `legal_basis` passes; introduced with empty `legal_basis` fails.
- Targeted tests, the full repository suite, rebuilt capsule verification, two fixed-fingerprint final-state audit cycles, and remote CI pass.
