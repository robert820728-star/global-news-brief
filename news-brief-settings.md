# News Brief Settings

## Purpose

Track the user's daily news brief rules in a versioned text file so future changes can be reviewed and restored from git history.

## Schedule

- Main daily news brief: keep the existing official scheduled task unchanged unless explicitly requested.
- Independent tests: create separate tasks when requested. Do not merge, pause, modify, or otherwise interfere with existing news tasks unless explicitly requested.
- Time window: each run should judge news from the actual execution time looking back 24 hours.

## Output Format

Every brief must be divided into exactly three top-level blocks, in this order:

1. `今日總覽`
2. `逐條詳報`
3. `後續觀察`

Do not collapse these three blocks into a single continuous list. Do not replace the third block with scattered comments inside each item.

### Block 1: 今日總覽

Start each brief with a severity summary before the detailed news items.

The severity summary should:

- State how many news items are worth noting today.
- Group items by severity level when useful.
- Use a vertical bullet list or short grouped list where each selected event appears on its own line. Do not compress multiple event titles into one paragraph or one comma-separated sentence.
- Prefer the readable pattern:
  - `S`
  - `荷姆茲/紅海航運與能源供應風險升高`
  - `A+`
  - `剛果民主共和國伊波拉病例與死亡數續升`
- A compact inline form such as `Russia-Ukraine war escalation - A` is allowed only for very short briefs with fewer than five selected items.
- Keep the list factual and avoid exaggeration. Upgrade severity only when evidence supports wider impact, rapid escalation, cross-border spread, systemic risk, or unusually high casualties.

### Block 2: 逐條詳報

After the overview, provide the selected news items using the standard item structure.

Severity levels:

- `SS`: Extreme global/systemic crisis risk, such as multiple major wars merging, several great powers being pulled in, or a plausible near-term world-war scenario.
- `S`: Severe international or regional crisis, or a major structural turning point with realistic potential to redirect later history, research, industry, policy, security, or long-term development.
- `A`: Major event requiring attention, such as serious war escalation, multi-country disease spread, very high casualties, major disaster, or strategically important political/economic shock.
- `B`: Important but still limited event, such as a new fast-spreading disease before broad regional collapse, meaningful but contained conflict escalation, or a significant policy/economic event.
- `C`: Routine or low-signal event, such as ordinary seasonal outbreaks, isolated incidents, or minor updates. Include when it enters the scan result, but keep it short.

Severity should guide length:

- All selected levels should use the same item structure: title with grade, sources, details, optional positions, and analysis. Severity changes the depth and length, not the core format.
- Once an item is selected, it must have a clear reason why it is worth knowing. Grade only changes urgency and depth. Do not treat `C` as "unimportant"; treat it as "limited impact, but still worth noting."
- `C`: Do not omit once selected. Aim for about 50-100 Chinese characters when useful, enough to explain the basic beginning, development, and why it remains low-priority. `C` items may be grouped only when they are closely related routine updates, but each event still needs a concrete explanation. Do not reduce interesting low-severity items to a bare one-line label.
- `B`: Do not omit once selected and do not reduce to a table-only summary. Treat each `B` item as a real news item with sources, details, and analysis. For disasters, attacks, public safety incidents, major weather events, disease outbreaks, and market-moving economic news, compare multiple sources when available and include key figures such as deaths, injuries, affected regions, damage, or official estimates.
- `A`: Give enough context to understand scale, trend, affected stakeholders, uncertainty, and likely next developments.
- `S`: Explain clearly with sources, affected countries or sectors, escalation paths, uncertainty, and practical reasons to keep watching. If the topic matches the user's interests or may develop quickly, suggest creating a separate monitoring task.
- `SS`: Treat as a top-level crisis brief. Be explicit about evidence, uncertainty, possible scenarios, and why this crosses from severe news into systemic global risk. Suggest independent monitoring unless the user has already declined it.

High-impact but unverified claims:

