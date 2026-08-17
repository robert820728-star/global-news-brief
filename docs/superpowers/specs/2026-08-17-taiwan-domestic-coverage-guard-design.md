# Taiwan Domestic Coverage Guard Design

## Goal

Prevent nationally relevant Taiwan economy, consumer-safety, and central-government events from disappearing before grading, while keeping the mobile ChatGPT daily run close to its current cost and source count.

## Root cause

The validated daily run shows two distinct failures. Some requested topics never entered the 300-item candidate audit, while the central-budget topic entered only as a mixed weekly roundup and was graded as that roundup rather than as a distinct institutional event. Taiwan acquisition is also materially weaker than global structured feeds: the UDN route produced 20 numeric titles among 37 items, TVBS exposed only 13 items, and EBC was dominated by low-signal stories.

## Chosen design

Keep the existing five primary Taiwan sources and fifteen-source global contract. Add three bounded Taiwan-only coverage sweeps after normal source materialization:

1. economy, trade, industry, and supply-chain effects;
2. food, medicine, consumer safety, and nationwide recalls;
3. central budget, legislation, constitutional action, and public-system operation.

Each sweep returns at most five results, is restricted to the configured Taiwan primary-source domains, and is limited to the same 24-hour window. A discovered URL is not a parallel untracked source. It must be fetched through the owning source's same-source recovery path, added to that source's ranked items with evidence, deduplicated, scored, and audited normally. Therefore every selected URL remains inside the canonical fresh candidate pool.

Repair HTML materialization so an anchor's `title` or `aria-label` is preferred over an empty image anchor or numeric URL slug, and a later descriptive title can replace an equal-time low-quality candidate for the same URL.

## Domestic grading calibration

Taiwan is a monitored section. The selector must explicitly reassess at least C when verified evidence shows nationwide or multi-industry consequences, a broad official business survey with material operating effects, a product contamination and recall affecting ordinary consumers or multiple downstream firms, or a central budget/constitutional action with concrete effects on agencies or public services.

This is not topic-based automatic promotion. A recurring political accusation, social-media anxiety, rumor, survey without material consequences, or unchanged budget dispute remains below C unless the current window contains a concrete decision, legal action, funding effect, service disruption, or other direct consequence. Grades continue to follow the public-value dimensions and require a case-specific reason.

## Cost and failure handling

The guard adds only three searches with five-result caps and runs only for the Taiwan section. It does not add primary sources, scan every government site, or start image work for rejected candidates. A sweep failure is recorded by beat and retried once; it cannot erase successful primary-source scans. If a relevant result cannot be materialized through an existing Taiwan source, it is recorded as a coverage lead but cannot silently enter the audited pool.

## Acceptance

- UDN-like HTML produces descriptive article titles rather than numeric IDs.
- The daily and mobile contracts contain the three Taiwan sweep beats, same-source restriction, five-result cap, and normal audit requirement.
- Examples distinguish the three requested event types from rumor or consequence-free political commentary.
- Existing 15-source and mobile low-cost contracts remain intact.
- Full tests and capsule verification pass before publication.
