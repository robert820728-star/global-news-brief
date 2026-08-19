# 48-Hour Re-entry and Per-Story Image Design

## Goal

Make the mobile daily brief retain meaningful continuing stories without repeating unchanged news every few hours, and prevent a single visible image from excusing image omissions across the rest of the brief.

## Re-entry policy

- Treat 48 hours from the event's last reader publication as a cooldown, not as a forced republication interval.
- During the cooldown, republish only when the newly verified impact independently reaches grade C or higher. Escalating disasters, epidemics, wars, public-safety events, and material policy or market consequences therefore remain immediately publishable.
- Once 48 hours have elapsed, rescore the event using its current verified impact. Republish when the current event still reaches C or higher; otherwise keep it in the rolling audit with the lower grade or remove it under the existing retention rules.
- Never inherit the prior or parent-event grade. The reason must state whether the event is new, materially updated inside 48 hours, or reassessed after 48 hours.

## Image policy

- Apply the image decision per selected story. `IMAGE_DEFAULT_ONE_ASSET` remains the default for every story, not a document-level average.
- For each story, inspect cited source-page body images, `og:image`, `srcset`, and official graphics, followed by one already-cited reliable same-event source when needed.
- A usable source image must be actually visible in the ChatGPT conversation. A URL, Markdown that renders as a broken image, a logo, or unrelated stock imagery does not pass.
- A story may use a non-technical no-image explanation only when no qualifying source image is available or public embedding is unsuitable, and the reason must describe that story's limitation. One visible image cannot satisfy other stories.
- An isolated image failure reruns only the image decision and delivery for that story. It must not restart discovery, scoring, verification, or reader text.

## Scope

Change only the existing settings/mobile prompt contract and its contract tests. Do not add a schema, service, image proxy, stage, classifier, renderer, checkpoint, or publishing path.

## Acceptance tests

1. The contract explicitly defines the 48-hour cooldown, immediate material-update exception, post-48-hour rescoring, and no automatic republication.
2. The contract requires a per-story image attempt and forbids one story's image from satisfying another.
3. Per-story omission remains allowed only with a concrete source/embedding limitation.
4. Existing continuing-event escalation, one-off decay, compact audit, and reader-structure tests remain green.
