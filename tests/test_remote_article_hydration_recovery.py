import json
import tempfile
import unittest
from pathlib import Path

from scripts.remote_acquisition_bridge import (
    _finalize_exhausted,
    _latest_hydration_evidence,
    _try_materialize_regional_ledger,
    validate_request,
)

MAIN_SHA = "a9a8ec2d3340fc123b1aae116b6226d1ece6f86e"
RUN_ID = "gnb-20260905T220000Z-a1b2c3d4"
WINDOW = {
    "start": "2026-09-05T06:00:00+08:00",
    "end": "2026-09-06T06:00:00+08:00",
}


def article_input(**updates):
    value = {
        "row_id": "row-" + "1" * 24,
        "candidate_id": "candidate-1",
        "source_id": "cna",
        "canonical_url": "https://www.cna.com.tw/news/aopl/202609060006.aspx",
        "title": "規範致命自主武器邁出重要一步",
        "listing_published_at": "2026-09-06T04:59:00+08:00",
    }
    value.update(updates)
    return value


def request(row=None, sequence=1):
    return {
        "schema_version": "1.0",
        "operation": "article_hydration",
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "batch_sequence": sequence,
        "article_inputs": [row or article_input()],
    }


def unresolved(row_id=None):
    return {
        "row_id": row_id or article_input()["row_id"],
        "article_body_published_at": None,
        "article_body_timestamp_evidence": None,
        "article_body_evidence_url": article_input()["canonical_url"],
        "content_sha256": None,
        "admission_status": "unresolved",
        "model_evidence": {
            "review_status": "unresolved",
            "reason": "direct route failed; recovery remains",
            "evidence_refs": [article_input()["canonical_url"]],
        },
        "hydration_attempts": [{
            "url": article_input()["canonical_url"],
            "status": "failed",
            "route": "canonical",
        }],
    }


