# Visible-Media Schedule Eligibility Design

## Problem

The production profile requires every selected event with a qualified current image to deliver that image visibly. The current installer may nevertheless create a recurring `mobile-native` task whose host cannot materialize a remote image as a local attachment and whose native image-card route is not reliable. That creates a deterministic dead end: discovery and image sourcing succeed, external hotlinks remain correctly forbidden, and the run stays at `visuals-completed` forever because no full-runtime worker is actually scheduled to resume it.

## Decision

A recurring canonical daily-news task with mandatory visible images is eligible for activation only on a desktop/local-project `full-runtime` execution surface. Installation must prove the exact delivery boundary before activating the recurrence: use the verified workspace's checked-in PNG, deliver it as a real local attachment in the current conversation, and confirm it is visibly rendered. A web/mobile-only host may still perform a one-time diagnostic or candidate review, but it must not be installed or represented as the production recurring canonical task.

The existing source fallback order and the prohibition on external image URL delivery remain unchanged. No new schema, receipt, recovery state, validator, execution mode, or compatibility path is introduced.

## Contract Flow

1. Resolve and bootstrap the current verified main in a desktop local project or worktree.
2. Before creating or activating the recurring task, visibly attach `maps/generated/taiwan-counties-yellow-v2.png` from the verified local workspace to the current conversation.
3. If the local attachment is not visibly rendered, do not activate the recurring task and do not fall back to a production `mobile-native` schedule.
4. If it succeeds, create or update the current-chat recurring task with the complete canonical template and full-runtime project execution.
5. Daily source images continue through direct media acquisition, legal same-event fallbacks, local materialization, and visible local attachment.

## Acceptance

- The high-authority installation contract rejects a production recurring `mobile-native` task for the mandatory-visible-image profile.
- The start prompt and README tell the user to create the task in a desktop local project and require the visible local-attachment smoke test before activation.
- The scheduled task template refuses to start a canonical news run when it is accidentally invoked without the proven full-runtime project surface.
- Existing external-URL and image-fallback gates remain present.
- Targeted and full repository tests pass, and the generated capsule binds the final source commit.

