import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FullRuntimeVisibleImageContractTests(unittest.TestCase):
    def test_every_daily_news_surface_requires_full_runtime(self):
        documents = (
            ROOT / "INSTALL.md",
            ROOT / "README.md",
            ROOT / "scheduled-task-prompt-template.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "news-brief-settings.md",
            ROOT / ".agents/skills/daily-news-brief/SKILL.md",
            ROOT / ".agents/skills/collect-news-images/SKILL.md",
            ROOT / ".agents/skills/recover-news-run/SKILL.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("EVERY_DAILY_NEWS_EXECUTION_GATE", text, path.name)
            self.assertIn(
                "manual, single-run, test, first-run, recurring, or resume",
                text,
                path.name,
            )

    def test_active_contract_has_no_mobile_news_execution_branch(self):
        documents = (
            ROOT / "INSTALL.md",
            ROOT / "README.md",
            ROOT / "scheduled-task-prompt-template.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "news-brief-settings.md",
            ROOT / ".agents/skills/daily-news-brief/SKILL.md",
            ROOT / ".agents/skills/select-news-events/SKILL.md",
            ROOT / ".agents/skills/verify-news-events/SKILL.md",
            ROOT / ".agents/skills/collect-news-images/SKILL.md",
            ROOT / ".agents/skills/recover-news-run/SKILL.md",
        )
        forbidden = (
            "mobile-native 在 capability routing 選定後建立或 resume",
            "mobile-native 保存 `verification.json`",
            "mobile-native 保存 `map-decisions.json`",
            "mobile-native 執行 `MOBILE_READER_STRUCTURE_EQUIVALENT`",
            "MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT",
            "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden:
                self.assertNotIn(phrase, text, f"{path.name}: {phrase}")

    def test_retired_mobile_prompt_is_inert(self):
        retired = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("DEPRECATED_NON_EXECUTABLE_MOBILE_NEWS_PATH", retired)
        self.assertIn("不得原地推進", retired)
        for forbidden in (
            "MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT",
            "MOBILE_READER_STRUCTURE_EQUIVALENT",
            "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
            "execution_mode=mobile-native",
        ):
            self.assertNotIn(forbidden, retired)

    def test_screenshot_is_first_class_and_original_quality_is_not_required(self):
        documents = (
            ROOT / "INSTALL.md",
            ROOT / "scheduled-task-prompt-template.md",
            ROOT / "news-brief-settings.md",
            ROOT / ".agents/skills/collect-news-images/SKILL.md",
            ROOT / ".agents/skills/recover-news-run/SKILL.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE", text, path.name)
            self.assertIn("原畫質", text, path.name)
            self.assertTrue("截圖" in text or "截取" in text, path.name)


if __name__ == "__main__":
    unittest.main()
