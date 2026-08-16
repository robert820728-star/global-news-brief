import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PipelineContractTests(unittest.TestCase):
    def test_each_run_resolves_fresh_main_and_pins_only_that_run(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        bootstrap = (ROOT / "bootstrap-workspace.md").read_text(encoding="utf-8")

        for document in (prompt, bootstrap):
            for requirement in (
                "/git/ref/heads/main?cache_bust=",
                "/commits/main?cache_bust=",
                "fresh UTC nonce",
                "must not enumerate repository branches",
                "must not reuse a commit SHA",
                "same SHA",
            ):
                self.assertIn(requirement, document)

        self.assertIn("pin all repository reads for this run", bootstrap)
        self.assertIn("resolve fresh `main` again on the next run", bootstrap)

    def test_schedule_uses_cross_platform_python_runtime_tools(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "宿主提供的 bundled-runtime",
            "python3 scripts/resolve_bundled_python.py",
            "fetch_source_routes.py",
        ):
            self.assertIn(requirement, prompt)
        self.assertNotIn("powershell.exe", prompt)

    def test_linux_ci_exercises_cross_platform_runtime_paths(self):
        workflow = (ROOT / ".github/workflows/build-bootstrap-capsule.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tests/test_workspace_python_resolver.py", workflow)
        self.assertIn("tests/test_source_route_fetcher.py", workflow)
        self.assertIn("scripts/resolve_bundled_python.py", workflow)
        self.assertIn("scripts/fetch_source_routes.py", workflow)

    def test_mobile_chatgpt_profile_is_low_cost_and_preserves_minimum_contract(self):
        start = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        self.assertIn("Instant", start)
        self.assertIn("不要使用 Thinking 或 Pro", start)
        self.assertIn("每天 06:00", start)
        self.assertIn("建立後立即執行一次", start)
        for requirement in ("十四天", "六項", "C 級以上", "圖片說明"):
            self.assertIn(requirement, daily)
        for forbidden in ("Codex", "powershell", "bootstrap capsule", "git clone"):
            self.assertNotIn(forbidden, daily)

    def test_mobile_image_delivery_uses_small_stable_thumbnail_with_fallback(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "最多一張",
            "同一張圖",
            "srcset",
            "640px",
            "200KB",
            "75–82",
            "改放同一張原圖",
            "替代文字",
            "短效簽名",
            "登入",
            "`data:`",
            "`blob:`",
        ):
            self.assertIn(requirement, daily)
        self.assertNotIn("**圖片來源頁：**", daily)

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
