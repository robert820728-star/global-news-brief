# Policy Governance Evidence Gate Design

## Goal

Prevent a public-policy, regulatory, platform-governance, or cultural-industry event from being scored as a superficial controversy before the system has established the underlying institutional event and reconciled that identity with all six scoring dimensions.

## Problem

The current audit requires structured grading evidence and six non-empty dimension-evidence strings, but a syntactically complete candidate can still omit the decisive institutional facts. A model can describe public reaction, assign a low grade, and pass validation even when the evidence also contains an official legal interpretation, an enforcement referral, operational platform changes, cross-agency supervision, or a rule with spillover beyond one case.

The fix must not create a named-event exception or an automatic B-grade floor. It must improve event identity and evidence consistency for every jurisdiction and topic.

## Design

Add `POLICY_GOVERNANCE_EVIDENCE_GATE` after semantic event identity and region/time identity, but before final six-dimension scoring.

Every latest-run candidate must include `grading_evidence.policy_governance_review`. Non-policy events use `{ "applies": false }`. Applicable events must record:

- evidence-backed trigger types;
- legal or regulatory basis;
- official actions;
- direct operational effects;
- affected actor classes;
- cross-agency effects;
- precedent or spillover scope;
- material effects inside the exact run window;
- source URLs;
- unverified allegations kept outside the verified event identity;
- a score-consistency review performed after the six scores are drafted.

The score-consistency review separately checks public impact, scope, structural significance, and current-window development. Any `contradiction` or `unresolved` result blocks audit completion and requires identity correction or rescoring. A strong governance profile that contains official action, actual operator/platform effects, and either cross-agency or spillover evidence may still finish below B, but only with an explicit evidence-based `why_not_b`. This is a challenge requirement, not a grade floor.

## Separation of Claims

Verified official action and operational effects belong to the core semantic event. Public reaction is supporting context. Historical accusations or alleged misconduct that lack reliable verification must be listed under `unverified_allegations`; they cannot be merged into the verified event identity, used as a direct consequence, or increase any dimension score.

## Validation

The latest-run validator will reject:

- a missing policy-governance review;
- an applicable review with no trigger, legal/official evidence, operational effect, window effect, or evidence URL;
- unverified allegations that are not explicitly separated;
- any score-alignment status other than `consistent`;
- a strong governance profile below B without an explicit `why_not_b` challenge;
- a review outcome other than `consistent`.

Historical runs remain readable because the new review is required only for the latest run. The JSON schema documents the structure without retroactively adding it to the global required list.

## Prompt and Runtime Integration

The gate must appear in the canonical settings, full scheduled prompt, mobile prompt, and `select-news-events` skill. The verified bootstrap capsule must be rebuilt so scheduled ChatGPT runs receive the same rule and validator as repository users.

## Tests

Regression coverage uses generic evidence states rather than a named news event:

1. A non-policy event with `applies=false` remains valid and receives no automatic grade change.
2. A strong governance event below B without `why_not_b` fails.
3. A strong governance event with internally consistent B-level scoring passes.
4. Unverified allegations that are not separated fail.
5. A contradiction in any score-alignment field fails and requires review.

## Out of Scope

- No automatic grade floor.
- No keyword-to-score mapping.
- No change to the fixed score-to-grade bands.
- No special rule tied to a particular organization, work, country, or user-preferred outcome.