def ready(row_id=None):
    return {
        "row_id": row_id or article_input()["row_id"],
        "article_body_published_at": "2026-09-06T04:59:00+08:00",
        "article_body_timestamp_evidence": "發稿時間：2026/09/06 04:59",
        "article_body_evidence_url": article_input()["canonical_url"],
        "content_sha256": "a" * 64,
        "admission_status": "content_ready",
        "model_evidence": {
            "review_status": "pending_semantic_review",
            "reason": "article body ready",
            "evidence_refs": [article_input()["canonical_url"]],
        },
        "hydration_attempts": [{
            "url": article_input()["canonical_url"],
            "status": "fetched",
            "route": "same_source_alternate",
        }],
    }


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class RemoteArticleHydrationRecoveryTests(unittest.TestCase):
    def test_same_source_fetch_url_is_allowed_but_cross_source_is_rejected(self):
        payload = request(article_input(fetch_url="https://www.cna.com.tw/news/aopl/202609060006.aspx?ref=recovery"))
        validated = validate_request(payload, expected_main_sha=MAIN_SHA)
        self.assertEqual("article_hydration", validated["operation"])

        payload = request(article_input(fetch_url="https://www.reuters.com/world/example"))
        with self.assertRaisesRegex(ValueError, "configured cna source site"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

    def test_exhaustion_confirmation_requires_explicit_evidence_and_no_fetch_url(self):
        payload = request(article_input(exhaustion_confirmed=True))
        with self.assertRaisesRegex(ValueError, "exhaustion_evidence"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

        payload = request(article_input(
            exhaustion_confirmed=True,
            exhaustion_evidence=["browser_snapshot:no timestamp after final same-source fallback"],
            fetch_url=article_input()["canonical_url"],
        ))
        with self.assertRaisesRegex(ValueError, "must not contain fetch_url"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

        payload = request(article_input(
            exhaustion_confirmed=True,
            exhaustion_evidence=["browser_snapshot:no timestamp after final same-source fallback"],
        ))
        self.assertTrue(validate_request(payload, expected_main_sha=MAIN_SHA)["article_inputs"][0]["exhaustion_confirmed"])

    def test_unresolved_row_can_be_retried_but_terminal_row_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp)
            write_jsonl(evidence_dir / "batch-0001.jsonl", [unresolved()])
            write_jsonl(evidence_dir / "batch-0002.jsonl", [ready()])
            latest, history = _latest_hydration_evidence(evidence_dir)
            self.assertEqual("content_ready", latest[article_input()["row_id"]]["admission_status"])
            self.assertEqual(2, len(history[article_input()["row_id"]]))

            write_jsonl(evidence_dir / "batch-0003.jsonl", [ready()])
            with self.assertRaisesRegex(ValueError, "terminal hydrated row was repeated"):
                _latest_hydration_evidence(evidence_dir)

    def test_regional_ledger_waits_for_unresolved_then_materializes_after_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            row = article_input()
            source_row = {
                "row_id": row["row_id"],
                "candidate_id": row["candidate_id"],
                "provisional_group_id": "group-" + "2" * 24,
                "source_id": row["source_id"],
                "source_name": "中央社",
                "section": "TWN",
                "title": row["title"],
                "summary": row["title"],
                "summary_quality": "title_only",
                "discovery_signals": {},
                "published_at": row["listing_published_at"],
                "listing_timestamp_evidence": "2026/09/06 04:59",
                "url": row["canonical_url"],
                "canonical_url": row["canonical_url"],
                "categories": [],
                "discovery_priority_reason": row["title"],
                "acquisition_route": "structured_direct",
                "normalized_title": "fixture",
                "dedup_seed": "2" * 24,
                "snapshot_path": "fixture.json",
                "page_index": 1,
            }
            (output / "source-candidates.json").write_text(json.dumps({
                "schema_version": "1.0.0",
                "window_start": WINDOW["start"],
                "window_end": WINDOW["end"],
                "source_count": 1,
                "sources": ["cna"],
                "items": [source_row],
            }, ensure_ascii=False), encoding="utf-8")
            (output / "news-relevance-gate.json").write_text(json.dumps({
                "schema_version": "1.0.0",
                "input_article_row_count": 1,
                "content_hydration_count": 1,
                "lightweight_semantic_review_count": 0,
                "decisions": [{
                    "row_id": row["row_id"],
                    "candidate_id": row["candidate_id"],
                    "source_id": row["source_id"],
                    "canonical_url": row["canonical_url"],
                    "route": "content_hydration",
                    "reasons": ["regional_supplement_complete_admission"],
                    "matched_discovery_signals": {},
                }],
            }, ensure_ascii=False), encoding="utf-8")

            write_jsonl(output / "content-evidence/batch-0001.jsonl", [unresolved()])
            ledger, remaining = _try_materialize_regional_ledger(output, RUN_ID)
            self.assertIsNone(ledger)
            self.assertEqual(1, remaining)

            write_jsonl(output / "content-evidence/batch-0002.jsonl", [ready()])
            ledger, remaining = _try_materialize_regional_ledger(output, RUN_ID)
            self.assertEqual(0, remaining)
            self.assertTrue(ledger.is_file())
            durable = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(1, durable["source_row_count"])
            self.assertEqual("content_ready", durable["rows"][0]["admission_status"])

    def test_exhausted_terminal_requires_prior_unresolved_history(self):
        row = article_input(
            exhaustion_confirmed=True,
            exhaustion_evidence=["browser_snapshot:final fallback exhausted"],
        )
        with self.assertRaisesRegex(RuntimeError, "requires prior unresolved"):
            _finalize_exhausted(row, [])

        terminal = _finalize_exhausted(row, [unresolved()])
        self.assertEqual("unresolved_exhausted", terminal["admission_status"])
        self.assertEqual("unresolved_exhausted", terminal["model_evidence"]["review_status"])
        self.assertTrue(any(
            attempt.get("status") == "exhaustion_confirmed"
            for attempt in terminal["hydration_attempts"]
        ))


if __name__ == "__main__":
    unittest.main()
