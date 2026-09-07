import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts import materialize_mobile_candidate_audit as transport


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "gnb-20260907T010203Z-a1b2c3d4"
MAIN_SHA = "a" * 40
WINDOW = {
    "start": "2026-09-06T01:02:03+00:00",
    "end": "2026-09-07T01:02:03+00:00",
    "timezone": "Asia/Shanghai",
}


def load_candidate_fixtures():
    spec = importlib.util.spec_from_file_location(
        "candidate_fixture_module", ROOT / "tests" / "test_manage_candidate_audit.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit_input_fixture(root: Path, count: int = 2):
    rows = []
    for index in range(count):
        row_id = f"row-{index + 1:024x}"
        rows.append({
            "row_id": row_id,
            "candidate_id": f"source-candidate-{index + 1}",
            "provisional_group_id": f"group-{index + 1}",
            "source_id": "cna",
            "section": "TWN",
            "title": f"title {index + 1}",
            "summary": f"summary {index + 1}",
            "canonical_url": f"https://example.com/{index + 1}",
            "article_body_published_at": "2026-09-06T12:00:00+08:00",
            "article_body_timestamp_evidence": "article body time",
            "model_excerpt": f"body evidence {index + 1}",
            "model_input_status": "ready",
        })
    batch = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "batch_sequence": 1,
        "row_count": len(rows),
        "rows": rows,
    }
    write_json(root / "audit-input" / "batch-0001.json", batch)
    manifest = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "source_row_count": len(rows),
        "batch_size": 20,
        "batch_count": 1,
        "batch_files": ["batch-0001.json"],
        "ready_for_model_audit": True,
    }
    write_json(root / "audit-input" / "manifest.json", manifest)
    return manifest, batch


def review_result(batch, *, unresolved=False):
    rows = []
    for index, source in enumerate(batch["rows"]):
        disposition = "unresolved" if unresolved and index == 0 else "event_evidence"
        event_id = None if disposition != "event_evidence" else f"semantic-{index + 1}"
        rows.append({
            "row_id": source["row_id"],
            "disposition": disposition,
            "semantic_event_id": event_id,
            "reason": "bounded semantic review completed",
            "model_evidence": {
                "review_status": disposition,
                "reason": "bounded semantic review completed",
                "evidence_refs": [source["canonical_url"]],
            },
        })
    return {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "batch_sequence": batch["batch_sequence"],
        "rows": rows,
    }


