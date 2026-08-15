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


class NewsRunCheckpointTests(unittest.TestCase):
    def test_incomplete_checkpoint_is_fail_closed(self):
        checkpoint = MODULE.create_checkpoint(
            "run-1", "2026-08-14T00:00:00+08:00", "2026-08-15T00:00:00+08:00"
        )
        errors = MODULE.validate_checkpoint(checkpoint)
        self.assertTrue(any("source-scan" in item for item in errors))

    def test_completed_stages_and_bound_artifacts_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "audit.json"
            manifest = root / "manifest.json"
            brief = root / "brief.md"
            audit.write_text("{}", encoding="utf-8")
            manifest.write_text("{}", encoding="utf-8")
            brief.write_text("brief", encoding="utf-8")
            checkpoint = MODULE.create_checkpoint(
                "run-1", "2026-08-14T00:00:00+08:00", "2026-08-15T00:00:00+08:00"
            )
            for stage in MODULE.RELEASE_REQUIRED_STAGES:
                artifacts = []
                if stage == "audit-news-candidates":
                    artifacts = [f"candidate_audit={audit}"]
                elif stage == "materialize-manifest":
                    artifacts = [f"manifest={manifest}"]
                elif stage == "render":
                    artifacts = [f"brief={brief}"]
                MODULE.mark_stage(checkpoint, stage, "completed", artifacts)
            self.assertEqual(MODULE.validate_checkpoint(checkpoint), [])
            self.assertEqual(
                MODULE.verify_bound_artifact(checkpoint, "render", "brief", brief), []
            )

    def test_bound_artifact_change_invalidates_checkpoint_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brief.md"
            path.write_text("first", encoding="utf-8")
            checkpoint = MODULE.create_checkpoint("run", "a", "b")
            MODULE.mark_stage(checkpoint, "render", "completed", [f"brief={path}"])
            path.write_text("changed", encoding="utf-8")
            errors = MODULE.verify_bound_artifact(checkpoint, "render", "brief", path)
            self.assertTrue(any("雜湊不符" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
