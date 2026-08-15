import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "recover_news_run.py"
SPEC = importlib.util.spec_from_file_location("recover_news_run", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecoveryControllerTests(unittest.TestCase):
    def test_plan_targets_only_failed_image_stage(self):
        manifest = {
            "stage_status": {"collect-news-images": "failed"},
            "recovery": {"status": "pending", "max_attempts_per_target": 3, "attempts": [], "unresolved_targets": []},
            "events": [
                {
                    "event_id": "GLB-01",
                    "grade": "A",
                    "verification": {"status": "completed", "sources": [{"url": "https://example.com/news"}]},
                    "map": {"required": False, "status": "not_required"},
                    "images": {"status": "pending", "source_checks": [], "assets": []},
                }
            ],
        }
        plan = MODULE.recovery_plan(manifest)
        targets = {(item["target_stage"], item["event_id"], item["reason"]) for item in plan}
        self.assertIn(("collect-news-images", None, "階段狀態為 failed"), targets)
        self.assertIn(("collect-news-images", "GLB-01", "尚未檢查全部引用來源頁"), targets)

    def test_missing_brief_reopens_render_after_core_stages_complete(self):
        manifest = {
            "stage_status": {
                "select-news-events": "completed",
                "verify-news-events": "completed",
                "build-news-maps": "completed",
                "build-news-charts": "completed",
                "collect-news-images": "completed",
                "render": "completed",
                "validate": "completed",
            },
            "recovery": {
                "status": "completed",
                "max_attempts_per_target": 3,
                "attempts": [],
                "unresolved_targets": [],
            },
            "events": [],
            "final_status": "ready",
        }
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "news-brief.md"
            plan = MODULE.recovery_plan(manifest, brief_path=str(missing))
        self.assertTrue(
            any(
                item["target_stage"] == "render"
                and item["continue_required"]
                for item in plan
            )
        )

    def test_third_failure_rotates_strategy_without_stopping_run(self):
        manifest = {
            "stage_status": {"collect-news-images": "failed", "recover-news-run": "in_progress"},
            "recovery": {
                "status": "in_progress",
                "max_attempts_per_target": 3,
                "attempts": [
                    {"target_stage": "collect-news-images", "event_id": "GLB-01", "attempt": 1, "outcome": "failed"},
                    {"target_stage": "collect-news-images", "event_id": "GLB-01", "attempt": 2, "outcome": "failed"},
                ],
                "unresolved_targets": [],
            },
            "events": [],
            "final_status": "draft",
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.json"
            output = Path(directory) / "out.json"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            args = type("Args", (), {
                "input": str(source), "output": str(output), "stage": "collect-news-images",
                "event_id": "GLB-01", "outcome": "failed", "message": "替代來源失敗",
                "error_code": "image_unavailable", "started_at": None,
            })()
            MODULE.record(args)
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["recovery"]["status"], "recovering")
        self.assertEqual(result["stage_status"]["recover-news-run"], "running")
        self.assertEqual(result["final_status"], "draft")
        plan = MODULE.recovery_plan(result)
        target = next(
            item for item in plan
            if item["target_stage"] == "collect-news-images"
            and item["event_id"] == "GLB-01"
        )
        self.assertEqual(target["strategy"], "official-page-screenshot")
        self.assertTrue(target["continue_required"])
        self.assertFalse(target["exhausted"])


if __name__ == "__main__":
    unittest.main()
