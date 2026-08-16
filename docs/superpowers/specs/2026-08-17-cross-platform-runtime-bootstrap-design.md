# Cross-Platform Runtime Bootstrap Design

## Goal

Keep the verified repository capsule workflow executable on Windows, Linux, and macOS without allowing an unverified PATH Python to run the news pipeline.

## Chosen architecture

Use standard-library Python as the single canonical scheduled path on every host. `python3` launches `resolve_bundled_python.py`; the returned verified bundled Python then runs `fetch_source_routes.py` and the remaining pipeline. Existing PowerShell source files remain only for repository history and are excluded from the schedule, active tests, and runtime capsule.

The resolver candidate order is: explicit host-provided path, `CODEX_BUNDLED_PYTHON`, runtime-root environment variables, then platform-specific Codex cache locations. Every candidate must exist and successfully execute a Pillow import probe. PATH Python may launch the Unix resolver but cannot become the returned pipeline runtime unless it is explicitly supplied or found in the bundled-runtime locations.

The Python route fetcher preserves the PowerShell contract: date-template expansion, redirects, gzip/deflate decoding, exact snapshot bytes, SHA-256, per-route result records, `source-route-coverage.json`, compact JSON stdout, and nonzero exit when any route is not ready.

## Alternatives considered

1. Use Python as the scheduled path everywhere and retain PowerShell only as legacy compatibility. This is selected because the user runs updates from mobile, the scheduled host already has `python3`, and PowerShell is unavailable there.
2. Dispatch by OS and keep PowerShell canonical on Windows. Rejected because the user's workflow never runs the schedule on a Windows PC and the extra branch adds no value.
3. Add Bash and PowerShell wrappers around shared programs. Rejected because it adds another platform layer without improving verification.

## Capsule and CI

Both new Python programs are runtime files under `scripts/`, so the deterministic capsule must include them and be rebuilt. Capsule tests explicitly assert their presence. The GitHub workflow compiles both programs and runs resolver, route-fetcher, capsule, and checkpoint tests on Ubuntu. PowerShell programs are excluded from the active test and runtime closure.

## Failure behavior

The resolver prints one JSON object on success and diagnostic text on stderr on failure. It never silently falls back to an unverified PATH runtime. The route fetcher records each failed route and exits 1 when coverage is incomplete. The schedule reports the existing Stage -1 blocker only after the correct platform resolver has exhausted valid bundled-runtime candidates.

## Acceptance

- A host-provided bundled Python path wins over fallback candidates.
- A candidate without Pillow is rejected.
- The schedule resolves a bundled runtime and fetches routes without PowerShell on every host.
- The rebuilt capsule verifies and contains both Python programs.
- Ubuntu CI compiles and tests the cross-platform paths.
