# Cross-module reader contract convergence

## Objective

Remove the remaining executable contradictions between discovery, candidate audit, manifest materialization, verification, mobile-native execution, and publication without adding speculative subsystems.

## Scope decisions

### 1. Configured section scopes

The latest audit run carries `section_scopes`, ordered objects with `code`, `member_country_codes`, and `fallback`. Exactly one fallback is required. Candidate section validation uses event country codes against this run-scoped authority; it no longer hard-codes TWN, CHN, and GLB. Historical runs may omit the field. Source-candidate section fields accept any stable three-letter code.

This is the smallest complete implementation of the custom-section promise already present in installation and schedule contracts. It does not add a preferences parser or a new settings service.

### 2. Reader threshold

The publication threshold is C. C- remains a scoring and audit grade but is always reserve-only. Remove the special C- selection reason and field from schema, validators, manifest, skills, and tests.

### 3. Verification feedback

Do not add a second publication-disposition state machine. An `insufficient` verification finding must use `status=failed` and cannot enter a ready manifest. After bounded verification recovery is exhausted, the existing checkpoint is rewound to `audit-news-candidates`; discovery, preprocessing, and semantic selection remain completed. The affected candidate is then excluded or rescored, the manifest is rematerialized, and downstream stages rerun.

### 4. Truthful degraded execution

`validate_source_scan_evidence.py --scan-dir` validates scan files only for `scan_status=completed`. A truthful failed row must have unavailable metadata and no scan file. Readiness counts completed scans only.

Article hydration has two unresolved states: recoverable `unresolved`, which blocks completion, and terminal `unresolved_exhausted`, which remains in the row ledger and degrades coverage without blocking verified events. A dedicated conserved count prevents exhausted rows from being relabeled as non-news.

### 5. Web search boundary

Do not create a fictitious `fallback_web` source class. Cross-source web results cannot enter the canonical discovery pool and cannot satisfy source completeness. Web search may identify a same-source recovery lead that is rematerialized through the configured route, or support later verification. Remove all contrary promises.

### 6. V2-only selection semantics

Remove the fixed 48-hour re-entry gate and all event-type default-D language. Continuity, current realized impact, and material update scores decide each run.

### 7. Policy-stage evidence

Policy evidence requirements are stage-specific. Rumor permits empty legal basis and official actions but requires attributable evidence. Consideration requires evidence of active consideration but not a legal text. Proposal and later stages retain legal/official evidence requirements. Operational-effect arrays remain allowed to be empty until effects exist.

### 8. Mobile parity

Mobile-native instructions preserve the same scan-status versus coverage-status separation and the same degraded metadata as full-runtime.

## Explicit non-goals

- No new scoring dimension or grade band.
- No changes to image, map, bootstrap, or first-run fourteen-day behavior.
- No general-purpose fallback source framework.
- No rediscovery after verification feedback.

## Acceptance cases

1. JPN section scope accepts a JPN event through audit, manifest binding, and reader validation.
2. A selected C- candidate is rejected; C- reserve remains valid.
3. `verification.finding=insufficient` cannot coexist with completed verification or a ready release.
4. Checkpoint rewind from audit preserves earlier stage evidence and clears audit plus all downstream evidence.
5. One completed and two truthful failed sources pass standalone scan-directory validation when the configured minimum is one.
6. A terminal inaccessible article is conserved as `unresolved_exhausted`; verified candidates can still complete.
7. Cross-source web candidates remain forbidden in canonical discovery provenance.
8. Mobile and full-runtime contracts contain no event-type hard grade or fixed 48-hour gate and share the coverage fields.
9. Rumor and consideration candidates do not fabricate legal text; later policy stages retain stronger gates.

