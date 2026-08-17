# Local Disaster Publication Threshold Design

## Goal

Prevent ordinary local disasters and accidents from entering the reader edition merely because a few people died, while preserving explicit exceptions for extreme scope, critical-system impact, and conflict escalation involving monitored regions.

## Decision order

1. Military and conflict events remain governed by the existing border-conflict and ongoing-conflict rules. The casualty threshold in this design must not replace those rules.
2. For an ordinary single-country local disaster, accident, or public-safety event with no special significance:
   - 0–49 confirmed deaths: below C and excluded from the reader edition.
   - 50–99 confirmed deaths: C.
   - 100–249 confirmed deaths: B.
   - 250 or more confirmed deaths: A-.
3. A sub-50 event may be regraded only when it has verified special significance. Examples include, but are not limited to: monitored-region conflict escalation risk; an extreme abnormal number of missing, seriously injured, or evacuated people; large-scale medical, electricity, transport, or other public-system disruption; a disaster that is demonstrably expanding rapidly; multinational direct impact; a rare disaster mechanism; clear regulatory failure or systemic risk; mass housing or critical-infrastructure loss; historic extreme scale; or another event-specific trigger supported by verifiable direct consequences.
4. Location in a monitored region, media attention, warning coverage, or dramatic imagery is not by itself special significance.

## Enforcement

Each newest-run candidate carries a compact `local_disaster_review`. Non-applicable candidates need only `{"applies": false}`. Applicable candidates record confirmed deaths, structured exception triggers, and an adjustment reason. The validator derives the baseline grade from the four bands above. The baseline applies normally; an upward change must explain the event-specific reason and provide at least one verified special-significance trigger. Downward changes are not a routine editorial option and are reserved for corrected figures, unreliable core facts, or clear misclassification, with a concrete reason. `other_verified_special_significance` keeps the exception list open without allowing unsupported claims. The audit validator rejects unexplained deviations and attempts to classify an already identified conflict as a local disaster.

Existing fourteen-day history remains readable; the new field is enforced on the newest run so older retained runs do not block migration.

## Calibration cases

- Ordinary non-core local accident, 49 deaths, no special trigger: below C.
- Ordinary local accident, 50–99 deaths, no special trigger: C.
- Ordinary local accident, 100–249 deaths, no special trigger: B.
- Ordinary local accident, 250 or more deaths, no special trigger: A-.
- 2014 Sewol ferry disaster: 304 confirmed deaths establish an A- baseline; failed rescue, regulatory failure, and systemic institutional risk support an explained upward adjustment to A.
- 2022 Itaewon crowd crush: A- is supported by the rare mechanism, national investigation, accountability, and lasting public-safety implications, not death count alone.
- 2026 Spokane complex fires: a sub-50/zero-death exception is supported by tens of thousands evacuated, mass structure loss, and historic city-scale impact.
- A low-casualty event that credibly risks military or other conflict in a monitored region: exempt from the ordinary local-disaster threshold and evaluated under the existing conflict rules.
- A grade above or below its casualty baseline is allowed only with a concrete adjustment reason; upward adjustment additionally requires verified special significance.

## Scope boundary

No change to source collection, the six shortlist scores, C-or-higher reader inclusion, image handling, maps, or the existing military/conflict definitions.
