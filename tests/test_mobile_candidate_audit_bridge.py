import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import mobile_candidate_audit_bridge as bridge


MAIN_SHA = "a" * 40
RUN_ID = "gnb-20260907T010203Z-a1b2c3d4"
WINDOW = {
    "start": "2026-09-06T01:02:03+00:00",
    "end": "2026-09-07T01:02:03+00:00",
    "timezone": "Asia/Shanghai",
}


def request(operation="candidate_audit_review", **updates):
    value = {
        "schema_version": "1.0",
        "operation": operation,
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
    }
    if operation == "candidate_audit_review":
        value.update({
            "batch_sequence": 1,
            "rows": [{
                "row_id": "row-" + "1" * 24,
                "disposition": "non_news",
                "semantic_event_id": None,
                "reason": "not a reportable event",
                "model_evidence": {
                    "review_status": "non_news",
                    "reason": "not a reportable event",
                    "evidence_refs": ["https://example.com/1"],
                },
            }],
        })
    value.update(updates)
    return value


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class MobileCandidateAuditBridgeTests(unittest.TestCase):
    def test_workflow_executes_against_occurrence_pinned_runtime_and_run_logs_only(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/mobile-candidate-audit-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("ref: ${{ steps.pin.outputs.main_sha }}", workflow)
        self.assertIn("--run-logs-root runlogs", workflow)
        self.assertIn("git add -A -- logs", workflow)
        self.assertNotIn("git add -A -- .", workflow)
        self.assertIn("materialize_mobile_map_decisions.py", workflow)
        self.assertIn("materialize_mobile_image_evidence.py", workflow)
        self.assertIn("mobile-candidate-audit-${{ github.event.issue.number }}", workflow)
        self.assertNotIn("mobile-candidate-audit-${{ github.event.comment.id }}", workflow)

    def test_active_contracts_require_resumable_candidate_verification_and_map_transport(self):
        root = Path(__file__).resolve().parents[1]
        daily = (root / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        install = (root / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("MOBILE_CANDIDATE_AUDIT_CHECKPOINT_TRANSPORT", daily)
        self.assertIn("MOBILE_VERIFICATION_CHECKPOINT_TRANSPORT", daily)
        self.assertIn("MOBILE_MAP_DECISION_CHECKPOINT_TRANSPORT", daily)
        self.assertIn("MOBILE_IMAGE_EVIDENCE_CHECKPOINT_TRANSPORT", daily)
        self.assertIn("candidate_audit_review", install)
        self.assertIn("candidate_audit_status", install)
        self.assertIn("verification_prepare", install)
        self.assertIn("map_prepare", install)
        self.assertIn("image_prepare", install)

    def test_status_operation_persists_derived_next_action(self):
        value = request("candidate_audit_status")
        self.assertEqual("candidate_audit_status", bridge.validate(value, MAIN_SHA)["operation"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_root = root / "runlogs/logs/runs" / RUN_ID
            input_root = run_root / "audit-input"
            row = {
                "row_id": "row-" + "1" * 24,
                "candidate_id": "candidate-1", "provisional_group_id": "group-1",
                "source_id": "cna", "section": "TWN", "title": "fixture",
                "summary": "fixture", "canonical_url": "https://example.com/1",
                "model_excerpt": "fixture body", "model_input_status": "ready",
            }
            write_json(input_root / "batch-0001.json", {
                "schema_version": "1.0.0", "run_id": RUN_ID, "main_sha": MAIN_SHA,
                "window": WINDOW, "batch_sequence": 1, "row_count": 1, "rows": [row],
            })
            write_json(input_root / "manifest.json", {
                "schema_version": "1.0.0", "run_id": RUN_ID, "main_sha": MAIN_SHA,
                "window": WINDOW, "source_row_count": 1, "batch_size": 20,
                "batch_count": 1, "batch_files": ["batch-0001.json"],
                "ready_for_model_audit": True,
            })
            output = bridge.execute(value, root / "runtime", root / "runlogs")
            self.assertEqual("candidate_audit_review", output["next_operation"])
            progress_path = run_root / "candidate-audit-work/progress.json"
            self.assertTrue(progress_path.is_file())
            self.assertEqual(output, json.loads(progress_path.read_text(encoding="utf-8")))

            wrong_window = copy.deepcopy(value)
            wrong_window["window"]["start"] = "2026-09-06T00:02:03+00:00"
            wrong_window["window"]["end"] = "2026-09-07T00:02:03+00:00"
            with self.assertRaisesRegex(ValueError, "status request changed durable run/main/window identity"):
                bridge.execute(wrong_window, root / "runtime", root / "runlogs")

    def test_comment_requires_one_marker_and_one_json_request(self):
        body = bridge.MARKER + "\n```json\n" + json.dumps(request()) + "\n```"
        parsed = bridge.extract_request_from_comment(body)
        self.assertEqual("candidate_audit_review", parsed["operation"])
        with self.assertRaisesRegex(ValueError, "exactly once"):
            bridge.extract_request_from_comment(body + "\n" + bridge.MARKER)

    def test_validation_rejects_stale_sha_and_unbounded_review_batch(self):
        with self.assertRaisesRegex(ValueError, "stale"):
            bridge.validate(request(), "b" * 40)
        oversized = request()
        oversized["rows"] *= 21
        with self.assertRaisesRegex(ValueError, "1..20"):
            bridge.validate(oversized, MAIN_SHA)

    def test_verification_transport_rejects_unknown_event_before_writing(self):
        value = request("verification_event")
        value.update({"event_id": "GLB-99", "verification": {}})
        self.assertEqual("verification_event", bridge.validate(value, MAIN_SHA)["operation"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_root = root / "runlogs/logs/runs" / RUN_ID / "verification-work/input"
            write_json(input_root / "manifest.json", {
                "run_id": RUN_ID, "main_sha": MAIN_SHA, "window": WINDOW,
                "event_ids": ["GLB-01"],
            })
            with self.assertRaisesRegex(ValueError, "unknown selected event"):
                bridge.execute(value, root / "runtime", root / "runlogs")

    def test_map_transport_rejects_unknown_event_before_writing(self):
        value = request("map_event")
        value.update({"event_id": "GLB-99", "map": {"required": False}})
        self.assertEqual("map_event", bridge.validate(value, MAIN_SHA)["operation"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_root = root / "runlogs/logs/runs" / RUN_ID / "map-work/input"
            write_json(input_root / "manifest.json", {
                "run_id": RUN_ID, "main_sha": MAIN_SHA, "window": WINDOW,
                "event_ids": ["GLB-01"],
            })
            with self.assertRaisesRegex(ValueError, "unknown selected event"):
                bridge.execute(value, root / "runtime", root / "runlogs")

    def test_image_transport_rejects_unknown_event_before_writing(self):
        value = request("image_event")
        value.update({"event_id": "GLB-99", "image_evidence": {}})
        self.assertEqual("image_event", bridge.validate(value, MAIN_SHA)["operation"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_root = root / "runlogs/logs/runs" / RUN_ID / "image-work/input"
            write_json(input_root / "manifest.json", {
                "run_id": RUN_ID, "main_sha": MAIN_SHA, "window": WINDOW,
                "event_ids": ["GLB-01"],
            })
            with self.assertRaisesRegex(ValueError, "unknown selected event"):
                bridge.execute(value, root / "runtime", root / "runlogs")

    def test_execute_persists_review_checkpoint_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            runlogs = root / "runlogs"
            input_root = runlogs / "logs" / "runs" / RUN_ID / "audit-input"
            row = {
                "row_id": "row-" + "1" * 24,
                "candidate_id": "candidate-1",
                "provisional_group_id": "group-1",
                "source_id": "cna",
                "section": "TWN",
                "title": "fixture",
                "summary": "fixture",
                "canonical_url": "https://example.com/1",
                "model_excerpt": "fixture body",
                "model_input_status": "ready",
            }
            write_json(input_root / "batch-0001.json", {
                "schema_version": "1.0.0", "run_id": RUN_ID, "main_sha": MAIN_SHA,
                "window": WINDOW, "batch_sequence": 1, "row_count": 1, "rows": [row],
            })
            write_json(input_root / "manifest.json", {
                "schema_version": "1.0.0", "run_id": RUN_ID, "main_sha": MAIN_SHA,
                "window": WINDOW, "source_row_count": 1, "batch_size": 20,
                "batch_count": 1, "batch_files": ["batch-0001.json"],
                "ready_for_model_audit": True,
            })
            output = bridge.execute(request(), runtime, runlogs)
            self.assertEqual("terminal", output["status"])
            result_path = runlogs / "logs" / "runs" / RUN_ID / "candidate-audit-work" / "row-review" / "batch-0001-result.json"
            self.assertTrue(result_path.is_file())
            self.assertEqual(output, bridge.execute(request(), runtime, runlogs))


if __name__ == "__main__":
    unittest.main()
