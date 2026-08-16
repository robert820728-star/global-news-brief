import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PipelineContractTests(unittest.TestCase):
    def test_selection_contract_forbids_prior_run_drivers(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        self.assertIn("validate_selection_freshness.py", prompt)
        self.assertIn("不得匯入或執行舊 `work/validation-run-*`", prompt)

    def test_final_manifest_validation_is_after_image_collection(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        skill = (ROOT / ".agents/skills/daily-news-brief/SKILL.md").read_text(
            encoding="utf-8"
        )
        for document in (prompt, skill):
            self.assertIn(
                "validate_news_brief.py stage --stage verify-news-events",
                document,
            )
            self.assertIn(
                "collect-news-images` completed",
                document,
            )
            self.assertIn(
                "validate_news_brief.py manifest",
                document,
            )


if __name__ == "__main__":
    unittest.main()
