# Public Value V2 Scoring Design

## Status and scope

This design implements `public_value_v2.0` as the only active scoring contract. It preserves the current dimension weights and grade bands while changing each dimension to a normalized 0–100 evidence scale. V2.1 shadow comparison, the candidate 30/20/15/15/15/5 weighting, and grade-band recalibration are explicitly out of scope.

The user-provided scoring proposal is the approved product specification for this design. The implementation proceeds under the existing standing execution authorization.

## Considered approaches

1. **In-place V2 contract migration — selected.** Bump configuration and schema versions, migrate fixtures, and make V2 the sole formal scoring result. This avoids two competing authoritative grades and gives validators one deterministic contract.
2. **Dual V1/V2 runtime.** Keep V1 formal while producing a V2 shadow score. This is appropriate for V2.1 calibration but would duplicate schema, publisher, and reader answers before the evidence gates are proven.
3. **Compatibility adapter around V1 scores.** Convert old bounded dimension points to percentages. This preserves old data but cannot enforce realized-versus-potential evidence, fact references, or high-score challenges and therefore does not meet the objective.

## Configuration contract

`news-source-pool.json.ranking` becomes `public_value_v2` and is the single source of truth for:

- Six normalized dimensions, each with `minimum=0`, `maximum=100`, and weights `30/20/15/15/10/10`.
- Allowed score increment of 5. Multiples of 10 are anchors; midpoint values are allowed only with evidence placing the event between adjacent anchors.
- Existing grade minimums: C 45, C+ 50, B- 55, B 60, B+ 65, A- 70, A 75, A+ 80, S- 85, S 90, S+ 94, SS 97.
- Dimension anchors, casualty public-impact floors, high-score threshold 70, cross-dimension reuse threshold 3, material-update delta threshold 70, and confidence bands.

Python must read weights and thresholds from this configuration. Grade bands remain code-visible only as a checked fallback; configuration and code must be equal or validation fails.

## Score calculation

Each dimension is a number from 0 through 100 in increments of 5. The weighted importance score is:

```text
public_impact * 0.30
+ geographic_or_population_scope * 0.20
+ urgency_and_safety * 0.15
+ structural_or_policy_significance * 0.15
+ material_new_development * 0.10
+ core_section_relevance * 0.10
```

The result is rounded to two decimal places and stored in both `importance_score` and `weighted_score`. The two fields must match. The existing grade mapping applies to this weighted result.

## Evidence model

Every candidate contains an `evidence_facts` array. Each fact has a unique `fact_id`, non-empty fact text, evidence type, consequence class, and one or more source URLs. Consequence classes are `realized`, `ongoing`, `potential`, or `speculative`.

`consequence_evidence` groups fact IDs into the same four classes. Every referenced ID must exist, and each fact's declared consequence class must match the group that references it.

`dimension_evidence` maps each scoring dimension to one or more fact IDs, replacing free-form dimension text as the scoring authority:

- Public impact, direct scope, and urgency may reference only realized or ongoing facts.
- Structural significance may reference realized, ongoing, or potential facts, but potential facts require high confidence and a concrete institutional mechanism.
- No dimension may reference speculative facts.
- Material update must reference a `delta_fact` when its score is at least 70.
- Core relevance measures centrality to the monitored section; mere classification into TWN, CHN, or GLB is insufficient evidence.

If one fact supports three or more dimensions, `cross_dimension_rationales` must contain a record for that fact listing the reused dimensions and explaining the distinct causal contribution. This allows legitimate reuse but rejects unreasoned multi-dimensional score inflation.

## Actual, potential, and policy maturity

Policy-like candidates contain `policy_stage` with one of:

`rumor`, `consideration`, `proposal`, `draft`, `introduced`, `passed`, `signed`, `effective`, `implemented`, `measurable_effect`, or `not_applicable`.

There is no stage-based hard score cap. A proposal may have high realized impact if the evidence facts demonstrate an impact that has already occurred. Future or hypothetical effects remain potential and cannot support public impact, direct scope, or urgency.

