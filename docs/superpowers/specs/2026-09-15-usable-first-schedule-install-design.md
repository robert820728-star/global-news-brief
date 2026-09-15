# Usable-First Scheduled Task Installation Design

## Goal

Make the ordinary installation path reliably create or update one enabled daily 06:00 ChatGPT Scheduled Task before optional diagnostics, while preserving canonical prompt integrity and duplicate prevention.

## Root Cause

The current contract couples three different outcomes into one blocking release gate: persistence of the scheduled task, optional metadata readback, and visible-media capability smoke. A successful create/update can therefore be reversed into an installation failure when later readback is truncated or a media path is unavailable. Context recovery compounds the dead end by forbidding an idempotent update even when the exact task ID is known.

## Chosen Design

Use one control-plane mutation as the installation product action. The canonical create/update payload contains the complete prompt, daily 06:00 recurrence, account timezone, current-conversation delivery, and `enabled=true`. A successful response containing the exact task ID is the installation acknowledgement.

Saved-prompt, timezone, next-run, and delivery readback remain useful verification evidence, but missing or truncated readback produces `verification_partial`; it does not undo the acknowledged installation. Visible-media smoke becomes a post-install diagnostic of the runtime route. It must not pause, disable, delete, reschedule, replace, or duplicate the formal task. Each real occurrence continues to enforce its own Reader and visible-media publication gates.

## State Transitions

- `new_without_exact_id`: authoritative inventory; update the single match or create once after authoritative absence.
- `known_exact_id_resume`: submit the canonical desired state idempotently to that exact ID. Inventory and create are forbidden.
- `create_outcome_unknown`: reconcile the original operation identity. A second create is forbidden.
- `multiple_present`: report the exact IDs and do not mutate automatically.
- `unknown_without_exact_id`: report the actual control-plane limitation and do not create blindly.

## User-Facing Starter

The starter contains only the repository, four user settings, fresh-main instruction, complete INSTALL compliance, and singleton prohibition. Internal state-machine prose stays in `INSTALL.md` instead of being duplicated in the paste-ready prompt.

## Failure Semantics

- Create/update rejected or no exact task ID: installation not acknowledged.
- Create/update acknowledged: task remains enabled and usable.
- Optional readback missing: `verification_partial`, with unavailable fields listed.
- Optional smoke fails: record the unavailable media route; do not mutate the schedule.
- Runtime Reader/media failure: fail the occurrence only; never mutate the formal task.

## Acceptance

Tests must prove the starter is concise, known-ID recovery is idempotent, acknowledged create/update is not invalidated by missing readback, smoke is nonblocking, and no diagnostic path can disable or recreate the formal task. The full repository suite, capsule verification, clean export, remote CI, and final-state audit must pass on one final fingerprint.
