# Canonical Scheduled Task Instruction Design

## Goal

Make a new-chat request such as “create the daily news schedule from the latest repository `INSTALL.md`” produce one complete, durable Scheduled Task instruction instead of a thin launcher that leaves high-risk behavior to model memory.

## Root Cause

The current `SCHEDULE_PROMPT_AUTHORITY_GATE` explicitly forbids embedding image fallback, discovery, scoring, stage, and delivery requirements in the task prompt. It therefore generates a short launcher. At execution time the model may compress the linked contract and prematurely classify a visible article image as unavailable.

## Design

- Add one canonical `scheduled-task-prompt-template.md` as the exact task-instruction source.
- Keep latest `main` plus `INSTALL.md` as the dynamic authority; the template must fresh-resolve them on every trigger.
- Put the stable, high-salience minimum execution envelope directly in the task instruction: one occurrence/run, exact 24-hour window, coverage truthfulness, Public Value V2 selection, independent verification, per-story image acquisition and visible delivery, canonical three-part Reader, same-run recovery, and current-conversation delivery.
- The task creator may substitute only regions and monitoring types. Schedule time and timezone remain task metadata.
- Do not add a schema, validator, receipt, state, source class, or compatibility mode.

## Acceptance

- A contract test rejects the old launcher-only policy.
- The exact template contains every required execution family and the four-tier image fallback, including direct article JPEG/WebP delivery.
- `INSTALL.md` and `README.md` point to the template as the only task prompt source.
- Existing full suite and capsule verification pass.

