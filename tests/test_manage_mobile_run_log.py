import importlib.util
import json
import subprocess
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
MAIN_SHA = "1" * 40
RUN_WINDOW = {
    "start": "2026-08-16T22:00:00Z",
    "end": "2026-08-17T22:00:00Z",
    "timezone": "Asia/Taipei",
}


def artifact_reference(path, blob_sha, *, run_id=RUN_1, main_sha=MAIN_SHA, window=None):
    return {
        "branch": "run-logs",
        "path": path,
        "blob_sha": blob_sha,
        "run_id": run_id,
        "main_sha": main_sha,
        "window": dict(window or RUN_WINDOW),
    }


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

    def prepare(
        self,
        run_id=RUN_1,
        at="2026-08-17T21:58:00Z",
        scheduled_for="2026-08-18T06:00:00+08:00",
    ):
        return self.module.prepare_run(
            self.ledger_dir,
            run_id=run_id,
            scheduled_for=scheduled_for,
            updated_at=at,
            execution_mode="full-runtime",
        )

    def advance_to(self, target, *, stage_kwargs=None):
        """Advance through every declared stage so tests exercise the real state machine."""
        stage_kwargs = stage_kwargs or {}
        current = self.read("current.json")
        start = self.module.STAGE_INDEX[current["current_stage"]] + 1
        end = self.module.STAGE_INDEX[target] + 1
        result = current
        for index in range(start, end):
            stage = self.module.STAGES[index]
            kwargs = dict(stage_kwargs.get(stage, {}))
            if stage == "executor-started":
                kwargs.setdefault("window", RUN_WINDOW)
            if stage == "main-pinned":
                kwargs.setdefault("main_sha", MAIN_SHA)
            updated_at = (
                RUN_WINDOW["end"]
                if stage == "executor-started"
                else f"2026-08-17T22:{index:02d}:00Z"
            )
            result = self.module.advance_run(
                self.ledger_dir,
                run_id=current["run_id"],
                stage=stage,
                updated_at=updated_at,
                **kwargs,
            )
        return result

    def mobile_artifacts(self):
        return {
            "candidate-audit": {
                "candidate_audit_artifact": artifact_reference(
                    f"logs/runs/{RUN_1}/candidate-audit.json", "a" * 40
                )
            },
            "visuals-completed": {
                "verification_artifact": artifact_reference(
                    f"logs/runs/{RUN_1}/verification.json", "e" * 40
                )
            },
            "reader-rendered": {
                "map_decisions_artifact": artifact_reference(
                    f"logs/runs/{RUN_1}/map-decisions.json", "f" * 40
                ),
                "image_evidence_artifact": artifact_reference(
                    f"logs/runs/{RUN_1}/image-evidence.json", "d" * 40
                ),
            },
            "github-result-saved": {
                "reader_artifact": artifact_reference(
                    "logs/latest-reader.md", "b" * 40
                )
            },
        }

    def test_prepare_creates_awaiting_executor_record(self):
        self.prepare()
        current = self.read("current.json")
        self.assertEqual(current["run_id"], RUN_1)
        self.assertEqual(current["status"], "awaiting_executor")
        self.assertEqual(current["current_stage"], "schedule-prepared")
        self.assertEqual(current["execution_mode"], "full-runtime")
        self.assertEqual(current["delivery_profile"], "full-assets")
        self.assertEqual(current["native_media_status"], "available")
        self.assertEqual(current["capability_limitations"], [])
        self.assertIsNone(current["window"])
        self.assertIsNone(current["candidate_audit_artifact"])
        self.assertIsNone(current["verification_artifact"])
        self.assertIsNone(current["map_decisions_artifact"])
        self.assertIsNone(current["image_evidence_artifact"])
        self.assertEqual(current["durable_audit_status"], "not_started")
        self.assertIsNone(current["durable_audit_artifact"])
        self.assertEqual(current["delivery_status"], "not_ready")
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").exists()
        )

    def test_prepare_uses_actual_task_occurrence_without_fixed_clock(self):
        current = self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T04:00:00+09:00",
            updated_at="2026-08-17T19:00:00Z",
            execution_mode="mobile-native",
        )
        self.assertEqual("2026-08-18T04:00:00+09:00", current["scheduled_for"])
        self.assertEqual("mobile-native", current["execution_mode"])

    def test_mobile_native_mode_and_candidate_audit_artifact_are_persisted(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifact = artifact_reference(
            f"logs/runs/{RUN_1}/candidate-audit.json", "a" * 40
        )
        self.advance_to(
            "candidate-audit",
            stage_kwargs={
                "candidate-audit": {
                    "execution_mode": "mobile-native",
                    "candidate_audit_artifact": artifact,
                }
            },
        )
        current = self.read("current.json")
        self.assertEqual(current["execution_mode"], "mobile-native")
        self.assertEqual(current["candidate_audit_artifact"], artifact)

    def test_mobile_native_requires_verification_binding_after_verification_stage(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        self.advance_to(
            "selection-verified", stage_kwargs=self.mobile_artifacts()
        )
        with self.assertRaisesRegex(ValueError, "verification artifact"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="visuals-completed",
                updated_at="2026-08-17T22:30:00Z",
            )

    def test_mobile_native_requires_candidate_audit_before_selection_verified(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        self.advance_to("candidate-audit")
        with self.assertRaisesRegex(ValueError, "candidate audit artifact"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="selection-verified",
                updated_at="2026-08-17T22:20:00Z",
            )

    def test_mobile_verification_recovery_rebinds_audit_without_stage_regression(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        self.advance_to("selection-verified", stage_kwargs=self.mobile_artifacts())
        revised_audit = artifact_reference(
            f"logs/runs/{RUN_1}/candidate-audit.json", "9" * 40
        )
        recovered = self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="selection-verified",
            updated_at="2026-08-17T22:25:00Z",
            candidate_audit_artifact=revised_audit,
        )
        self.assertEqual("selection-verified", recovered["current_stage"])
        self.assertEqual(revised_audit, recovered["candidate_audit_artifact"])
        self.assertIsNone(recovered["verification_artifact"])

    def test_mobile_native_requires_image_evidence_before_reader_rendered(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["reader-rendered"] = {
            "map_decisions_artifact": artifacts["reader-rendered"]["map_decisions_artifact"]
        }
        self.advance_to("visuals-completed", stage_kwargs=artifacts)
        with self.assertRaisesRegex(ValueError, "image evidence artifact"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="reader-rendered",
                updated_at="2026-08-17T22:40:00Z",
                **artifacts["reader-rendered"],
            )

    def test_mobile_native_requires_reader_before_github_result_saved(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        self.advance_to("reader-rendered", stage_kwargs=artifacts)
        with self.assertRaisesRegex(ValueError, "reader artifact"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="github-result-saved",
                updated_at="2026-08-17T22:45:00Z",
            )

    def test_advance_cli_can_bind_reader_before_github_result_saved(self):
        self.prepare()
        self.advance_to("reader-rendered", stage_kwargs=self.mobile_artifacts())
        reference_path = self.ledger_dir / "reader-reference.json"
        reference_path.write_text(
            json.dumps(self.mobile_artifacts()["github-result-saved"]["reader_artifact"]),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "advance",
                "--ledger-dir",
                str(self.ledger_dir),
                "--run-id",
                RUN_1,
                "--stage",
                "github-result-saved",
                "--updated-at",
                "2026-08-17T22:10:00Z",
                "--reader-artifact",
                str(reference_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        current = self.read("current.json")
        self.assertEqual("github-result-saved", current["current_stage"])
        self.assertEqual(
            self.mobile_artifacts()["github-result-saved"]["reader_artifact"],
            current["reader_artifact"],
        )

    def test_stage_transition_rejects_forward_skip(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "stage skip"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="main-pinned",
                updated_at="2026-08-17T22:01:00Z",
            )

    def test_main_sha_cannot_change_after_pin(self):
        self.prepare()
        self.advance_to("main-pinned")
        with self.assertRaisesRegex(ValueError, "main_sha is immutable"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="main-pinned",
                updated_at="2026-08-17T22:02:00Z",
                main_sha="2" * 40,
            )

    def test_main_pinned_requires_main_sha(self):
        self.prepare()
        self.advance_to("executor-started")
        with self.assertRaisesRegex(ValueError, "main-pinned and later stages require main_sha"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="main-pinned",
                updated_at="2026-08-17T22:02:00Z",
            )

    def test_main_sha_rejected_before_main_pinned(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "main_sha belongs to main-pinned stage"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="schedule-prepared",
                updated_at="2026-08-17T22:00:00Z",
                main_sha=MAIN_SHA,
            )

    def test_executor_started_requires_window(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "executor-started and later stages require window"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="executor-started",
                updated_at="2026-08-17T22:00:00Z",
            )

    def test_window_rejected_before_executor_started(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "window belongs to executor-started stage"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="schedule-prepared",
                updated_at="2026-08-17T21:59:00Z",
                window=RUN_WINDOW,
            )

    def test_window_cannot_change_after_executor_started(self):
        self.prepare()
        self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="executor-started",
            updated_at="2026-08-17T22:00:00Z",
            window=RUN_WINDOW,
        )
        changed = dict(RUN_WINDOW)
        changed["end"] = "2026-08-17T22:30:00Z"
        with self.assertRaisesRegex(ValueError, "window is immutable"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="executor-started",
                updated_at="2026-08-17T22:30:00Z",
                window=changed,
            )

    def test_executor_window_end_must_match_updated_at(self):
        self.prepare()
        mismatched = {
            "start": "2026-08-17T22:00:00Z",
            "end": "2026-08-18T22:00:00Z",
            "timezone": "Asia/Taipei",
        }
        with self.assertRaisesRegex(ValueError, "window end must match executor-started updated_at"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="executor-started",
                updated_at="2026-08-17T22:00:00Z",
                window=mismatched,
            )

    def test_mobile_window_accepts_task_timezone(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T07:00:00+09:00",
            updated_at="2026-08-17T21:59:00Z",
            execution_mode="mobile-native",
        )
        task_timezone = dict(RUN_WINDOW)
        task_timezone["timezone"] = "Asia/Tokyo"
        result = self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="executor-started",
            updated_at="2026-08-17T22:00:00Z",
            window=task_timezone,
        )
        self.assertEqual("Asia/Tokyo", result["window"]["timezone"])

    def test_executor_window_equivalent_offset_is_accepted(self):
        self.prepare()
        equivalent_offset = {
            "start": "2026-08-17T06:00:00+08:00",
            "end": "2026-08-18T06:00:00+08:00",
            "timezone": "Asia/Taipei",
        }
        result = self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="executor-started",
            updated_at="2026-08-17T22:00:00Z",
            window=equivalent_offset,
        )
        self.assertEqual(result["window"], equivalent_offset)

    def test_candidate_audit_window_must_match_ledger_window(self):
        self.prepare()
        mismatched = dict(RUN_WINDOW)
        mismatched["start"] = "2026-08-17T22:30:00Z"
        mismatched["end"] = "2026-08-18T22:30:00Z"
        artifact = artifact_reference(
            f"logs/runs/{RUN_1}/candidate-audit.json",
            "a" * 40,
            window=mismatched,
        )
        with self.assertRaisesRegex(ValueError, "artifact window does not match ledger"):
            self.advance_to(
                "candidate-audit",
                stage_kwargs={"candidate-audit": {"candidate_audit_artifact": artifact}},
            )

    def test_source_scan_resume_preserves_exact_window(self):
        self.prepare()
        self.advance_to("source-scan")
        before = self.read("current.json")["window"]
        resumed = self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="source-scan",
            updated_at="2026-08-17T22:30:00Z",
        )
        self.assertEqual(before, resumed["window"])

    def test_execution_mode_cannot_change_after_prepare(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "execution_mode is immutable"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="schedule-prepared",
                updated_at="2026-08-17T22:00:00Z",
                execution_mode="mobile-native",
            )

    def test_source_scan_rejects_candidate_audit_binding(self):
        self.prepare()
        self.advance_to("source-scan")
        current = self.read("current.json")
        current["candidate_audit_artifact"] = self.mobile_artifacts()["candidate-audit"][
            "candidate_audit_artifact"
        ]
        with self.assertRaisesRegex(ValueError, "candidate audit artifact.*future stage"):
            self.module.validate_record(current)

    def test_source_scan_rejects_verification_binding(self):
        self.prepare()
        self.advance_to("source-scan")
        current = self.read("current.json")
        current["verification_artifact"] = self.mobile_artifacts()["visuals-completed"][
            "verification_artifact"
        ]
        with self.assertRaisesRegex(ValueError, "verification artifact.*future stage"):
            self.module.validate_record(current)

    def test_source_scan_rejects_map_and_image_bindings(self):
        self.prepare()
        self.advance_to("source-scan")
        current = self.read("current.json")
        current.update(self.mobile_artifacts()["reader-rendered"])
        with self.assertRaisesRegex(ValueError, "map decisions artifact.*future stage"):
            self.module.validate_record(current)

    def test_source_scan_rejects_reader_binding(self):
        self.prepare()
        self.advance_to("source-scan")
        current = self.read("current.json")
        current.update(self.mobile_artifacts()["github-result-saved"])
        with self.assertRaisesRegex(ValueError, "reader artifact.*future stage"):
            self.module.validate_record(current)

    def test_artifact_run_id_mismatch_rejects_binding(self):
        self.prepare()
        artifact = artifact_reference(
            f"logs/runs/{RUN_1}/candidate-audit.json", "a" * 40, run_id=RUN_2
        )
        with self.assertRaisesRegex(ValueError, "artifact run_id"):
            self.advance_to(
                "candidate-audit",
                stage_kwargs={"candidate-audit": {"candidate_audit_artifact": artifact}},
            )

    def test_artifact_main_sha_mismatch_rejects_binding(self):
        self.prepare()
        artifact = artifact_reference(
            f"logs/runs/{RUN_1}/candidate-audit.json", "a" * 40, main_sha="2" * 40
        )
        with self.assertRaisesRegex(ValueError, "artifact main_sha"):
            self.advance_to(
                "candidate-audit",
                stage_kwargs={"candidate-audit": {"candidate_audit_artifact": artifact}},
            )

    def test_artifact_window_mismatch_rejects_binding(self):
        self.prepare()
        artifacts = self.mobile_artifacts()
        mismatched = dict(RUN_WINDOW)
        mismatched["end"] = "2026-08-18T21:59:59Z"
        artifacts["visuals-completed"] = {
            "verification_artifact": artifact_reference(
                f"logs/runs/{RUN_1}/verification.json", "e" * 40, window=mismatched
            )
        }
        with self.assertRaisesRegex(ValueError, "artifact window"):
            self.advance_to("visuals-completed", stage_kwargs=artifacts)

    def test_same_run_main_and_window_artifact_identity_passes(self):
        self.prepare()
        result = self.advance_to("candidate-audit", stage_kwargs=self.mobile_artifacts())
        self.assertEqual(
            RUN_WINDOW, result["candidate_audit_artifact"]["window"]
        )

    def test_mobile_native_requires_map_binding_after_visuals_stage(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        verification = artifact_reference(
            f"logs/runs/{RUN_1}/verification.json", "e" * 40
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"] = {
            "verification_artifact": verification
        }
        self.advance_to("visuals-completed", stage_kwargs=artifacts)
        with self.assertRaisesRegex(ValueError, "map decisions artifact"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="reader-rendered",
                updated_at="2026-08-17T22:40:00Z",
            )

    def test_same_occurrence_resume_preserves_verification_and_map_bindings(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        verification = artifact_reference(
            f"logs/runs/{RUN_1}/verification.json", "e" * 40
        )
        maps = artifact_reference(
            f"logs/runs/{RUN_1}/map-decisions.json", "f" * 40
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"] = {
            "verification_artifact": verification
        }
        artifacts["reader-rendered"] = {
            "map_decisions_artifact": maps,
            "image_evidence_artifact": self.mobile_artifacts()["reader-rendered"][
                "image_evidence_artifact"
            ],
        }
        self.advance_to("reader-rendered", stage_kwargs=artifacts)
        resumed = self.prepare(run_id=RUN_2, at="2026-08-17T22:54:00Z")
        self.assertEqual(verification, resumed["verification_artifact"])
        self.assertEqual(maps, resumed["map_decisions_artifact"])

    def test_prepare_rejects_noncanonical_run_id(self):
        with self.assertRaisesRegex(ValueError, "canonical format"):
            self.prepare(run_id="run-001")

    def test_read_rejects_retired_schema_instead_of_migrating_it(self):
        retired = self.ledger_dir / "retired.json"
        retired.write_text(json.dumps({"schema_version": "1.2.0"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported run-log schema version"):
            self.module._read_json(retired)

    def test_next_prepare_rotates_completed_current_to_previous(self):
        self.prepare()
        artifact = artifact_reference(
            f"logs/runs/{RUN_1}/candidate-audit.json", "a" * 40
        )
        reader = artifact_reference("logs/latest-reader.md", "b" * 40)
        self.advance_to(
            "delivery-handoff",
            stage_kwargs={
                "delivery-handoff": {
                    "status": "completed",
                    "delivery_status": "handoff_started",
                    "candidate_audit_artifact": artifact,
                    "reader_artifact": reader,
                }
            },
        )
        self.prepare(run_id=RUN_2, at="2026-08-18T21:58:00Z", scheduled_for="2026-08-19T06:00:00+08:00")
        self.assertEqual(self.read("previous.json")["run_id"], RUN_1)
        self.assertEqual(self.read("previous.json")["status"], "completed")
        self.assertEqual(self.read("current.json")["run_id"], RUN_2)

    def test_mobile_native_media_delivery_failure_stops_at_visuals(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"].update({
            "delivery_profile": "reader-canonical-capability-degraded",
            "native_media_status": "unavailable",
            "capability_limitations": ["NATIVE_MEDIA_UNAVAILABLE"],
            "image_evidence_artifact": artifacts["reader-rendered"][
                "image_evidence_artifact"
            ],
        })
        self.advance_to("visuals-completed", stage_kwargs=artifacts)
        with self.assertRaisesRegex(ValueError, "visuals-completed recovery"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="reader-rendered",
                updated_at="2026-08-17T22:40:00Z",
                **artifacts["reader-rendered"],
            )
        current = self.read("current.json")
        self.assertEqual(current["status"], "running")
        self.assertEqual(current["current_stage"], "visuals-completed")
        self.assertEqual(current["delivery_profile"], "reader-canonical-capability-degraded")
        self.assertEqual(current["capability_limitations"], ["NATIVE_MEDIA_UNAVAILABLE"])
        self.assertIsNone(current["last_error"])

    def test_completed_record_rejects_native_media_delivery_failure(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"].update({
            "delivery_profile": "reader-canonical-capability-degraded",
            "native_media_status": "unavailable",
            "capability_limitations": ["NATIVE_MEDIA_UNAVAILABLE"],
            "image_evidence_artifact": artifacts["reader-rendered"][
                "image_evidence_artifact"
            ],
        })
        self.advance_to("visuals-completed", stage_kwargs=artifacts)
        current = self.read("current.json")
        current["current_stage"] = "delivery-handoff"
        current["stage_index"] = self.module.STAGE_INDEX["delivery-handoff"]
        current["status"] = "completed"
        current["delivery_status"] = "handoff_started"
        with self.assertRaisesRegex(ValueError, "visuals-completed recovery"):
            self.module.validate_record(current)

    def test_mobile_source_exhaustion_can_complete_without_capability_limitation(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["delivery-handoff"] = {
            "status": "completed",
            "delivery_status": "handoff_started",
        }
        self.advance_to("delivery-handoff", stage_kwargs=artifacts)
        current = self.read("current.json")
        self.assertEqual("completed", current["status"])
        self.assertEqual([], current["capability_limitations"])

    def test_noncritical_qualified_image_delivery_failure_blocks_reader(self):
        reader = ROOT / "tests" / "fixtures" / "mobile-reader-missing-verified-image.md"
        evidence = (
            ROOT
            / "tests"
            / "fixtures"
            / "mobile-reader-missing-verified-image-evidence.json"
        )
        self.assertNotIn("![", reader.read_text(encoding="utf-8"))
        evidence_data = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertFalse(evidence_data["events"][0]["claim_critical"])
        self.assertTrue(evidence_data["events"][0]["usable_image_found"])
        self.assertEqual(
            evidence_data["events"][0]["delivery_outcome"], "delivery_unavailable"
        )

        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"].update({
            "delivery_profile": "reader-canonical-capability-degraded",
            "native_media_status": "unavailable",
            "capability_limitations": ["NATIVE_MEDIA_UNAVAILABLE"],
            "image_evidence_artifact": artifacts["reader-rendered"][
                "image_evidence_artifact"
            ],
        })
        self.advance_to("visuals-completed", stage_kwargs=artifacts)
        with self.assertRaisesRegex(ValueError, "visuals-completed recovery"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="reader-rendered",
                updated_at="2026-08-17T22:08:00Z",
                **artifacts["reader-rendered"],
            )

        current = self.read("current.json")
        self.assertEqual(current["status"], "running")
        self.assertEqual(current["current_stage"], "visuals-completed")

    def test_native_media_unavailable_requires_visuals_completed(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        self.advance_to("source-scan")
        current = self.read("current.json")
        current.update({
            "delivery_profile": "reader-canonical-capability-degraded",
            "native_media_status": "unavailable",
            "capability_limitations": ["NATIVE_MEDIA_UNAVAILABLE"],
        })
        with self.assertRaisesRegex(ValueError, "requires running visuals-completed"):
            self.module.validate_record(current)

    def test_native_media_unavailable_requires_running_status(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"].update({
            "delivery_profile": "reader-canonical-capability-degraded",
            "native_media_status": "unavailable",
            "capability_limitations": ["NATIVE_MEDIA_UNAVAILABLE"],
            "image_evidence_artifact": artifacts["reader-rendered"][
                "image_evidence_artifact"
            ],
        })
        self.advance_to("visuals-completed", stage_kwargs=artifacts)
        current = self.read("current.json")
        current["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "requires running visuals-completed"):
            self.module.validate_record(current)

    def test_same_run_visual_recovery_preserves_news_artifacts(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        artifacts = self.mobile_artifacts()
        artifacts["visuals-completed"].update({
            "delivery_profile": "reader-canonical-capability-degraded",
            "native_media_status": "unavailable",
            "capability_limitations": ["NATIVE_MEDIA_UNAVAILABLE"],
            "image_evidence_artifact": artifacts["reader-rendered"][
                "image_evidence_artifact"
            ],
        })
        blocked = self.advance_to("visuals-completed", stage_kwargs=artifacts)
        revised_image = artifact_reference(
            f"logs/runs/{RUN_1}/image-evidence.json", "8" * 40
        )
        recovered = self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="visuals-completed",
            updated_at="2026-08-17T22:41:00Z",
            delivery_profile="full-assets",
            native_media_status="available",
            capability_limitations=[],
            image_evidence_artifact=revised_image,
        )
        self.assertEqual(blocked["candidate_audit_artifact"], recovered["candidate_audit_artifact"])
        self.assertEqual(blocked["verification_artifact"], recovered["verification_artifact"])
        self.assertEqual(revised_image, recovered["image_evidence_artifact"])

    def test_completed_run_requires_run_scoped_candidate_audit_not_durable_history(self):
        self.prepare()
        self.advance_to("github-result-saved")
        with self.assertRaisesRegex(ValueError, "run-scoped candidate audit"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="delivery-handoff",
                updated_at="2026-08-18T00:15:00Z",
                status="completed",
                delivery_status="handoff_started",
                reader_artifact=artifact_reference(
                    "logs/latest-reader.md", "b" * 40
                ),
                candidate_audit_artifact=artifact_reference(
                    "logs/latest-candidate-audit.json", "a" * 40
                ),
            )

    def test_next_prepare_marks_running_current_interrupted(self):
        self.prepare()
        self.advance_to("source-scan")
        self.prepare(run_id=RUN_2, at="2026-08-18T21:58:00Z", scheduled_for="2026-08-19T06:00:00+08:00")
        previous = self.read("previous.json")
        self.assertEqual(previous["status"], "interrupted_by_next_run")
        self.assertEqual(previous["current_stage"], "source-scan")
        self.assertEqual(previous["last_error"]["code"], "executor_interrupted")

    def test_rotation_replaces_the_older_previous_record(self):
        self.prepare(RUN_1)
        self.prepare(RUN_2, "2026-08-18T21:58:00Z", "2026-08-19T06:00:00+08:00")
        self.prepare(RUN_3, "2026-08-19T21:58:00Z", "2026-08-20T06:00:00+08:00")
        self.assertEqual(self.read("previous.json")["run_id"], RUN_2)
        self.assertNotIn(RUN_1, (self.ledger_dir / "previous.json").read_text(encoding="utf-8"))
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").exists()
        )

    def test_same_occurrence_resumes_existing_reader_run_without_rotation(self):
        self.prepare()
        reader = artifact_reference("logs/latest-reader.md", "b" * 40)
        self.advance_to(
            "reader-rendered",
            stage_kwargs={
                "reader-rendered": {
                    "delivery_status": "reader_saved",
                    "reader_artifact": reader,
                }
            },
        )
        resumed = self.prepare(run_id=RUN_2, at="2026-08-17T22:54:00Z")
        self.assertEqual(RUN_1, resumed["run_id"])
        self.assertEqual("reader-rendered", resumed["current_stage"])
        self.assertEqual("reader_saved", resumed["delivery_status"])
        self.assertEqual(reader, resumed["reader_artifact"])
        self.assertFalse((self.ledger_dir / "previous.json").exists())

    def test_equivalent_timezone_timestamp_resumes_same_occurrence(self):
        self.prepare()
        resumed = self.prepare(
            run_id=RUN_2,
            at="2026-08-17T22:54:00Z",
            scheduled_for="2026-08-17T22:00:00+00:00",
        )
        self.assertEqual(RUN_1, resumed["run_id"])
        self.assertFalse((self.ledger_dir / "previous.json").exists())

    def test_stage_transition_rejects_regression(self):
        self.prepare()
        self.advance_to("selection-verified")
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
        self.advance_to("github-result-saved")
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

