# URL Recovery and Batched Model Triage Design

## Goal

Continue the lossless pilot by recovering descriptive titles from content URLs and packaging every provisional evidence group into bounded model-triage batches. The design reduces request count without deleting low-value events or allowing keywords to decide importance.

## Scope

This remains an experimental branch feature. It consumes the saved 20,450-row 2026-08-20 artifact and may also run compatibility checks on older saved artifacts. It does not modify the production schedule, the six-dimension rubric, the C threshold, or GitHub `main`.

## Data Flow

1. Reuse canonical URL, row conservation, and title-quality rules from the first pilot.
2. For each `needs_title_recovery` row, derive a `recovered_title_candidate` only from a descriptive URL path segment. The original title and URL remain unchanged.
3. Reject recovery candidates that are purely numeric, UUID-like, opaque identifiers, navigation labels, or shorter than three word tokens unless they contain at least six CJK characters.
4. Re-run exact-title grouping with the effective title. Recovered titles may consolidate evidence only when their normalized descriptive text and section match exactly.
5. Generate high-similarity pairs as model-review hints only. No fuzzy pair is automatically merged.
6. Sort all resulting groups deterministically by section, published time, and group ID, then pack at most 100 groups per model request.

## Model Contract

Every provisional group appears in exactly one batch. The model must return one result per group with:

- `group_id`;
- `event_fingerprint` as a neutral event identity, not a grade;
- extracted verifiable facts, including casualties, affected places, formal government decisions, and public-system interruptions when present;
- `needs_deep_review`;
- `reason` tied to supplied evidence;
- `candidate_event_ids` when two or more groups may describe the same event.

Keywords may route fact extraction but cannot score, delete, promote, or demote. Only deep review applies the six-dimension rubric.

## Failure Handling

- A failed model batch is retried as that exact batch; it is never silently skipped.
- Missing or duplicate returned `group_id` values fail validation.
- Title recovery failure leaves the row unresolved and auditable.
- All reports retain input `row_id`, source `candidate_id`, original title, recovered title candidate, URL, and provenance.

## Acceptance

- exact row conservation and deterministic hashes;
- zero automatic deletions and zero importance decisions;
- model batches cover every provisional group exactly once;
- no batch exceeds 100 groups;
- model review of all recovered-title multi-row groups finds zero confirmed false merges;
- deterministic samples expose unresolved recovery rows and suspected missed merges;
- no production promotion before three comparable 24-hour artifacts exist and a separate approval is given.

