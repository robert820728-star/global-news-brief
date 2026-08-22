import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "news_run_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("news_run_checkpoint", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PreManifestRecoveryTests(unittest.TestCase):
    def source_scan_artifacts(self, directory):
        artifacts = []
        for name in MODULE.REQUIRED_STAGE_ARTIFACTS["source-scan"]:
            path = Path(directory) / f"{name}.json"
            path.write_text("{}", encoding="utf-8")
            artifacts.append(f"{name}={path}")
        return artifacts

    def test_plan_targets_earliest_incomplete_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            cp = MODULE.create_checkpoint("run", "a", "b")
            MODULE.mark_stage(cp, "source-scan", "running")
            MODULE.mark_stage(
                cp, "source-scan", "completed",
                self.source_scan_artifacts(directory),
            )
            plan = MODULE.recovery_plan(cp)
            self.assertEqual(plan[0]["target_stage"], "preprocess-news-candidates")
            self.assertTrue(plan[0]["continue_required"])

    def test_failed_source_scan_is_recoverable_without_manifest(self):
        cp = MODULE.create_checkpoint("run", "a", "b")
        MODULE.mark_stage(cp, "source-scan", "running")
        MODULE.mark_stage(cp, "source-scan", "failed", message="timeout")
        plan = MODULE.recovery_plan(cp)
        self.assertEqual(plan[0]["target_stage"], "source-scan")
        self.assertEqual(plan[0]["state"], "failed")

    def test_running_stage_after_interruption_is_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            cp = MODULE.create_checkpoint("run", "a", "b")
            MODULE.mark_stage(cp, "source-scan", "running")
            MODULE.mark_stage(
                cp, "source-scan", "completed",
                self.source_scan_artifacts(directory),
            )
            MODULE.mark_stage(cp, "preprocess-news-candidates", "running")
            plan = MODULE.recovery_plan(cp)
            self.assertEqual(plan[0]["target_stage"], "preprocess-news-candidates")
            self.assertEqual(plan[0]["state"], "running")


if __name__ == "__main__":
    unittest.main()
