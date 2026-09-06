import json
import tempfile
import unittest
import urllib.error
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts import hydrate_source_rows as hydration
from scripts import materialize_source_row_admissions as admissions
from scripts import remote_acquisition_bridge_v2 as bridge

MAIN_SHA = "a" * 40
RUN_ID = "gnb-20260906T000000Z-a1b2c3d4"
WINDOW = {
    "start": "2026-09-05T06:00:00+08:00",
    "end": "2026-09-06T06:00:00+08:00",
}
ROW_ID = "row-" + "1" * 24
CANONICAL = "https://www.cna.com.tw/news/aopl/202609060006.aspx"


def source_candidates():
    return {
        "schema_version": "1.0.0",
        "window_start": WINDOW["start"],
        "window_end": WINDOW["end"],
        "items": [{
            "row_id": ROW_ID,
            "candidate_id": "candidate-1",
            "provisional_group_id": "group-1",
            "source_id": "cna",
            "section": "TWN",
            "url": CANONICAL,
            "canonical_url": CANONICAL,
            "published_at": "2026-09-06T04:59:00+08:00",
            "listing_timestamp_evidence": "2026/09/06 04:59",
            "title": "fixture",
        }],
    }


def relevance_gate():
    return {
        "input_article_row_count": 1,
        "decisions": [{
            "row_id": ROW_ID,
            "candidate_id": "candidate-1",
            "source_id": "cna",
            "canonical_url": CANONICAL,
            "route": "content_hydration",
            "reasons": ["regional_supplement_complete_admission"],
        }],
    }


def hydration_request(**updates):
    value = {
        "schema_version": "1.0",
        "operation": "article_hydration",
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "batch_sequence": 1,
        "row_ids": [ROW_ID],
    }
    value.update(updates)
    return value


def unresolved_result():
    return {
        "row_id": ROW_ID,
        "candidate_id": "candidate-1",
        "canonical_url": CANONICAL,
        "requested_url": CANONICAL,
        "source_id": "cna",
        "status": "unresolved",
        "actual_url": None,
        "content_type": None,
        "content_sha256": None,
        "article_body_published_at": None,
        "article_body_timestamp_evidence": None,
        "article_body_evidence_url": None,
        "error": "temporary failure",
    }


def ready_result():
    return {
        "row_id": ROW_ID,
        "candidate_id": "candidate-1",
        "canonical_url": CANONICAL,
        "requested_url": CANONICAL,
        "source_id": "cna",
        "status": "content_ready",
        "actual_url": CANONICAL,
        "content_type": "text/html; charset=utf-8",
        "content_sha256": "b" * 64,
        "article_body_published_at": "2026-09-06T04:59:00+08:00",
        "article_body_timestamp_evidence": "2026-09-06T04:59:00+08:00",
        "article_body_evidence_url": CANONICAL,
        "error": None,
    }


def write_result(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "1.1", "rows": [row]}), encoding="utf-8")


class HydrateSourceRowsTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime.fromisoformat(WINDOW["start"])
        self.end = datetime.fromisoformat(WINDOW["end"])

    def test_in_window_body_timestamp_is_content_ready(self):
        data = b'<meta property="article:published_time" content="2026-09-06T04:59:00+08:00"><p>body</p>'
        with patch.object(hydration, "fetch", return_value=(data, CANONICAL, "text/html; charset=utf-8")):
            row = hydration.hydrate(source_candidates(), [ROW_ID], self.start, self.end)[0]
        self.assertEqual("content_ready", row["status"])
        self.assertEqual("2026-09-06T04:59:00+08:00", row["article_body_published_at"])
        self.assertEqual(64, len(row["content_sha256"]))

    def test_article_body_proving_outside_window_is_terminal_evidence_not_failure(self):
        data = b'<meta property="article:published_time" content="2026-09-04T04:59:00+08:00"><p>old body</p>'
        with patch.object(hydration, "fetch", return_value=(data, CANONICAL, "text/html; charset=utf-8")):
            row = hydration.hydrate(source_candidates(), [ROW_ID], self.start, self.end)[0]
        self.assertEqual("outside_window", row["status"])
        self.assertEqual("2026-09-04T04:59:00+08:00", row["article_body_published_at"])
        self.assertIsNone(row["error"])

    def test_single_transport_failure_remains_unresolved(self):
        with patch.object(hydration, "fetch", side_effect=urllib.error.URLError("temporary")):
            row = hydration.hydrate(source_candidates(), [ROW_ID], self.start, self.end)[0]
        self.assertEqual("unresolved", row["status"])
        self.assertIn("temporary", row["error"])

    def test_fetched_body_without_authoritative_timestamp_remains_unresolved_with_hash(self):
        data = b"<html><body>body but no timestamp</body></html>"
        with patch.object(hydration, "fetch", return_value=(data, CANONICAL, "text/html; charset=utf-8")):
            row = hydration.hydrate(source_candidates(), [ROW_ID], self.start, self.end)[0]
        self.assertEqual("unresolved", row["status"])
        self.assertEqual(64, len(row["content_sha256"]))
        self.assertEqual(CANONICAL, row["article_body_evidence_url"])


