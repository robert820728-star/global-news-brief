# Event Region and Time Identity Gate Design

## Goal

Prevent a publisher's discovery bucket or a newly published retrospective from becoming the event's region or a new event. Every semantic event must carry independently evidenced structured geography and time identity before scoring.

## Contract

- Source-candidate `section` is a discovery hint only. It is never event-location evidence.
- `event_identity` adds `country_codes`, `primary_country_code`, `location_evidence`, `event_occurred_at`, `material_update_at`, `material_update_type`, and `material_update_evidence`.
- The candidate section is derived from `primary_country_code`: `TWN` -> `TWN`, `CHN` -> `CHN`, all other countries or `GLB` -> `GLB`.
- `material_update_at` must fall inside the exact run window. A `new_event` also requires `event_occurred_at` inside that window.
- An event whose occurrence predates the window must use a verified material-update type and continuity status. Republishing, retrospective summaries, anniversaries, headline changes, and unchanged recaps are not material updates; their article rows are `non_news`.
- Missing or contradictory geography/time identity is unresolved and cannot be scored, selected, or published.
- Region classification runs before the six-dimension score, so `core_section_relevance` is calculated from the validated event section.

## Compatibility

The schema accepts legacy identity fields in retained historical runs, while the latest-run validator requires the new structured fields. This preserves the rolling fourteen-day audit during migration and fails closed for every new run.

