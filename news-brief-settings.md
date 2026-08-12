# News Brief Settings

## Purpose

Track the user's daily news brief rules in a versioned text file so future changes can be reviewed and restored from git history.

## Schedule

- Main daily news brief: keep the existing official scheduled task unchanged unless explicitly requested.
- Independent tests: create separate tasks when requested. Do not merge, pause, modify, or otherwise interfere with existing news tasks unless explicitly requested.
- Time window: each run should judge news from the actual execution time looking back 24 hours.

## Output Format

Start each brief with a severity summary before the detailed news items.

The severity summary should:

- State how many news items are worth noting today.
- Group items by severity level when useful.
- Use compact one-line entries, such as `Russia-Ukraine war escalation - A`.
- Keep the list factual and avoid exaggeration. Upgrade severity only when evidence supports wider impact, rapid escalation, cross-border spread, systemic risk, or unusually high casualties.

Severity levels:

- `SS`: Extreme global/systemic crisis risk, such as multiple major wars merging, several great powers being pulled in, or a plausible near-term world-war scenario.
- `S`: Severe international or regional crisis, such as multi-country war expansion, large-scale lockdowns across countries, major financial/systemic shock, or fast-moving pandemic-level spread.
- `A`: Major event requiring attention, such as serious war escalation, multi-country disease spread, very high casualties, major disaster, or strategically important political/economic shock.
- `B`: Important but still limited event, such as a new fast-spreading disease before broad regional collapse, meaningful but contained conflict escalation, or a significant policy/economic event.
- `C`: Routine or low-signal event, such as ordinary seasonal outbreaks, isolated incidents, or minor updates. Usually omit unless context makes it useful.

Severity should guide length:

- `C`: Usually omit. If included, keep the summary under 20 Chinese characters or similarly short.
- `B`: Keep concise. Give the key fact, why it matters, and one caution if needed.
- `A`: Give enough context to understand scale, trend, and likely next developments.
- `S`: Explain clearly with sources, affected countries or sectors, escalation paths, uncertainty, and practical reasons to keep watching. If the topic matches the user's interests or may develop quickly, suggest creating a separate monitoring task.
- `SS`: Treat as a top-level crisis brief. Be explicit about evidence, uncertainty, possible scenarios, and why this crosses from severe news into systemic global risk. Suggest independent monitoring unless the user has already declined it.

Each selected news item should use these sections, in this order:

1. Severity Summary
2. Title
3. Sources
4. Details
5. Positions
6. Analysis

If there are no meaningful competing positions, stakeholder differences, or useful angles to compare, omit the Positions section entirely.

## Selection Notes

- Prioritize genuinely important Taiwan, China, and international event news.
- Include entertainment, film, television, documentaries, or cultural items only when they are exceptional, highly influential, or useful for serious discussion.
- Avoid filler items added only to satisfy a category.
- Duplicate coverage is allowed for independent test tasks; each task should judge importance on its own.

## Current Confirmed State

- The news brief format was updated to include Title, Sources, Details, Positions, and Analysis.
- Positions should be omitted when not useful.
- Each brief should begin with a severity summary that counts notable items and ranks them with SS/S/A/B/C levels before detailed reporting.
- A five-minute independent test task was requested and created separately from the main daily news task.