- Severity measures how urgently the item deserves attention, not only how certain it already is.
- A claim may be rated `S` when it is still unverified if the potential impact is world-changing, the claim is technically plausible enough to merit serious review, and independent verification is actively developing.
- Always label such items as unverified, uncertain, or awaiting replication. Do not write as if the claim is already true.
- If evidence weakens, downgrade from `S` to `A` or `B`, but still report the downgrade as important when the claim itself changed markets, research priorities, public policy, or scientific understanding.
- If disproven, treat the debunking as a meaningful follow-up rather than pretending the event was never important.
- Example: an LK-99-like room-temperature superconductivity claim can start as `S` while the world is trying to replicate it, then move to `A/B` as replication fails, and later become a concise but important postmortem about scientific replication and material misidentification.
- If an LK-99-like claim or comparable "holy grail" breakthrough is independently confirmed by multiple credible teams and points toward reproducible application, upgrade to `SS`. Confirmed room-temperature ambient-pressure superconductivity would qualify because it could reshape energy systems, electronics, magnets, transportation, medical imaging, and major scientific infrastructure.

Milestone and structural turning-point events:

- `S` may apply when an event has credible potential to become a structural turning point: something later analysis may treat as a before/after marker, even if the practical effects take years to unfold.
- This includes confirmed or strongly credible breakthroughs in mathematics, physics, computing, biology, energy, space infrastructure, medicine, geopolitics, or security when they may redirect major research programs, industries, state strategy, or civilization-scale development.
- Example: a proof of the Riemann Hypothesis may be `S` because it would be a foundational mathematical milestone with possible downstream effects across number theory, cryptography, computation, and theoretical science, even if ordinary daily life does not change immediately.
- Do not downgrade a turning-point event only because it is abstract, academic, or slow-moving. Grade by long-term structural impact, not only immediate casualties, money, or visible chaos.
- Still avoid hype: if a claimed milestone is weak, vague, or not accepted by relevant experts, label the uncertainty clearly and downgrade as evidence weakens.

Scope-adjusted severity:

- Use three reporting scopes: global/international, China-Taiwan/national, and local/regional. The smaller the scope, the lower the threshold for `A` or `S`, because a smaller event can still materially affect a country, province, city, or the user's daily life.
- Global/international scope should keep stricter thresholds. A single-country disaster outside Taiwan or China is usually `B` unless casualties, economic impact, diplomatic consequences, supply chains, migration, energy, finance, or regional stability make it broader.
- China-Taiwan/national scope can use more flexible thresholds. `S` may mean a turning point for Taiwan or China, not necessarily the whole world. `A` may include major disasters, serious public safety events, national-level technology or economic developments, major policy changes, or high-risk criminal cases with broad public concern.
- Local/regional scope should prioritize direct relevance and disruption. Events in Taiwan, China, and especially Jiangsu-Zhejiang-Shanghai should be weighted higher than comparable events elsewhere because the user lives and works around Suzhou.
- Disease outbreaks should be graded by scope. Cross-province spread in China or cross-county/city spread in Taiwan can justify `A` or `S-` if growth is fast, containment is uncertain, or healthcare/public order impact is significant, even if the same scale would be lower globally.
- Major disasters should be graded by both casualty scale and relevance. Examples such as the 921 earthquake, the Sichuan earthquake, or the Weiguan Jinlong building collapse may be `A` or higher in China-Taiwan/national scope. A large earthquake affecting only one foreign country may be `B` unless wider impacts emerge.
- High-technology, industrial, or economic developments in Taiwan or China may be upgraded when they affect national competitiveness, semiconductors, advanced manufacturing, energy, exports, employment, capital markets, or long-term strategy.
- Major criminal cases may be upgraded when they involve unusual violence, public safety risk, systemic failure, cross-region effects, major social fear, or policy consequences. Avoid sensational wording; explain the public-risk reason for the grade.
- Deaths or major health events involving former or current top national leaders should be included for the directly relevant country edition. For China, the death of a former premier, Politburo Standing Committee member, president, party general secretary, or equivalent national leader is at least `B` in the China/Taiwan-national scope, because it has historical, political-memory, elite-politics, and official-narrative significance even when no immediate policy change follows.
- Major Taiwanese corporate transactions should be included when they affect listed companies, large market value, control rights, telecom, finance, technology, IT services, semiconductors, infrastructure, employment, or national competitiveness. Public tender offers or control-seeking acquisitions of major listed companies are usually at least `C`, and can be `B` when the transaction size, market structure, or strategic sector impact is meaningful.
- Taiwan cultural, media, internet, creator-economy, film, television, or entertainment-sector events should be included when they mark the cancellation, shutdown, transformation, or funding stress of a widely recognized institution, award, platform, festival, or public figure's project. These are often `C`, but not filler when they reveal structural pressure in media, sponsorship, creator economics, or public culture.
- Assassination threats or credible security threats against a sitting head of state, especially a U.S. president, Chinese leader, Taiwanese president, Japanese prime minister, or other major-power leader, are usually at least `B` even if the attack does not occur. Upgrade to `A` or higher when the threat involves a state actor, military weapon, secret evacuation, aircraft security, congressional oversight, cross-border escalation, or active conflict.
- Military force used against ships, aircraft, bases, or personnel in an active crisis zone is usually at least `B`, and may be `A` or `S` when it affects major shipping lanes, energy routes, blockade enforcement, civilian vessels, casualties, or risk of state-to-state escalation.
- Taiwan-adjacent military activity involving China plus a third country's forces should usually be at least `B` in Taiwan/China scope and can be `A` when it occurs east of Taiwan, around sensitive approaches, during Taiwan military exercises, or when it suggests normalization of foreign participation in China's Taiwan-area military narrative.

