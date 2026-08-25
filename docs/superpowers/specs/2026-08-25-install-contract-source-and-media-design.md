# Install Contract, Discovery Pool, and Media Capability Design

## Objective

Make `INSTALL.md` the complete human installation and operating entry point, remove the obsolete fixed-source contract from every active surface, and make missing native-media delivery capability a recorded degradation instead of a blocker for a verified mobile-native reader run.

## Contract ownership

- `INSTALL.md` owns installation order, required files, execution-mode selection, the end-to-end stage table, required artifacts, validators, recovery entry points, and first-run acceptance.
- `daily-schedule-prompt.md` owns the detailed full-runtime daily execution contract.
- `mobile-chatgpt-daily-prompt.md` owns the scheduled mobile-native execution contract.
- `.agents/skills/daily-news-brief/SKILL.md` owns orchestration and stage ownership. Stage skills own only their bounded stage behavior.
- `news-source-pool.json` owns discovery routes only. Verification sources are selected per event and claim role; there is no fixed verification count or list.
- JSON schemas and validators are machine-enforced truth. Prose must match them.
- `news-brief-template.md` owns reader layout. `news-brief-examples.md` is consulted only to diagnose a reader-format failure.
- `VERSION-RECORD.md` and dated design/plan documents remain historical records, but describe the retired system generically so the obsolete numeric contract is not copied forward.

When two active owners overlap, their statements must agree. Installation stops only for a missing required file or an actual active-contract contradiction, and reports the exact paths and clauses.

## Discovery and verification model

The active discovery pool contains exactly three route definitions: GDELT, CNA, and China News Service. Every successful route contributes all verified in-window items to deduplication and scoring without a fixed top-N cutoff. GDELT acquisition is archive-first, followed by one non-blocking DOC API attempt only when archives are unavailable, then a labeled valid cache.

The former `primary_sources_per_section`, `section_sources`, fixed `sources` array, and legacy source health profile are removed. Candidate-audit coverage and recovery validate only configured discovery routes. Selected C-or-higher events are then verified with sources appropriate to the claim: original reporting, official or primary records, and genuinely independent evidence as needed. Verification is not constrained to a predeclared count or pool.

## Completion and native-media capability

Canonical run completion and native-media delivery are separate dimensions.

- `full-runtime`: required local map/chart/image artifacts must be materialized and validated before completion.
- `mobile-native`: a run may complete after the current-news pipeline, evidence checks, candidate audit, reader render, and reader delivery have passed. It must first attempt source-image download, screenshot fallback, and any supported local/native attachment route; absence of a specially named media tool is not proof of inability. Only an actual final-mile failure may record `delivery_profile=reader-canonical-capability-degraded`, `native_media_status=unavailable`, and `NATIVE_MEDIA_UNAVAILABLE` as a non-error capability limitation. It must preserve verified source-image and delivery-attempt evidence plus reader-safe omission notes, and must not claim attachment delivery or rendered-pixel validation.
- An unavailable media capability must not create a second run, mark `last_error`, rerun discovery, deduplication, scoring, verification, or reader rendering, or require a full-runtime continuation before the mobile-native run can become `completed`.
- A later full-runtime continuation may enrich only the missing visual-delivery stage using the preserved run identity and checkpoint. It is optional enrichment, not a prerequisite for the already completed mobile-native reader.
- Missing news evidence, unresolved candidate rows, invalid reader structure, or a visual artifact that the declared execution profile claims to have delivered remain blocking defects.

The mobile run ledger therefore records both terminal run status and a delivery profile/capability limitation. A completed capability-degraded run requires `delivery-handoff`, a saved reader artifact, a saved candidate-audit artifact, and `delivery_status=handoff_started` (or an externally acknowledged confirmation). It must have no `last_error`.

## Installation and operating flow

`INSTALL.md` will include:

1. The three installation questions and defaults.
2. A complete required-file inventory including all nine skills, all active schemas, core scripts, configurations, templates, maps, and bootstrap files.
3. A document authority and reading-order table.
4. A full-runtime versus mobile-native capability table and completion criteria.
5. An end-to-end stage table from latest-main resolution/bootstrap through source scan, preprocessing, selection, audit, manifest materialization, verification, maps, charts, images, render, publish, bundle, and delivery.
6. Required inputs, artifacts, mandatory fields/counts, validators, local-recovery boundaries, and completion conditions for every stage.
7. Correct canonical reader structure beginning with `# 每日新聞讀者版`, followed by the manifest-derived reporting period, grading explanation, one `## 今日總覽`, then sectioned stories.
8. First-run validation, degraded-mode behavior, and exact pre-manifest/post-manifest recovery commands.

## Error and recovery behavior

- Bootstrap failure occurs before checkpoint creation and is repaired in place.
- Pre-manifest failures use the durable source/candidate/preprocess/selection/audit artifacts and do not restart completed source routes.
- Post-manifest failures use event/stage-specific patches and rerun only the failed stage.
- `NATIVE_MEDIA_UNAVAILABLE` is a warning/capability limitation for `mobile-native`, not a recovery target or `last_error`.
- GDELT, CNA, or China News Service route degradation is recorded and does not block publication when current candidates remain verifiable.
- Fourteen-day cross-run incompleteness is an audit status and does not erase or block a valid current 24-hour reader.

## Verification

Tests will enforce discovery-only pool semantics, absence of fixed-source active contracts, archive-first GDELT wording, nine-skill inventory, canonical reader structure, bootstrap/checkpoint order, same-source fallback order, and capability-degraded mobile completion. Targeted tests run first with the bundled Python runtime, followed by the full suite, an active-surface residue scan, and bootstrap capsule rebuild/verification tied to the source commit.

## Scope exclusions

Historical records are not rewritten. The scoring rubric, grade thresholds, map style, event schema content outside delivery capability metadata, and unrelated parsers are not redesigned.
