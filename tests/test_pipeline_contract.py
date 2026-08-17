import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PipelineContractTests(unittest.TestCase):
    def test_taiwan_domestic_coverage_guard_is_bounded_and_audited(self):
        import json

        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        self.assertIn("taiwan_coverage_sweeps", pool)
        sweeps = pool["taiwan_coverage_sweeps"]
        self.assertEqual(
            {
                "economy_trade_industry",
                "health_food_consumer",
                "central_policy_institutions",
            },
            {item["sweep_id"] for item in sweeps},
        )
        self.assertTrue(all(item["result_limit"] == 5 for item in sweeps))
        self.assertTrue(all(item["same_source_only"] is True for item in sweeps))
        self.assertTrue(all(item["window_hours"] == 24 for item in sweeps))
        self.assertEqual(5, pool["primary_sources_per_section"])

        documents = [
            ROOT / "news-brief-settings.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/acquire-news-candidates/SKILL.md",
        ]
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("TAIWAN_DOMESTIC_COVERAGE_GUARD", text)
            self.assertIn("same-source recovery", text)
            self.assertIn("5 results", text)
            self.assertIn("canonical candidate audit", text)

    def test_taiwan_domestic_grading_requires_consequences_not_topic(self):
        severity = (ROOT / ".agents/skills/select-news-events/references/severity-rubric.md").read_text(encoding="utf-8")
        examples = (ROOT / "news-brief-examples.md").read_text(encoding="utf-8")
        for marker in (
            "broad_business_operating_impact",
            "nationwide_consumer_recall",
            "central_budget_constitutional_consequence",
            "rhetoric_without_new_consequence",
        ):
            self.assertIn(marker, severity)
            self.assertIn(marker, examples)

    def test_run_started_ledger_precedes_high_pressure_bootstrap_reads(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        bootstrap = (ROOT / "bootstrap-workspace.md").read_text(encoding="utf-8")

        for document in (prompt, bootstrap):
            ordered_markers = (
                "EARLY_DIAGNOSTIC_RUN_ID",
                "EARLY_DIAGNOSTIC_MAIN_PINNED",
                "EARLY_DIAGNOSTIC_RUN_STARTED",
                "EARLY_DIAGNOSTIC_TREE_VERIFIED",
                "EARLY_DIAGNOSTIC_MANIFEST_VERIFIED",
                "EARLY_DIAGNOSTIC_HELPERS_VERIFIED",
            )
            for marker in ordered_markers:
                self.assertIn(marker, document)
            positions = [document.index(marker) for marker in ordered_markers]
            self.assertEqual(positions, sorted(positions))
            self.assertIn("before any recursive tree read", document)
            self.assertIn("update the same comment", document)

    def test_external_ledger_is_debounced_and_never_blocks_news(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        protocol = (ROOT / "bootstrap" / "RUN_LEDGER_PROTOCOL.md").read_text(
            encoding="utf-8"
        )

        for document in (prompt, protocol):
            self.assertIn("one comment per run_id", document)
            self.assertIn("every 8 completed chunks", document)
            self.assertIn("at most once every 3 minutes", document)
            self.assertIn("best-effort", document)
            self.assertIn("must never block the news pipeline", document)
            self.assertIn("external_ledger: unavailable", document)

    def test_mobile_bootstrap_has_bounded_diagnostic_transport(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        bootstrap = (ROOT / "bootstrap-workspace.md").read_text(encoding="utf-8")

        for document in (prompt, bootstrap):
            self.assertIn("bootstrap/bootstrap_progress.py", document)
            self.assertIn("16-line", document)
            self.assertIn("one initial attempt plus at most three retries", document)
            self.assertIn("2, 5, and 10", document)
            self.assertIn("RUN_RECEIPT", document)
            self.assertIn("external_ledger: unavailable", document)

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

    def test_disaster_publication_floor_and_conflict_precedence_are_explicit(self):
        settings = (ROOT / "news-brief-settings.md").read_text(encoding="utf-8")
        severity = (ROOT / ".agents/skills/select-news-events/references/severity-rubric.md").read_text(encoding="utf-8")
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for document in (settings, severity, mobile):
            self.assertIn("未滿 50 人", document)
            self.assertIn("50–99 人", document)
            self.assertIn("監控／指定區域", document)
            self.assertIn("軍事／衝突", document)
        self.assertIn("local_disaster_review", severity)
        self.assertNotIn("死亡 100 人以上可列 A-", (ROOT / "news-brief-examples.md").read_text(encoding="utf-8"))

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
