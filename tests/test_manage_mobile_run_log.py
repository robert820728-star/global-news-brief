import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = ROOT / "scripts" / "manage_mobile_run_log.py"
RUN_1 = "gnb-20260817T215800Z-00000001"
RUN_2 = "gnb-20260818T215800Z-00000002"
RUN_3 = "gnb-20260819T215800Z-00000003"


def load_module():
    spec = importlib.util.spec_from_file_location("manage_mobile_run_log", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MobileRunLogTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def read(self, name):
        return json.loads((self.ledger_dir / name).read_text(encoding="utf-8"))

    def prepare(self, run_id=RUN_1, at="2026-08-17T21:58:00Z"):
        return self.module.prepare_run(
            self.ledger_dir,
            run_id=run_id,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at=at,
        )

    def test_prepare_creates_awaiting_executor_record(self):
        self.prepare()
        current = self.read("current.json")
        self.assertEqual(current["run_id"], RUN_1)
        self.assertEqual(current["status"], "awaiting_executor")
        self.assertEqual(current["current_stage"], "schedule-prepared")
        self.assertEqual(current["execution_mode"], "full-runtime")
        self.assertIsNone(current["candidate_audit_artifact"])
        self.assertEqual(current["delivery_status"], "not_ready")
        workflow = (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("58 21 * * *", workflow)
        self.assertIn("run-logs", workflow)

    def test_mobile_native_mode_and_candidate_audit_artifact_are_persisted(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifact = {
            "branch": "run-logs",
            "path": "logs/latest-candidate-audit.json",
            "blob_sha": "a" * 40,
        }
        self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="candidate-audit",
            updated_at="2026-08-17T22:10:00Z",
            execution_mode="mobile-native",
            candidate_audit_artifact=artifact,
        )
        current = self.read("current.json")
        self.assertEqual(current["execution_mode"], "mobile-native")
        self.assertEqual(current["candidate_audit_artifact"], artifact)

    def test_prepare_rejects_noncanonical_run_id(self):
        with self.assertRaisesRegex(ValueError, "canonical format"):
            self.prepare(run_id="run-001")

    def test_next_prepare_rotates_completed_current_to_previous(self):
        self.prepare()
        self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="delivery-handoff",
            updated_at="2026-08-18T00:15:00Z",
            status="completed",
            delivery_status="handoff_started",
        )
        self.prepare(run_id=RUN_2, at="2026-08-18T21:58:00Z")
        self.assertEqual(self.read("previous.json")["run_id"], RUN_1)
        self.assertEqual(self.read("previous.json")["status"], "completed")
        self.assertEqual(self.read("current.json")["run_id"], RUN_2)

    def test_next_prepare_marks_running_current_interrupted(self):
        self.prepare()
        self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="source-scan",
            updated_at="2026-08-17T22:10:00Z",
        )
        self.prepare(run_id=RUN_2, at="2026-08-18T21:58:00Z")
        previous = self.read("previous.json")
        self.assertEqual(previous["status"], "interrupted_by_next_run")
        self.assertEqual(previous["current_stage"], "source-scan")
        self.assertEqual(previous["last_error"]["code"], "executor_interrupted")

    def test_rotation_replaces_the_older_previous_record(self):
        self.prepare(RUN_1)
        self.prepare(RUN_2, "2026-08-18T21:58:00Z")
        self.prepare(RUN_3, "2026-08-19T21:58:00Z")
        self.assertEqual(self.read("previous.json")["run_id"], RUN_2)
        self.assertNotIn(RUN_1, (self.ledger_dir / "previous.json").read_text(encoding="utf-8"))
        workflow = (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("HEAD:main", workflow)

    def test_stage_transition_rejects_regression(self):
        self.prepare()
        self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="selection-verified",
            updated_at="2026-08-17T22:20:00Z",
        )
        with self.assertRaisesRegex(ValueError, "stage regression"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="workspace-ready",
                updated_at="2026-08-17T22:21:00Z",
            )
        mobile_prompt = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        for stage in self.module.STAGES:
            self.assertIn(f"`{stage}`", mobile_prompt)

    def test_client_confirmation_requires_an_external_acknowledgement(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "client delivery cannot be confirmed"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="delivery-handoff",
                updated_at="2026-08-18T00:15:00Z",
                status="completed",
                delivery_status="client_confirmed",
                client_ack=False,
            )
        mobile_prompt = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        self.assertLess(
            mobile_prompt.index("`github-result-saved`"),
            mobile_prompt.index("`delivery-handoff`"),
        )
        self.assertIn("client_confirmed", mobile_prompt)
        self.assertIn("不得宣稱", mobile_prompt)


if __name__ == "__main__":
    unittest.main()

