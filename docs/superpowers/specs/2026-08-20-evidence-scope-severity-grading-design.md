# Evidence-Based Integrated Six-Dimension Grading Design

## Goal

Derive every candidate grade from the combined evidence across six weighted dimensions. Geographic scope informs one dimension; it is never a publication gate, grade ceiling, or exception system.

## Six dimensions

- `public_impact` (30): verified importance or severity, including casualties, serious injuries, essential-service interruption, binding rights or policy effects, irreversible loss, state-function loss, or existential consequences.
- `geographic_or_population_scope` (20): verified direct reach across people, first-level regions, countries, or public systems. Publication location, audience reach, warning coverage, official rank, and country size alone do not count.
- `urgency_and_safety` (15): current danger, time sensitivity, and need for immediate public action.
- `structural_or_policy_significance` (15): binding institutional, regulatory, constitutional, security, market-structure, scientific, or statehood change.
- `material_new_development` (10): verified change inside the current 24-hour window rather than repetition, commentary, or ceremony.
- `core_section_relevance` (10): direct relevance to the configured monitored sections.

Every dimension requires event-specific evidence. Keywords, official rank, company fame, media volume, or rhetorical importance cannot substitute for consequences.

## Integrated score and grades

The six scores sum to 0-100 and map directly to the final grade:

| Total | Grade |
|---:|:---|
| 97-100 | SS |
| 94-96 | S+ |
| 90-93 | S |
| 85-89 | S- |
| 80-84 | A+ |
| 75-79 | A |
| 70-74 | A- |
| 65-69 | B+ |
| 60-64 | B |
| 55-59 | B- |
| 50-54 | C+ |
| 45-49 | C |
| 40-44 | C- |
| 20-39 | D |
| 0-19 | E |

No single dimension has a hard ceiling on the final grade. A narrow event can still be highly graded when severity, urgency, structural consequences, current material change, and relevance supply enough verified points.

## Casualty and urgency integration

Conservatively confirmed deaths set a minimum evidence floor for `public_impact`, not a final grade: 1-9 deaths require at least 8 points, 10-49 at least 14, 50-99 at least 18, 100-249 at least 23, 250-2,499 at least 27, and 2,500 or more require 30. Other verified severity evidence may justify the same or a higher score within the 30-point limit.

`urgency_and_safety` remains independent: 0-3 means danger has ended or no immediate action is required; 4-7 means an active but bounded local response; 8-11 means continuing major danger, an open rescue window, or stressed essential services; 12-15 means an expanding or uncontrolled threat requiring broad immediate action. Death count alone never determines urgency, preventing the same evidence from being counted twice.

## Scope scoring anchors

Scope uses direct affected population and systems as well as geography:

- 0-3: individual, facility, ceremony, or no demonstrated direct public reach.
- 4-7: one locality or otherwise limited directly affected population.
- 8-11: a substantial part of one first-level region, an entire small sovereign state, or roughly two to three first-level regions/countries.
- 12-15: four or more first-level regions/countries, or material national public-system reach.
- 16-18: many first-level regions/countries across multiple regions.
- 19-20: global or civilization-wide direct reach.

The earlier Taiwan 2-3 county, China multi-province, and world multi-country examples are anchors for the scope component only. They do not automatically assign C, B, or any other final grade.

## Calibration cases

- A routine Chongqing mayoral appointment scores low on public impact, scope, urgency, and structural change; even with a current formal result, its combined example score is 25, grade D.
- A Taiwan event directly affecting three counties can reach C when the other dimensions bring the combined score to 45-49.
- A four-country event can reach B when its combined verified score is 60-64.
- A severe disaster in one small country can reach C through severity and urgency despite limited geography.
- Verified collapse of state functions can reach C+ or B through severity, urgency, scope across the national population, and structural consequences.
- An existential statehood, delisting, or habitability crisis can reach A without any exception flag.
- Destruction of Chongqing by a meteor can reach A or S through catastrophic severity, mass casualties, system collapse, urgency, and irreversible loss even though only one first-level region is directly hit.

## Data and validation

Each latest-run candidate stores `importance_score`, six-key `importance_breakdown`, and six-key `dimension_evidence`. Validation rejects missing evidence, out-of-range component scores, a total that differs from the components, or a grade that differs from the configured total-score band.

## Scope boundary

This change covers final candidate grading evidence, score-to-grade mapping, schema, configuration, guidance, tests, and version records. It does not change candidate discovery, GDELT fallback, fourteen-day merging, or image processing.
