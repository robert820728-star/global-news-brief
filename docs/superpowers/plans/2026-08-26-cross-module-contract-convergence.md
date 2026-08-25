# Cross-module reader contract convergence implementation plan

## Frozen acceptance scope

Rollback source: `e1e0336aa6f5fcf0b4260c699c693159847e2948`.

| Task | Expected | Warning | Hard stop | Evidence | Completion condition |
|---|---:|---:|---:|---|---|
| Add red cross-module tests | 6 min | 6.6 min | 7.2 min | Targeted failing tests | Every accepted defect has a failing executable case |
| Implement schema and validator changes | 10 min | 11 min | 12 min | Targeted tests | Section, C-, verification, source, hydration, and policy cases pass |
| Remove stale operational prose | 5 min | 5.5 min | 6 min | Structural repository searches | No web-candidate promise, 48-hour gate, or hard-D prose remains |
| Full regression | 4 min | 4.4 min | 4.8 min | `unittest discover` | Full suite passes from the final fingerprint |
| Independent final-state audit | 10 min | 11 min | 12 min | Append-only ledger and report | Two consecutive zero-finding cycles on one unchanged fingerprint |

## Test-first sequence

1. Extend candidate-audit fixtures with default section scopes and exhausted-hydration counts.
2. Add JPN scope, selected C-, and `unresolved_exhausted` tests.
3. Add failed-source scan-directory CLI test.
4. Add insufficient-verification and checkpoint-rewind tests.
5. Add rumor/consideration policy-stage tests.
6. Extend obsolete-contract and mobile parity tests.
7. Run the new tests and confirm they fail for the intended reasons.
8. Patch schemas, scripts, settings, skills, prompts, and examples.
9. Run targeted tests, then the frozen full suite.
10. Run the project-final-state audit methods and reset the streak after any formal artifact change.