class SourceRowAdmissionTerminalTests(unittest.TestCase):
    def test_outside_window_terminal_row_is_conserved(self):
        evidence = {
            "rows": [{
                "row_id": ROW_ID,
                "admission_status": "outside_window",
                "article_body_published_at": "2026-09-04T04:59:00+08:00",
                "article_body_timestamp_evidence": "2026-09-04T04:59:00+08:00",
                "article_body_evidence_url": CANONICAL,
                "content_sha256": "c" * 64,
                "failure_evidence": None,
                "model_evidence": {
                    "review_status": "outside_window",
                    "reason": "article body proves it is outside the run window",
                    "evidence_refs": [CANONICAL],
                },
            }],
        }
        ledger = admissions.build(source_candidates(), relevance_gate(), evidence, run_id=RUN_ID)
        self.assertEqual("outside_window", ledger["rows"][0]["admission_status"])
        self.assertEqual([], admissions.validate(ledger))

    def test_genuine_exhaustion_does_not_require_fabricated_timestamp_or_hash(self):
        evidence = {
            "rows": [{
                "row_id": ROW_ID,
                "admission_status": "unresolved_exhausted",
                "article_body_published_at": None,
                "article_body_timestamp_evidence": None,
                "article_body_evidence_url": None,
                "content_sha256": None,
                "failure_evidence": {
                    "attempted_url": CANONICAL,
                    "error": "all configured recovery routes exhausted",
                    "recovery_evidence": ["browser_snapshot:final fallback failed"],
                },
                "model_evidence": {
                    "review_status": "unresolved_exhausted",
                    "reason": "recovery exhausted",
                    "evidence_refs": [CANONICAL],
                },
            }],
        }
        ledger = admissions.build(source_candidates(), relevance_gate(), evidence, run_id=RUN_ID)
        self.assertIsNone(ledger["rows"][0]["article_body_published_at"])
        self.assertEqual([], admissions.validate(ledger))


class RemoteHydrationRecoveryTests(unittest.TestCase):
    def test_request_allows_same_batch_retry_controls(self):
        request = hydration_request(
            batch_sequence=2,
            fetch_overrides={ROW_ID: CANONICAL + "?recovery=1"},
        )
        self.assertEqual("article_hydration", bridge.validate(request, MAIN_SHA)["operation"])

    def test_exhaustion_requires_matching_evidence_and_cannot_fetch_simultaneously(self):
        with self.assertRaisesRegex(ValueError, "exactly match"):
            bridge.validate(hydration_request(exhausted_row_ids=[ROW_ID]), MAIN_SHA)
        with self.assertRaisesRegex(ValueError, "cannot be fetched"):
            bridge.validate(hydration_request(
                fetch_overrides={ROW_ID: CANONICAL},
                exhausted_row_ids=[ROW_ID],
                exhaustion_evidence={ROW_ID: ["final browser fallback exhausted"]},
            ), MAIN_SHA)
        valid = bridge.validate(hydration_request(
            exhausted_row_ids=[ROW_ID],
            exhaustion_evidence={ROW_ID: ["final browser fallback exhausted"]},
        ), MAIN_SHA)
        self.assertEqual([ROW_ID], valid["exhausted_row_ids"])

    def test_unresolved_can_repeat_in_later_batch_but_terminal_cannot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_result(root / "content-evidence/batch-0001-result.json", unresolved_result())
            write_result(root / "content-evidence/batch-0002-result.json", ready_result())
            latest, history = bridge._result_history(root)
            self.assertEqual("content_ready", latest[ROW_ID]["status"])
            self.assertEqual(2, len(history[ROW_ID]))
            write_result(root / "content-evidence/batch-0003-result.json", ready_result())
            with self.assertRaisesRegex(ValueError, "terminal hydration row repeated"):
                bridge._result_history(root)

    def test_same_incomplete_batch_prepare_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            runlogs = Path(tmp)
            request = hydration_request()
            first = bridge.prepare_hydration(request, runlogs)
            second = bridge.prepare_hydration(request, runlogs)
            self.assertEqual(first, second)
            records = bridge._read_jsonl(first)
            self.assertEqual(1, len(records))
            self.assertEqual("running", records[0]["status"])

    def test_exhaustion_terminal_requires_prior_unresolved(self):
        with self.assertRaisesRegex(ValueError, "prior unresolved"):
            bridge._make_exhausted_result(ROW_ID, [], ["final browser fallback exhausted"])
        terminal = bridge._make_exhausted_result(
            ROW_ID,
            [unresolved_result()],
            ["final browser fallback exhausted"],
        )
        self.assertEqual("unresolved_exhausted", terminal["status"])
        self.assertEqual(["final browser fallback exhausted"], terminal["recovery_evidence"])


if __name__ == "__main__":
    unittest.main()