class MobileCandidateAuditTransportTests(unittest.TestCase):
    def test_review_result_requires_exact_batch_row_conservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _manifest, batch = audit_input_fixture(root)
            result = review_result(batch)
            result["rows"].pop()
            result_path = root / "result.json"
            write_json(result_path, result)

            with self.assertRaisesRegex(ValueError, "conserve the input row universe exactly"):
                transport.record_review_result(
                    root / "audit-input/manifest.json",
                    root / "audit-input/batch-0001.json",
                    result_path,
                    root / "row-review",
                )

    def test_review_checkpoint_is_idempotent_but_conflicting_overwrite_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _manifest, batch = audit_input_fixture(root)
            result = review_result(batch)
            result_path = root / "result.json"
            write_json(result_path, result)

            first = transport.record_review_result(
                root / "audit-input/manifest.json",
                root / "audit-input/batch-0001.json",
                result_path,
                root / "row-review",
            )
            second = transport.record_review_result(
                root / "audit-input/manifest.json",
                root / "audit-input/batch-0001.json",
                result_path,
                root / "row-review",
            )
            self.assertEqual(first, second)

            result["rows"][0]["reason"] = "conflicting replacement"
            write_json(result_path, result)
            with self.assertRaisesRegex(ValueError, "append-only checkpoint conflict"):
                transport.record_review_result(
                    root / "audit-input/manifest.json",
                    root / "audit-input/batch-0001.json",
                    result_path,
                    root / "row-review",
                )

    def test_scoring_prepare_stops_on_nonterminal_unresolved_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _manifest, batch = audit_input_fixture(root)
            result_path = root / "result.json"
            write_json(result_path, review_result(batch, unresolved=True))
            transport.record_review_result(
                root / "audit-input/manifest.json",
                root / "audit-input/batch-0001.json",
                result_path,
                root / "row-review",
            )

            with self.assertRaisesRegex(ValueError, "unresolved rows must be recovered"):
                transport.prepare_scoring(
                    root / "audit-input/manifest.json",
                    root / "row-review",
                    root / "score-input",
                )

    def test_scoring_result_conserves_events_and_source_urls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _manifest, batch = audit_input_fixture(root)
            review_path = root / "review.json"
            write_json(review_path, review_result(batch))
            transport.record_review_result(
                root / "audit-input/manifest.json",
                root / "audit-input/batch-0001.json",
                review_path,
                root / "row-review",
            )
            score_manifest = transport.prepare_scoring(
                root / "audit-input/manifest.json",
                root / "row-review",
                root / "score-input",
            )
            score_batch = json.loads((root / "score-input/batch-0001.json").read_text(encoding="utf-8"))
            result = {
                "schema_version": "1.0.0",
                "run_id": RUN_ID,
                "main_sha": MAIN_SHA,
                "window": WINDOW,
                "batch_sequence": 1,
                "events": [
                    {
                        "semantic_event_id": event["semantic_event_id"],
                        "candidate": {
                            "semantic_event_id": event["semantic_event_id"],
                            "candidate_urls": event["candidate_urls"],
                        },
                    }
                    for event in score_batch["events"]
                ],
            }
            result["events"][0]["candidate"]["candidate_urls"] = ["https://invented.invalid/"]
            result_path = root / "score-result.json"
            write_json(result_path, result)

            self.assertEqual(2, score_manifest["semantic_event_count"])
            with self.assertRaisesRegex(ValueError, "candidate_urls must exactly match"):
                transport.record_score_result(
                    root / "score-input/manifest.json",
                    root / "score-input/batch-0001.json",
                    result_path,
                    root / "score-results",
                )

    def test_finalize_rebuilds_validator_accepted_candidate_audit(self):
        fixtures = load_candidate_fixtures()
        audit = fixtures.valid_audit(per_source_count=1)
        ledger = fixtures.row_ledger_for(audit)
        run = copy.deepcopy(audit["runs"][-1])
        run_id = run["run_id"]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = []
            for admission in ledger["rows"]:
                rows.append({
                    "row_id": admission["row_id"],
                    "candidate_id": admission["candidate_id"],
                    "provisional_group_id": admission["provisional_group_id"],
                    "source_id": admission["source_id"],
                    "section": admission["section"],
                    "title": admission["candidate_id"],
                    "summary": "fixture",
                    "canonical_url": admission["canonical_url"],
                    "article_body_published_at": admission["article_body_published_at"],
                    "article_body_timestamp_evidence": admission["article_body_timestamp_evidence"],
                    "model_excerpt": "fixture body",
                    "model_input_status": "ready",
                })
            batch = {
                "schema_version": "1.0.0", "run_id": run_id, "main_sha": MAIN_SHA,
                "window": {"start": run["window_start"], "end": run["window_end"], "timezone": "Asia/Shanghai"},
                "batch_sequence": 1, "row_count": len(rows), "rows": rows,
            }
            manifest = {
                "schema_version": "1.0.0", "run_id": run_id, "main_sha": MAIN_SHA,
                "window": batch["window"], "source_row_count": len(rows), "batch_size": 20,
                "batch_count": 1, "batch_files": ["batch-0001.json"],
                "ready_for_model_audit": True,
            }
            write_json(root / "audit-input/manifest.json", manifest)
            write_json(root / "audit-input/batch-0001.json", batch)
            dispositions = {item["row_id"]: item for item in run["article_dispositions"]}
            review = review_result(batch)
            review.update({"run_id": run_id, "window": batch["window"]})
            for item in review["rows"]:
                original = dispositions[item["row_id"]]
                item.update({
                    "disposition": original["disposition"],
                    "semantic_event_id": original["semantic_event_id"],
                    "reason": original["reason"],
                    "model_evidence": original["model_evidence"],
                })
            write_json(root / "review.json", review)
            transport.record_review_result(
                root / "audit-input/manifest.json", root / "audit-input/batch-0001.json",
                root / "review.json", root / "row-review",
            )
            transport.prepare_scoring(
                root / "audit-input/manifest.json", root / "row-review", root / "score-input"
            )
            score_batch = json.loads((root / "score-input/batch-0001.json").read_text(encoding="utf-8"))
            candidates = {item["semantic_event_id"]: item for item in run["candidates"]}
            score_result = {
                "schema_version": "1.0.0", "run_id": run_id, "main_sha": MAIN_SHA,
                "window": batch["window"], "batch_sequence": 1,
                "events": [
                    {"semantic_event_id": item["semantic_event_id"], "candidate": candidates[item["semantic_event_id"]]}
                    for item in score_batch["events"]
                ],
            }
            write_json(root / "score-result.json", score_result)
            transport.record_score_result(
                root / "score-input/manifest.json", root / "score-input/batch-0001.json",
                root / "score-result.json", root / "score-results",
            )
            write_json(root / "run-base.json", {
                key: value for key, value in run.items()
                if key not in {"article_dispositions", "processing_counts", "candidates", "deduplicated_candidate_count"}
            })
            write_json(root / "admissions.json", ledger)
            write_json(root / "history.json", {"schema_version": "1.2.0", "retention_days": 14, "updated_at": run["generated_at"], "runs": []})

            result = transport.finalize(
                root / "audit-input/manifest.json", root / "row-review",
                root / "score-input/manifest.json", root / "score-results",
                root / "run-base.json", root / "admissions.json",
                ROOT / "news-source-pool.json", root / "history.json",
                root / "candidate-audit.json",
            )
            self.assertEqual([], transport.manage_candidate_audit.validate(
                result, json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8")), ledger
            ))


if __name__ == "__main__":
    unittest.main()
