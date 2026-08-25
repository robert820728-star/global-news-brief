# Install Contract, Discovery Pool, and Media Capability Implementation Plan

> Execute directly in the current approved scope. Do not delegate.

**Goal:** Remove the obsolete fixed-source contract, make `INSTALL.md` the complete operating entry, and permit evidence-complete mobile-native runs to complete when native-media attachment capability is unavailable.

**Architecture:** Keep discovery configuration route-based, keep verification event/claim-role based, and represent delivery capability independently from terminal run status. Update machine contracts first, then align all active prose and regenerate the verified runtime capsule.

---

### Task 1: Lock the active contract with failing tests

**Files:** `tests/test_pipeline_contract.py`, `tests/test_manage_candidate_audit.py`, `tests/test_manage_mobile_run_log.py`, `tests/test_publish_news_brief.py`, relevant source-route tests.

Add assertions for discovery-only configuration, no active fixed-source keys/profile, archive-first GDELT acquisition, all nine skills and correct reader skeleton in `INSTALL.md`, bootstrap/checkpoint order, same-source fallback order, and completed `mobile-native` capability degradation. Run the targeted tests and retain the expected failures.

### Task 2: Remove fixed-source configuration and code dependencies

**Files:** `news-source-pool.json`, `source-health-profile.json` (remove), `source-route-config.json`, `scripts/manage_candidate_audit.py`, `scripts/build_source_candidate_list.py`, `scripts/materialize_source_scans.py`, `scripts/recover_same_source_leads.py`, `scripts/validate_source_scan_evidence.py`, and affected tests.

Delete legacy fixed-source fields/profile. Validate only configured discovery routes. Keep event verification source arrays unchanged because they are evidence records, not a fixed pool. Run source, audit, scan, and publisher fixture tests.

### Task 3: Implement capability-degraded mobile completion

**Files:** `schemas/mobile-run-log.schema.json`, `scripts/manage_mobile_run_log.py`, `scripts/validate_news_brief.py`, `scripts/publish_news_brief.py` if required by the declared full-runtime/mobile-native boundary, and affected tests.

Add delivery-profile and native-media-status metadata with backward migration. Permit `mobile-native` completion with saved reader/audit artifacts and a non-error `NATIVE_MEDIA_UNAVAILABLE` capability limitation. Keep full-runtime attachment validation fail-closed. Ensure usable image evidence may be represented as verified-but-not-delivered only for the declared capability-degraded profile.

### Task 4: Align all active documentation and rebuild `INSTALL.md`

**Files:** `INSTALL.md`, `README.md`, active root prompts/configuration docs, all nine active skill files, `bootstrap-workspace.md`, `docs/mobile-run-ledger.md`, template/preferences where contract wording overlaps.

Remove fixed-source wording, resolve GDELT and fallback-order conflicts, correct skill counts and reader format, document both execution profiles, and add complete stage/artifact/validator/recovery matrices. Historical dated documents and the version record remain historical.

### Task 5: Verify and package

Run targeted tests with the bundled Python runtime, then the full suite. Scan active files for fixed-fifteen residues and contradictory media blockers. Update the bilingual version record, commit source changes, rebuild the bootstrap capsule against that source commit, verify payload/blob identity from a clean exported tree, and commit the generated capsule. Do not push without explicit publication authorization.