The existing `policy_governance_review` remains required when applicable and must agree with `policy_stage`, realized operational effects, and the referenced facts.

## Material delta

`delta_facts` contains structured transitions with `fact_id`, `previous_state`, `current_state`, `why_material`, and evidence URLs. A material-update score of 70 or more requires at least one referenced delta fact. A new article, new wording, or background summary without a state transition cannot support a high material-update score.

## High-score challenge

Every dimension score of 70 or more requires one `high_score_challenges` entry with:

- the dimension;
- the high-score claim;
- a counter-question;
- supporting fact IDs;
- outcome `sustained` or `rescore_required`;
- a non-empty rationale.

Only `sustained` is valid for a completed score. Supporting facts must be eligible for that dimension.

When weighted score is 70 or more, `overall_high_score_challenge` is required. It must state what evidence distinguishes the assigned grade from B+, cite fact IDs, and have outcome `sustained`. If the evidence cannot identify that distinction, the candidate must be rescored below A- or remain provisional.

## Evidence confidence and grade status

`evidence_confidence` is an independent integer from 0 through 100 and does not alter importance. `confidence_band` is derived as high 80–100, medium 60–79, or low 0–59.

`grade_status` is `unscored`, `provisional`, or `validated`:

- `unscored` has no formal grade and cannot be selected.
- `provisional` may remain in the candidate pool but cannot map to a reader event.
- `validated` requires event identity, temporal review, fourteen-day continuity status, dimension facts, applicable policy review, score math, grade mapping, high-score challenges, and zero unresolved article dispositions.

Reader and manifest publication accept only `validated` candidates. Discovery coverage degradation or deferred durable-history maintenance does not by itself force a grade to provisional; missing evidence needed by a listed validation gate does.

## Manifest and publisher

The event manifest stores:

- `scoring_method=public_value_v2`;
- `validated_importance_score`;
- `validated_grade`;
- `grade_status=validated`;
- `evidence_confidence` and `confidence_band`.

Publisher validation requires exact equality between the latest candidate-audit mapping and these manifest fields. It rejects provisional or unscored candidates from the reader.

## Regression fixtures

`tests/fixtures/grading-cases.json` contains calibrated cases with expected score ranges and grade ranges:

1. A newly proposed nationwide law with no realized nationwide effect: structural may be high; impact and scope remain low to medium; grade cannot inflate to A solely from potential reach.
2. The same law after effective implementation and measured enterprise effects: realized impact and scope can rise.
3. A warning that a vessel may be seized with no disruption: structural high, urgency medium, impact medium or lower.
4. An actual seizure with shipping disruption and abnormal oil prices: realized consequences support higher scores.
5. Seven routine PLA vessels with no material change: D.
6. One hundred confirmed deaths, 180,000 evacuations, and active rescue: A through A+ when the full weighted evidence supports it.

Fixtures are validator calibration records, not a model inference service. Tests verify ranges, required facts, and rejection of known inflation patterns.

## Error and migration behavior

V1 candidate artifacts are not silently accepted as V2. Historical V1 runs remain traceability records; new formal runs must use V2. A mobile or degraded run may save provisional candidates, but only validated current-run events can enter the manifest or reader.

Validation errors identify the exact candidate, dimension, fact, and failed gate. The system repairs only the scoring/audit stage and must not rerun discovery when source rows and event identity are unchanged.

## Acceptance criteria

- Configuration, schema, validator, manifest, publisher, prompts, skills, settings, INSTALL, examples, and version records name one active V2 contract.
- Six scores are normalized 0–100 in increments of 5 and weighted from configuration.
- Potential and speculative facts cannot inflate actual impact, scope, or urgency.
- A score at or above 70 cannot pass without the required challenge and eligible facts.
- Material update at or above 70 cannot pass without a structured delta.
- Reuse across three or more dimensions cannot pass without a distinct rationale.
- Confidence remains independent of importance.
- Provisional grades cannot enter the manifest or reader.
- The calibrated fixtures and complete repository regression pass.
