# Scheduled Task Lifecycle Hardening Design

## Goal

Make the repository's installation and runtime contracts support one durable daily 06:00 ChatGPT Scheduled Task without duplicate creation, self-disabling behavior, occurrence deadlock, cross-workflow `run-logs` races, or off-main runtime execution.

## Confirmed root causes

1. The paste-ready installer hard-codes `create_new` and forbids inventory before the first create. That combination has no legal transition when a matching task is already present or its existence is unknown.
2. The runtime requires a structured `scheduled_for` field that the observed Scheduled Task host does not expose, even though the host identifies the turn as a real scheduled trigger.
3. The canonical runtime only prohibits disabling the task for one narrow candidate-audit condition. It does not globally forbid task-control mutations from a runtime occurrence.
4. The two workflows that write `run-logs` use different concurrency groups, so they are not serialized across workflows.
5. Both issue-comment workflows checkout a supplied 40-character SHA without proving that the commit belongs to `main` history.

## Considered approaches

### A. Capability-aware singleton transaction — selected

Use an `ensure_singleton` installation intent. If authoritative task inventory is available, adopt and update the unique matching task or create exactly once after authoritative absence. If inventory is unavailable, preserve an explicit unresolved lifecycle receipt and never perform a second create. This is the only approach that states exactly which duplicate-safety guarantees can be proven at each boundary.

### B. Repository-hosted task registry — rejected

Persisting task IDs in GitHub would improve recovery but would not be authoritative after a user deletes, duplicates, or edits a task in ChatGPT. It cannot replace control-plane inventory.

### C. Blind explicit create — rejected

Treating every fresh conversation as permission to create once is simple, but it cannot satisfy the simultaneous requirement that no duplicate recurring task be created.

## Design

### Installation state machine

The paste-ready starter uses `ensure_singleton`. Its legal transitions are:

- `present` with one exact matching task: adopt the exact ID and update it once.
- `absent` proven by authoritative inventory: create once and retain the returned exact ID.
- `multiple_present`: do not mutate any task; return the exact conflicting IDs for reconciliation.
- `unknown` because authoritative inventory is unavailable: do not claim duplicate-safe completion and do not create again. Preserve the actual control-plane limitation and any first-create operation identity.

An explicit user request carrying an exact task ID may select `update_existing`. A destructive request to create an additional task must be separately explicit and is outside the canonical singleton installer.

### Occurrence authority chain

The canonical occurrence key is resolved in this order:

1. Structured control-plane `scheduled_for`.
2. Verified Scheduled Task host provenance plus exact task identity and the first actual execution timestamp. The normalized timestamp becomes the canonical `scheduled_for` value stored in the existing ledger schema.

Ordinary user messages, assistant follow-ups, copied results, title matches, and manually supplied timestamps are never occurrence authority. The fallback is allowed only when the host itself marks the turn as an actual Scheduled Task trigger.

### Formal-task immutability

The saved runtime prompt states an unconditional invariant before the first runtime gate: a news occurrence cannot create, update, pause, disable, delete, reschedule, or replace its formal recurring task. Runtime failures may only update the run ledger and return a bounded failure receipt. Task-control mutation requires a separate installation or maintenance conversation, an exact task ID, and direct user authorization.

### Workflow serialization and runtime integrity

Every workflow that writes `run-logs` uses the same issue-scoped concurrency group with a maximum queue. Before executing any checked-out runtime, the workflow fetches `origin/main` and the requested SHA and proves that the requested SHA is an ancestor of `origin/main`. This retains same-occurrence historical-main execution while rejecting off-main commits.

## Error handling

- A missing inventory capability is reported as an external control-plane limitation, not as proof of absence.
- Multiple matching tasks are an explicit conflict and never trigger automatic deletion or update.
- A scheduled trigger without structured `scheduled_for` may proceed only through verified host provenance; a normal chat turn remains blocked.
- An off-main SHA fails before repository code from that SHA is executed.
- Concurrent `run-logs` writers queue on one shared key instead of racing pushes.

## Test strategy

- State-transition tests cover `present`, `absent`, `multiple_present`, `unknown`, and exact-ID update paths.
- Runtime contract tests prove the host-provenance fallback is accepted and a normal follow-up remains rejected.
- Contract tests assert the unconditional formal-task mutation prohibition across every canonical runtime document.
- Workflow tests assert one shared concurrency key, maximum queueing, ancestry verification before pinned checkout, and rejection of a non-main SHA fixture.
- Each repair follows RED, GREEN, targeted regression, full suite, capsule rebuild/verify, clean export, and outcome-alignment audit before the next repair begins.

