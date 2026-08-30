import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchedulePromptControlPlaneTests(unittest.TestCase):
    def test_prompt_is_updated_before_any_media_smoke(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        update = install.index("SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE")
        smoke = install.index("SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE")
        self.assertLess(update, smoke)
        self.assertIn("舊 prompt 不得繼續啟用", install)
        self.assertIn("後續 smoke 失敗時保留最新版 prompt 並暫停", install)

    def test_install_smoke_does_not_require_repository_bootstrap(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        block = install[
            install.index("SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE") :
            install.index("## Scheduled Task 排程指令唯一契約")
        ]
        self.assertNotIn("maps/generated/taiwan-counties-yellow-v2.png", block)
        self.assertIn("不得要求 verified workspace", block)
        self.assertIn("直接截圖", block)

    def test_saved_task_template_accepts_native_screenshot_route(self):
        prompt = (ROOT / "scheduled-task-prompt-template.md").read_text(encoding="utf-8")
        self.assertIn("HOST_VISIBLE_SCREENSHOT_ROUTE", prompt)
        self.assertIn("不要求原始檔或原畫質", prompt)
        self.assertNotIn("maps/generated/taiwan-counties-yellow-v2.png", prompt)
        self.assertNotIn("只能在已通過", prompt)

    def test_scheduled_host_path_is_active_and_cannot_degrade_after_discovery(self):
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        self.assertIn("SCHEDULED_HOST_VISIBLE_SCREENSHOT_ROUTE", mobile)
        self.assertIn("不得在 discovery 後宣告 NATIVE_MEDIA_UNAVAILABLE", mobile)
        self.assertNotIn("本檔只保留給 mobile-native 的流程外能力診斷", mobile)
        self.assertIn("直接截圖", mobile)


if __name__ == "__main__":
    unittest.main()

