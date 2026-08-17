# Run Identity Binding Design

## Purpose

Prevent an older fourteen-day list or intermediate reader from being mistaken for the current canonical edition. Every scheduled execution receives one human-readable, collision-resistant identifier and every release-facing artifact must bind to it.

## Identifier

The canonical format is `gnb-YYYYMMDDTHHMMSSZ-xxxxxxxx`, where the timestamp is the UTC executor-start time to the second and the suffix is eight lowercase hexadecimal characters generated from four cryptographically secure random bytes. Example: `gnb-20260817T102800Z-6a82b2e0`.

Timestamp alone is not sufficient because retries or parallel dispatches can begin within the same second. The random suffix is not a secret; it only prevents collisions.

## Binding

The same `run_id` must appear in the mobile run log, checkpoint, latest candidate-audit run, final manifest, reader identity block, release receipt, and immutable run-log snapshot. The final manifest also records the exact 40-character `main_sha`. The publisher fails closed when any identity differs or has an invalid format.

The reader begins with the date followed by three identity lines: execution id, full source commit, and formal-release status. This makes screenshots and copied lists self-identifying without exposing backend diagnostics.

Historical candidate-audit runs retain their original ids. Only the latest audit run is required to equal the current release identity.

## GitHub Ledger

The watchdog generates the identifier through a repository script rather than shell string assembly. `logs/current.json` retains the same id for the whole execution. Before publishing, the publisher validates the current ledger and saves an immutable snapshot inside the release directory; later ledger stage updates therefore do not invalidate the receipt.

## Failure Rules

- Invalid or missing run id: stop before publication.
- Manifest, checkpoint, audit, or run-log id mismatch: stop and name the mismatching artifact.
- Manifest and run-log main SHA mismatch: stop.
- Reader identity block missing, duplicated, stale, or marked non-final: stop.
- A release receipt whose snapshot or reader identity no longer matches: delivery is blocked.

## Test Strategy

Tests first prove that legacy ids are rejected, same-second ids remain unique, stale manifest or run-log identities block publication, and reader text without the exact identity block fails. The complete suite and capsule verification then guard cross-platform scheduled execution.

## Disaster and Disease Grade Ceiling

The same release also records the clarified absolute scale. Death toll alone may raise a disaster or disease event to A at 2,500 confirmed deaths, but cannot raise it above A. A+ requires separate evidence such as unusually rapid transmission, a Risk Group 4 pathogen combined with material control difficulty, or another major external escalation factor. Risk Group 4 classification alone is permissive evidence, not an automatic upgrade; transmission route and realistic spread potential remain material.

S- or higher requires a global pandemic that meets the existing world-scale definition: credible potential to change the world, become a global turning point, or create civilization-scale or extinction-scale danger. COVID-19 global lockdowns are the reference case for S-. Ordinary high-casualty events cannot reach S through death toll alone.