Repeated or overlapping regional impact:

- For typhoons, floods, heat waves, cold waves, disease waves, transport disruption, and similar repeated-impact events, avoid repeating the same basic explanation for every affected region.
- Choose one main affected region for detailed explanation based on severity, user relevance, population, infrastructure, or economic impact. Summarize other affected regions briefly in the same item.
- If Jiangsu-Zhejiang-Shanghai is affected, mention it clearly and raise practical relevance, especially for transport, work, safety, travel, supply chains, and local public services.

Tone:

- Keep the news brief professional, objective, and source-grounded. The user's informal metaphors are for internal calibration only; do not reproduce them as the brief's public style.
- It is acceptable to write with urgency when facts justify it, but avoid dramatic, apocalyptic, or exaggerated wording.
- Prefer terms such as "structural turning point", "systemic risk", "national-level impact", "regional disruption", "public safety risk", and "long-term strategic impact".

Disease outbreak severity:

- Do not grade disease severity by fear alone. Consider transmission mode, fatality risk, healthcare burden, public health capacity, border spread, local compliance, contact tracing feasibility, vaccine or treatment availability, and whether spread is accelerating despite containment.
- Ebola crossing into another country is usually `A+` or `S-`: it is highly dangerous and politically significant, but it does not automatically become `S` if the receiving country has strong isolation, contact tracing, healthcare capacity, and public cooperation.
- Upgrade Ebola or similar high-fatality outbreaks to `S` when cross-border chains keep expanding, healthcare systems are overwhelmed, multiple countries report sustained local transmission, or containment measures are visibly failing.
- Upgrade to `SS` only if a high-fatality outbreak becomes broadly international, containment breaks across several regions, or the pathogen changes in a way that materially increases transmissibility while retaining severe outcomes.
- Downgrade when imported cases are isolated quickly, contacts are traced, and no sustained local transmission appears. Still report the event because the downside risk is large even when the most likely outcome is containment.

Space program severity:

