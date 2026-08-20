# GDELT-Resilient Full Candidate Pool Design

## Goal

Keep GDELT as the primary broad discovery source without allowing a transient DOC API failure to stop publication, and pass every verified article in the 24-hour window from GDELT, CNA, and China News Service into deduplication. No discovery source may discard candidates through a fixed per-source ranking limit.

## Decision

The user explicitly requires continuous publication:

- GDELT remains the primary aggregator; CNA and China News Service remain regional supplements.
- HTTP 429 and other transient DOC API failures use bounded retries and respect `Retry-After`.
- If the DOC API remains unavailable, acquisition switches to GDELT's official 15-minute export archives for the 24-hour window.
- If both live GDELT interfaces are unavailable, the run records the exact degraded state, may reuse the most recent valid GDELT snapshot when present, and continues publication with available verified candidates.
- Supplements never masquerade as current GDELT coverage; degraded acquisition is explicit in route coverage and the run audit.
- Every verified in-window item from each successful discovery route enters the candidate pool. There is no fixed top 30, top 100, or other arbitrary discovery cutoff.

## Alternatives rejected

1. Stop publication whenever the DOC API returns 429. Rejected because an interface-level rate limit must not suppress the daily brief.
2. Silently treat CNA and China News Service as equivalent to GDELT. Rejected because the audit must preserve the difference between broad aggregator coverage and regional supplements.
3. Add an unrelated generic web-search source. Rejected for this change because GDELT already exposes an official archive fallback.

## Data flow

1. `fetch_source_routes.py` fetches the DOC API with bounded retries.
2. On continued DOC API failure, it materializes the same GDELT source from official 15-minute export archives.
3. If live GDELT remains unavailable, route coverage records cache or unavailable state and the command remains executable when another discovery route is ready.
4. `materialize_source_scans.py` preserves the complete ranked list and marks every ranked URL as selected for the candidate pool.
5. `build_source_candidate_list.py` consumes all verified in-window scan items from every successful source.
6. Deduplication and final evidence-based six-dimension grading occur after the complete pool is built.

## Error handling

- A DOC API 429 records its status and retry history, then triggers the official-export fallback.
- A live GDELT failure after all fallbacks produces `status=degraded`, never a false `ready` claim.
- Publication continues from all verifiable candidates, while the audit preserves GDELT acquisition mode, archive coverage, and any cache age.
- The run fails only when no discovery route yields any verifiable candidates.

## Acceptance tests

- A 429 response respects `Retry-After` and retries before fallback.
- A continued DOC API failure switches to the official GDELT export archive and remains publishable.
- When every GDELT interface is unavailable but a supplement succeeds, route coverage is degraded and publication remains executable.
- A scan with more than 30 in-window items selects all ranked URLs for the candidate pool.
- Candidate-audit validation rejects any successful source whose selected URL count differs from its complete ranked count.
- Prompt, skill, and configuration surfaces no longer describe per-source top-30 selection or a one-route minimum.

## Scope boundary

This change modifies discovery resilience, retries, GDELT archive fallback, complete candidate transfer, validation, guidance, tests, and version records. It does not change final grading weights, event verification, images, scheduling, or GitHub publishing.
