import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PipelineContractTests(unittest.TestCase):
    def test_scheduled_host_without_python_uses_mobile_native_fallback(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "SCHEDULED_HOST_CAPABILITY_ROUTING",
            "host_execution_unavailable",
            "mobile-chatgpt-daily-prompt.md",
            "execution_mode=full-runtime",
            "execution_mode=mobile-native",
            "do not disable the daily schedule",
        ):
            self.assertIn(requirement, prompt)
        self.assertLess(
            prompt.index("SCHEDULED_HOST_CAPABILITY_ROUTING"),
            prompt.index("EARLY_DIAGNOSTIC_TREE_VERIFIED"),
        )

    def test_pre_probe_metadata_read_is_recoverable_before_news_access(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "PRE_PROBE_METADATA_READ_RECOVERY",
            "must not fail the run",
            "discard the pre-read metadata",
            "must not reuse any pre-read tree, manifest, helper, payload, or chunk",
            "before any news source or prior result is read",
        ):
            self.assertIn(requirement, prompt)

    def test_same_source_recovery_uses_browser_only_as_final_fallback(self):
        documents = [
            ROOT / "news-brief-settings.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/acquire-news-candidates/SKILL.md",
        ]
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("SAME_SOURCE_RECOVERY_ORDER", text)
            self.assertIn(
                "canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot",
                text,
            )
            self.assertIn("browser is the final fallback only", text)
            self.assertIn("recover_same_source_leads.py", text)

    def test_taiwan_domestic_discovery_supplement_is_bounded_and_scored(self):
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
        self.assertTrue(all(item["window_hours"] == 24 for item in sweeps))
        self.assertIn("coverage_guard_recovery", pool["mandatory_overflow_triggers"])

        documents = [
            ROOT / "news-brief-settings.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/acquire-news-candidates/SKILL.md",
        ]
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("TAIWAN_DOMESTIC_COVERAGE_GUARD", text)
            self.assertIn("5 results", text)
            self.assertIn("評分", text)

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
                "PRE_CONTRACT_MAIN_RESOLUTION",
                "EARLY_DIAGNOSTIC_MAIN_PINNED",
                "EARLY_DIAGNOSTIC_RUN_ID",
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

    def test_fresh_main_wrapper_does_not_create_an_impossible_run_id_order(self):
        daily = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        bootstrap = (ROOT / "bootstrap-workspace.md").read_text(encoding="utf-8")
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for document in (daily, bootstrap):
            self.assertIn("PRE_CONTRACT_MAIN_RESOLUTION", document)
            self.assertIn("only permitted pre-contract GitHub reads", document)
            self.assertIn("without a tool call", document)
            self.assertLess(
                document.index("EARLY_DIAGNOSTIC_MAIN_PINNED"),
                document.index("EARLY_DIAGNOSTIC_RUN_ID"),
            )
        self.assertIn("external latest-main resolution", mobile)
        self.assertIn("first runtime GitHub action", mobile)

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
                "/branches/main?cache_bust=",
                "/commits/main?cache_bust=",
                "fresh UTC nonce",
                "single named `main` branch lookup",
                "must not enumerate repository branches",
                "must not reuse a commit SHA",
                "same SHA",
            ):
                self.assertIn(requirement, document)
            self.assertNotIn("/git/ref/heads/main?cache_bust=", document)

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
            "最多兩張",
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

    def test_mobile_image_delivery_requires_reader_visible_result(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "IMAGE_READER_VISIBLE_DELIVERY_GATE",
            "實際顯示",
            "破圖",
            "沿用前輪選圖",
            "圖片說明",
        ):
            self.assertIn(requirement, daily)
        self.assertIn("不算可見圖片", daily)

    def test_mobile_delivery_requires_native_media_content_not_markdown_text(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "NATIVE_MEDIA_BLOCK_DELIVERY_GATE",
            "NATIVE_IMAGE_SEARCH_CARD_ROUTE",
            "image/media content block",
            "async_image_group",
            "rendered pixel",
            "read_thread",
            "agentMessage text",
            "NATIVE_MEDIA_UNAVAILABLE",
        ):
            self.assertIn(requirement, daily)

    def test_mobile_b_or_higher_requires_a_visible_source_image(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE",
            "B 以上",
            "C 級新聞可使用圖片說明",
            "不得整份零張可見圖片",
            "只重做圖片階段",
        ):
            self.assertIn(requirement, daily)

    def test_mobile_images_are_gated_per_story(self):
        documents = (
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / "news-brief-settings.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            for requirement in (
                "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
                "每一則",
                "不得替其他新聞通過",
                "逐則",
            ):
                self.assertIn(requirement, text, f"{path} missing {requirement}")

        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        self.assertIn("og:image", daily)
        self.assertIn("srcset", daily)

    def test_image_workload_is_bounded_without_reducing_news_coverage(self):
        documents = [
            ROOT / "news-brief-settings.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/collect-news-images/SKILL.md",
        ]
        requirements = (
            "IMAGE_DEFAULT_ONE_ASSET",
            "IMAGE_SECOND_ASSET_REQUIRES_INCREMENTAL_INFORMATION",
            "IMAGE_SHA256_REUSE",
            "IMAGE_VISUAL_CHECK_ONCE_PER_HASH",
            "IMAGE_ONE_ASSET_MAY_SATISFY_BOTH_SOURCE_AND_PROFESSIONAL",
            "640px",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            for requirement in requirements:
                self.assertIn(requirement, text, f"{path} missing {requirement}")

        settings = documents[0].read_text(encoding="utf-8")
        self.assertIn("browser is the final fallback only", settings)
        self.assertIn("所有 C 級以上", settings)

    def test_mobile_candidate_audit_has_one_time_bootstrap_without_daily_rescan(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "FIRST_RUN_14_DAY_AUDIT_BOOTSTRAP",
            "從未保存的前輪淘汰候選",
            "純文字十四天回填",
            "不得每天重跑十四天",
        ):
            self.assertIn(requirement, daily)

    def test_discovery_then_verify_replaces_all_source_gate(self):
        import json

        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        scheduled = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))

        for document in (daily, scheduled):
            for requirement in (
                "DISCOVERY_THEN_VERIFY",
                "GDELT",
                "discovery source failure must not block the whole brief",
                "score and deduplicate before independent verification",
                "collect images only after verification",
                "TECH_SCIENCE_EVIDENCE_ROUTE",
                "CONFLICT_MULTI_SIDE_EVIDENCE_ROUTE",
                "DISASTER_OFFICIAL_STATISTICS_ROUTE",
                "OFFICIAL_SOURCE_BIAS_GUARD",
                "CATEGORY_APPROPRIATE_EVIDENCE_ROUTE",
                "MEDIA_TRANSCRIPTION_IS_NOT_VERIFICATION",
                "DOMAIN_EXPERTISE_MATCH",
                "TIMELINESS_WITH_SOURCE_LIMIT_NOTE",
            ):
                self.assertIn(requirement, document)
            self.assertNotIn("FIRST_RUN_SOURCE_COVERAGE_COMPLETENESS_GATE", document)
            self.assertNotIn("15/15", document)

        discovery = pool["discovery_sources"]
        self.assertEqual(["gdelt", "cna", "chinanews"], [item["source_id"] for item in discovery])
        self.assertEqual(1, pool["discovery_policy"]["minimum_ready_sources"])
        self.assertEqual("degrade_not_block", pool["discovery_policy"]["source_failure_policy"])
        self.assertTrue(pool["verification_policy"]["after_scoring"])
        self.assertTrue(pool["verification_policy"]["images_after_verification"])

    def test_candidate_discovery_has_no_fixed_source_completion_gate(self):
        documents = {
            "settings": (ROOT / "news-brief-settings.md").read_text(encoding="utf-8"),
            "acquisition skill": (
                ROOT / ".agents" / "skills" / "acquire-news-candidates" / "SKILL.md"
            ).read_text(encoding="utf-8"),
            "image skill": (
                ROOT / ".agents" / "skills" / "collect-news-images" / "SKILL.md"
            ).read_text(encoding="utf-8"),
        }
        forbidden = (
            "任一來源未完成",
            "十五站與完成回填",
            "任一來源未完成、未按站內前 30 則",
            "prevalidated daily-news sources",
        )
        for label, document in documents.items():
            for phrase in forbidden:
                self.assertNotIn(phrase, document, f"{label} retains fixed-source gate")

        schema = json.loads(
            (ROOT / "schemas" / "news-source-candidate-list.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual({"type": "integer", "minimum": 1}, schema["properties"]["source_count"])
        self.assertEqual(1, schema["properties"]["sources"]["minItems"])
        self.assertNotIn("maxItems", schema["properties"]["sources"])

    def test_conversation_delivery_requires_complete_reader_not_summary(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "CONVERSATION_READER_BYTE_IDENTITY_GATE",
            "完整內容",
            "不得改成摘要",
            "不得以 receipt 取代讀者版",
        ):
            self.assertIn(requirement, daily)

    def test_mobile_reader_must_follow_canonical_template_structure(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "READER_TEMPLATE_STRUCTURE_GATE",
            "news-brief-template.md",
            "## 今日總覽",
            "## 逐條詳報",
            "## 後續觀察",
            "不得加入 `今日重點表`",
        ):
            self.assertIn(requirement, daily)

    def test_mobile_increment_recovers_without_blocking_daily_reader(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "TYPE_CONSISTENT_COVERAGE_SANITY",
            "不得拿前輪來源掃描的 `raw_item_count`",
            "RECOVERABLE_14_DAY_BASELINE_WITHOUT_READER_BLOCK",
            "不得因此阻止本日讀者版",
            "DAILY_COVERAGE_IS_NOT_HISTORICAL_PROOF",
            "不得把可用、來源可核對且符合模板的每日讀者版改判失敗",
        ):
            self.assertIn(requirement, daily)

    def test_mobile_native_can_roll_forward_a_valid_existing_audit_without_rescoring_history(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        skill = (ROOT / ".agents/skills/audit-news-candidates/SKILL.md").read_text(
            encoding="utf-8"
        )

        for document in (daily, skill):
            for requirement in (
                "MOBILE_NATIVE_AUDIT_ROLLING_MERGE",
                "不得重算未發生實質更新的歷史候選",
                "六項欄位、各欄範圍與總分算法未變",
                "GitHub contents API 整檔 replacement",
                "不得因此阻止本日讀者版",
            ):
                self.assertIn(requirement, document)
        self.assertIn("只重評本輪新增或發生實質更新的候選", daily)
        self.assertIn("full-runtime", skill)
        self.assertIn("mobile-native", skill)

    def test_mobile_native_durable_audit_uses_compact_profile_without_verbose_evidence(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        skill = (ROOT / ".agents/skills/audit-news-candidates/SKILL.md").read_text(
            encoding="utf-8"
        )

        required_fields = (
            "candidate_id",
            "dedup_key",
            "event_date",
            "section",
            "title",
            "importance_breakdown",
            "importance_score",
            "provisional_grade",
            "decision",
            "reason",
            "source_ids",
            "selected_event_id",
            "continuity",
        )
        for document in (daily, skill):
            self.assertIn("MOBILE_NATIVE_COMPACT_DURABLE_AUDIT", document)
            for field in required_fields:
                self.assertIn(f"`{field}`", document)
            self.assertIn("MUST_OMIT_VERBOSE_GRADING_EVIDENCE", document)
            self.assertIn("`grading_evidence`", document)
            self.assertIn("`source_audit`", document)
            self.assertIn("full-runtime", document)

    def test_old_event_requires_independently_material_update_to_reenter_reader(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "MATERIAL_UPDATE_REENTRY_GATE",
            "不得只因仍在十四天內每天重刊",
            "本日新增部分必須獨立達到 C 級門檻",
        ):
            self.assertIn(requirement, daily)

    def test_mobile_reentry_uses_48_hour_cooldown_and_current_impact(self):
        documents = (
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / "news-brief-settings.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            for requirement in (
                "MATERIAL_UPDATE_48_HOUR_REENTRY_GATE",
                "48 小時內",
                "滿 48 小時",
                "不得自動重刊",
                "獨立達到 C 級",
            ):
                self.assertIn(requirement, text, f"{path} missing {requirement}")

        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        self.assertIn("實質惡化", daily)

    def test_continuing_events_are_scored_by_verified_impact_delta(self):
        documents = (
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / "news-brief-settings.md",
            ROOT / ".agents/skills/select-news-events/references/severity-rubric.md",
            ROOT / ".agents/skills/audit-news-candidates/SKILL.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            for requirement in (
                "IMPACT_DELTA_CONTINUITY_SCORING",
                "本日可驗證的影響力變化",
                "無新增公共影響的名人死亡",
                "死傷增加、影響範圍擴大",
                "不得因事件較舊而自動降級",
                "PASSIVE_ONE_OFF_FIVE_DAY_DECAY",
                "次日最高 B",
                "第三日最高 C",
                "第四日 D",
                "第五日 E",
                "五個日曆日後",
            ):
                self.assertIn(requirement, text, f"{path} missing {requirement}")

    def test_child_update_cannot_inherit_parent_event_grade(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "NO_PARENT_GRADE_INHERITANCE",
            "縣域消費措施",
            "不得繼承母事件的 B 或 B+",
        ):
            self.assertIn(requirement, daily)

    def test_ceremonial_and_single_company_routine_events_default_below_reader(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "CEREMONIAL_AND_SINGLE_COMPANY_ROUTINE_LOW",
            "喪禮、降半旗、紀念活動、例行訪問",
            "單一公司上市",
            "預設 D",
        ):
            self.assertIn(requirement, daily)

    def test_symbolic_cultural_name_dispute_defaults_below_reader(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "SYMBOLIC_CULTURAL_DISPUTE_LOW",
            "展覽名稱、館名、標示或稱謂爭議",
            "主管機關口頭抗議",
            "預設 D",
        ):
            self.assertIn(requirement, daily)

    def test_announced_diplomatic_visit_without_outcome_defaults_below_reader(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "ROUTINE_DIPLOMATIC_VISIT_LOW",
            "只有宣布訪問行程",
            "王毅訪韓",
            "預設 D",
        ):
            self.assertIn(requirement, daily)

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
            self.assertIn("DEFERRED", document)
            self.assertIn("不得標記整輪失敗", document)


if __name__ == "__main__":
    unittest.main()