- Do not rate every space launch highly. Routine satellite launches, resupply missions, or crew rotations are usually `C` or `B` unless tied to a larger strategic shift.
- A new or competing space station is important, but because the International Space Station already exists as precedent, station construction or completion is usually `A` unless it changes the global research or geopolitical order.
- `S` and `SS` require milestone value, not just a large topic. The event should plausibly become a historical marker that later research, industry, policy, or geopolitical competition builds on.
- Artemis-level lunar return programs, China's lunar base or "Moon Palace"-level plans, or other national programs aimed at sustained lunar presence may be `A` at announcement because they signal a major strategic direction.
- The start of construction, successful assembly, or completion of a sustained lunar base, lunar orbital infrastructure, or comparable off-Earth habitation system may be `S`.
- Semi-permanent or permanent off-Earth bases, especially lunar bases with long-duration habitation or resource use, may be `SS` when they plausibly mark a civilization-level expansion of human infrastructure.
- Crewed Mars mission announcements may be `A` if still programmatic, `S` when serious construction or launch preparation begins, and `SS` for actual crewed Mars launch, landing, sustained operation, or credible permanent settlement steps.
- After a milestone is achieved, routine follow-up research should be graded on its own impact. For example, ordinary lunar soil studies after a lunar base is established are usually `A` or `B`, not automatically `S`, unless they produce a major discovery, resource breakthrough, or strategic shift.
- Downgrade if the plan is vague propaganda, aspirational funding language, or lacks technical milestones. Upgrade only when funding, hardware, launch schedule, international alignment, or construction progress makes the shift concrete.

Each selected news item in `逐條詳報` should use these sections, in this order:

1. Title
2. Sources
3. Details
4. Positions
5. Analysis

If there are no meaningful competing positions, stakeholder differences, or useful angles to compare, omit the Positions section entirely.

### Block 3: 後續觀察

End each brief with a concise follow-up block.

The follow-up block should:

- List events that deserve continued monitoring, especially `S`, `A`, fast-moving `B`, and unusual `C` items with possible legal, market, technology, public safety, or geopolitical follow-through.
- State what would make each monitored item upgrade, downgrade, or disappear from future briefs.
- Keep it concise. This is not a second full analysis section.
- If nothing needs follow-up, explicitly say there are no notable follow-up items.

Low-severity handling:

- The brief must distinguish between "no B/C items found" and "B/C items found."
- If any `B` or `C` items are selected, list them explicitly in the severity summary.
- `B` items should normally appear as individual detailed items using the standard item structure. Do not use a separate "B summary table" as the only treatment.
- `C` items may be grouped when several are genuinely minor and closely related, but the grouped entry must still give each event enough explanation, usually about 50-100 Chinese characters when the item has an interesting origin, development, business angle, legal angle, technology angle, or consumer impact.
- Do not silently drop `B` or `C` items merely because higher-severity items exist.

## Selection Notes

- Prioritize genuinely important Taiwan, China, and international event news.
- Include entertainment, film, television, documentaries, or cultural items only when they are exceptional, highly influential, or useful for serious discussion.
- Avoid filler items added only to satisfy a category.
- Duplicate coverage is allowed for independent test tasks; each task should judge importance on its own.

Broader source scanning should not lower the selection bar:

- Expanding the source pool is for discovery, not for padding the brief.
- A scanned item should be selected only when it has a clear reason to be worth knowing: public safety, governance, geopolitics, national or regional relevance, major company or market impact, industry structure, technology/security implications, cultural significance, or an unusually revealing social signal.
- Do not include ordinary celebrity updates, routine product releases, minor stock moves, isolated local incidents, routine corporate announcements, or low-context social-media chatter unless they reveal a broader pattern or affect a relevant public, market, cultural, or safety question.
- If the only reason to include an item is that a source published it, omit it.
- If the item is interesting but low-impact, include it as `C` only when the brief can explain why it is worth knowing and why it stays low-severity.
- Keep the brief selective. A wider scan should improve recall of important or interesting items, not turn the output into a general news feed.

## Current Confirmed State

- The news brief format was updated to include Title, Sources, Details, Positions, and Analysis.
- Positions should be omitted when not useful.
- Each brief should begin with a severity summary that counts notable items and ranks them with SS/S/A/B/C levels before detailed reporting.
- B/C items should use the same core format as A/S. B items are individual news items; C items may be grouped only when genuinely minor and related.
- C items may use about 50-100 Chinese characters when useful so their context and significance are clear, even though they remain low-severity.
- A five-minute independent test task was requested and created separately from the main daily news task.
