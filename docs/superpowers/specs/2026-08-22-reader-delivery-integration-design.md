# Reader Delivery Integration Design

## Goal

Make one short run instruction—follow the repository contract plus explicit
regions and monitoring topics—produce a fail-closed daily brief whose reader
layout, source-image evidence, map requirements, and attachment placement are
validated consistently.

## Approved scope

The repository has one canonical reader layout: the existing sectioned layout in
`news-brief-template.md`. Each populated section contains its complete
`Time | Event | Grade` table followed immediately by that section's stories.
Each story uses title and grade, ordered visible assets, summary, and grading
comment with source links. The structured three-heading layout is retired from
the production delivery path.

The input contract remains preference-driven. Regions map to `sections`;
monitoring types map to normalized `topic_weights`. Unrecognized monitoring
labels must be preserved as explicit user preferences or rejected before a run;
they must not silently change the reader format or discovery limits.

## Components

1. `validate_news_brief.py` owns the canonical sectioned reader validator. It
   compares every Markdown image target with the manifest, enforces per-story
   asset order (map, charts, source images), requires numbered captions directly
   after each attachment, and rejects unmanifested or out-of-story images.
2. `publish_news_brief.py` and `check_unique_delivery_gate.py` call only the
   canonical sectioned validator. No production path may invoke the retired
   structured validator.
3. The manifest schema permits `images.reader_omission_note`, which is required
   when all cited source pages were evidenced as having no usable image.
4. A map decision marked `required: true` must be `ready` with at least one
   validated asset before a release can be ready. `omitted` remains an internal
   recovery state and cannot be published.
5. Runtime capability is explicit: mobile-native output may be a degraded draft,
   but canonical completion requires full-runtime attachment and visual checks.

## Error handling

Reader-only defects return to render validation. Image evidence defects return
to `collect-news-images`. Missing required maps return to
`build-news-maps`. Discovery, semantic event scoring, and verification are not
rerun for a render-only failure.

## Verification

Automated tests cover a valid sectioned reader, an evidenced no-image story, a
required map, two source images with independent captions, reversed assets,
missing captions, an extra image inside a story, and an image outside all story
blocks. Contract tests assert that publisher and delivery revalidation call the
sectioned validator and that the old three-heading contract is absent from
production instructions.
