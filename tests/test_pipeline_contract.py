import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PipelineContractTests(unittest.TestCase):
    def test_install_documents_the_actual_publisher_cli(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

        self.assertIn(
            "python3 scripts/publish_news_brief.py --checkpoint <checkpoint> "
            "--manifest <final-manifest> --audit <candidate-audit> "
            "--source-pool news-source-pool.json --brief <reader> "
            "--output-dir <release-dir>",
            install,
        )
        self.assertIn(
            "python3 scripts/publish_news_brief.py --deliver-receipt "
            "<release-dir>/release-receipt.json --checkpoint <checkpoint> "
            "--conversation-transport",
            install,
        )

    def test_s5_rule_matrix_is_scoped_as_traceability_not_complete_authority(self):
        matrix = json.loads(
            (ROOT / "docs/news-rule-matrix.json").read_text(encoding="utf-8")
        )

        self.assertEqual("traceability_snapshot", matrix["authority_status"])
        self.assertFalse(matrix["exhaustive"])
        self.assertIn("INSTALL.md", matrix["scope_en"])

    def test_public_value_v2_uses_normalized_weighted_dimensions(self):
        pool = json.loads(
            (ROOT / "news-source-pool.json").read_text(encoding="utf-8")
        )
        ranking = pool["ranking"]

        self.assertEqual("public_value_v2", ranking["method"])
        self.assertEqual(5, ranking["allowed_score_step"])
        self.assertEqual(
            100,
            sum(item["weight_percent"] for item in ranking["dimensions"].values()),
        )
        self.assertTrue(
            all(item["maximum"] == 100 for item in ranking["dimensions"].values())
        )

    def test_candidate_schema_requires_public_value_v2_evidence(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(
                encoding="utf-8"
            )
        )
        candidate = schema["$defs"]["v2Candidate"]
        required = {
            "scoring_method",
            "weighted_score",
            "consequence_evidence",
            "evidence_facts",
            "policy_stage",
            "delta_facts",
            "high_score_challenges",
            "overall_high_score_challenge",
            "cross_dimension_rationales",
            "midpoint_rationales",
            "evidence_confidence",
            "confidence_band",
            "grade_status",
        }

        self.assertTrue(required.issubset(candidate["required"]))
        for dimension in schema["$defs"]["importanceBreakdown"]["properties"].values():
            self.assertEqual(100, dimension["maximum"])

        self.assertEqual(
            "discovery_priority_v1",
            schema["$defs"]["sourceCoverage"]["properties"]["discovery_ranking_method"]["const"],
        )
        self.assertEqual(2, len(schema["$defs"]["candidate"]["anyOf"]))

    def test_historical_source_scan_receipts_do_not_require_current_run_files(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(
                encoding="utf-8"
            )
        )

        required = set(schema["$defs"]["sourceCoverage"]["required"])
        self.assertTrue(
            {"scan_window_start", "scan_window_end", "scan_evidence_path"}.isdisjoint(
                required
            )
        )

    def test_candidate_schema_accepts_mobile_compact_history_profile(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            {"$ref": "#/$defs/compactHistoricalCandidate"},
            schema["$defs"]["candidate"]["anyOf"],
        )
        compact = schema["$defs"]["compactHistoricalCandidate"]
        self.assertNotIn("grading_evidence", compact["required"])
        self.assertNotIn("source_audit", compact["required"])
        self.assertNotIn("candidate_urls", compact["required"])

    def test_prompt_source_scan_checkpoint_matches_runtime_contract(self):
        prompt = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")

        self.assertIn(
            "| `source-scan` | `source_candidates`, `relevance_gate`, "
            "`model_source_candidates` |",
            prompt,
        )

    def test_manifest_schema_requires_validated_public_value_v2_fields(self):
        schema = json.loads(
            (ROOT / "schemas/news-event-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        event = schema["$defs"]["event"]
        self.assertTrue(
            {
                "scoring_method",
                "validated_importance_score",
                "validated_grade",
                "grade_status",
                "evidence_confidence",
                "confidence_band",
            }.issubset(event["required"])
        )

    def test_install_is_complete_public_value_v2_entrypoint(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        contract = install[install.index("### Public Value V2 填寫與驗證順序"):]
        ordered_requirements = (
            "semantic_event_id",
            "consequence_evidence.realized",
            "dimension_evidence",
            "midpoint_rationales",
            "delta_facts",
            "cross_dimension_rationales",
            "high_score_challenges",
            "policy_stage",
            "evidence_confidence",
            "grade_status=validated",
            "validated_importance_score",
        )
        positions = [contract.index(requirement) for requirement in ordered_requirements]
        self.assertEqual(sorted(positions), positions)
        self.assertIn("30%／20%／15%／15%／10%／10%", install)
        self.assertIn("Reader、manifest 與 publisher 只接受 validated", install)

    def test_pre_manifest_recovery_bundle_gate_precedes_selection(self):
        required_artifacts = (
            "recovery/checkpoint.json",
            "recovery/source-candidates.json",
            "recovery/news-relevance-gate.json",
            "recovery/model-source-candidates.json",
            "recovery/preprocessed-candidates.json",
            "recovery/content-hydration-batches.json",
        )
        documents = (
            ROOT / "daily-schedule-prompt.md",
            ROOT / ".agents/skills/daily-news-brief/SKILL.md",
            ROOT / ".agents/skills/recover-news-run/SKILL.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            for marker in (
                "PRE_MANIFEST_RECOVERY_BUNDLE_GATE",
                "pack-recovery",
                "atomic tree/commit",
                "restore",
                "FIRST_SELECT_NEWS_EVENTS_EXECUTION",
                *required_artifacts,
            ):
                self.assertIn(marker, text, path.name)
            self.assertLess(
                text.index("PRE_MANIFEST_RECOVERY_BUNDLE_GATE"),
                text.index("FIRST_SELECT_NEWS_EVENTS_EXECUTION"),
                path.name,
            )

        checkpoint = (ROOT / "scripts/news_run_checkpoint.py").read_text(encoding="utf-8")
        self.assertIn('"scripts/manage_canonical_run_bundle.py"', checkpoint)

    def test_regional_supplements_have_complete_model_admission_gate(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        policy = pool["model_admission_policy"]
        self.assertEqual(["regional_supplement"], policy["complete_source_roles"])
        self.assertTrue(policy["heat_is_recall_only"])
        self.assertTrue(policy["absence_from_heat_never_excludes_complete_sources"])

        documents = (
            ROOT / "news-brief-settings.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/select-news-events/SKILL.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE", text, path.name)
            self.assertIn("validate_local_source_admission.py", text, path.name)

    def test_short_run_instruction_normalizes_regions_and_monitoring_types(self):
        documents = (
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / "news-brief-settings.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            self.assertIn("RUN_INPUT_NORMALIZATION_GATE", text, path.name)
            self.assertIn("sections", text, path.name)
            self.assertIn("topic_weights", text, path.name)

    def test_contract_documents_do_not_reintroduce_retired_reader_outline(self):
        settings = (ROOT / "news-brief-settings.md").read_text(encoding="utf-8")
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        self.assertNotIn("其後只能有三個二級標題", settings)
        self.assertNotRegex(mobile, r"(?m)^## 基礎讀者版$")
        self.assertNotRegex(mobile, r"(?m)^8\. `## 後續觀察`")

    def test_manifest_schema_allows_reader_image_omission_note(self):
        schema = json.loads(
            (ROOT / "schemas" / "news-event-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        image_properties = schema["$defs"]["imageResult"]["properties"]
        self.assertIn("reader_omission_note", image_properties)

    def test_publisher_uses_only_canonical_sectioned_reader_validator(self):
        for relative in (
            "scripts/publish_news_brief.py",
            "scripts/check_unique_delivery_gate.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("validate_canonical_reader", text)
            self.assertNotIn("validate_news_brief.validate_brief_text", text)

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
        self.assertEqual("all_verified_in_window", pool["candidate_transfer_policy"])

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

    def test_integrated_six_dimension_grading_and_conflict_context_are_explicit(self):
        settings = (ROOT / "news-brief-settings.md").read_text(encoding="utf-8")
        severity = (ROOT / ".agents/skills/select-news-events/references/severity-rubric.md").read_text(encoding="utf-8")
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for document in (settings, severity, mobile):
            self.assertIn("重要性／嚴重程度", document)
            self.assertIn("六項", document)
            self.assertIn("軍事／衝突", document)
            self.assertIn("INTEGRATED_SIX_DIMENSION_NO_HARD_CAP", document)
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
        full = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")

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
        for document in (daily, full):
            self.assertIn("scripts/materialize_news_images.py", document)
            self.assertIn("--manifest <materialized-images.json>", document)

    def test_native_media_unavailable_uses_verified_omission_without_blocking_release(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        bootstrap = (ROOT / "bootstrap-workspace.md").read_text(encoding="utf-8")

        for document in (daily, bootstrap):
            self.assertIn("NATIVE_MEDIA_CAPABILITY_FALLBACK", document)
            self.assertIn("verified image evidence", document)
            self.assertIn("reader_omission_note", document)
        self.assertIn("不得因宿主缺少原生媒體能力阻擋正式文字交付", daily)
        self.assertNotIn("只把圖片交付切換到既有 full-runtime", daily)
        self.assertIn("先實際嘗試", daily)
        self.assertIn("下載失敗", daily)
        self.assertIn("截圖", daily)
        self.assertIn("status=completed", daily)
        self.assertNotIn("若必要地圖或附件仍需 full-runtime，保持 `status=running`", daily)
        self.assertNotIn("不得標記 canonical completed", daily)

    def test_empty_audit_baseline_is_not_claimed_as_fourteen_day_complete(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        self.assertIn("FOURTEEN_DAY_AUDIT_COMPLETENESS_GATE", daily)
        self.assertIn("空的 `runs` 陣列", daily)
        self.assertIn("不得宣告十四天清單已完成", daily)

    def test_mobile_images_search_multiple_same_event_sources_before_degrading(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")

        for requirement in (
            "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
            "可檢查多個來源",
            "不限一個",
            "其他可靠媒體",
            "只重做該則圖片取得／交付",
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

        discovery = pool["discovery_sources"]
        self.assertEqual(["gdelt", "cna", "chinanews"], [item["source_id"] for item in discovery])
        for retired_key in ("sources", "section_sources", "primary_sources_per_section"):
            self.assertNotIn(retired_key, pool)
        self.assertFalse((ROOT / "source-health-profile.json").exists())
        self.assertEqual(1, pool["discovery_policy"]["minimum_ready_sources"])
        self.assertEqual("degrade_not_block", pool["discovery_policy"]["source_failure_policy"])
        self.assertEqual("all_verified_in_window", pool["candidate_transfer_policy"])
        self.assertTrue(pool["verification_policy"]["after_scoring"])
        self.assertTrue(pool["verification_policy"]["images_after_verification"])

        route_config = json.loads(
            (ROOT / "source-route-config.json").read_text(encoding="utf-8")
        )
        gdelt = next(
            route for route in route_config["routes"] if route["source_id"] == "gdelt"
        )
        self.assertEqual(1, gdelt["max_attempts"])
        self.assertEqual(
            ["gdelt_export_24h", "doc_api_optional", "last_known_good_cache"],
            gdelt["acquisition_order"],
        )
        self.assertEqual("gdelt_export_24h", gdelt["fallback"]["type"])
        for document in (daily, scheduled):
            self.assertIn("GDELT_RESILIENT_ACQUISITION", document)
            self.assertIn("FULL_DISCOVERY_POOL_UNCAPPED", document)
            self.assertIn("15-minute", document)

    def test_install_is_the_complete_and_consistent_entry_point(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        for requirement in (
            "文件權責與讀取順序",
            "完整每日執行流程",
            "必填產物與驗證",
            "執行模式與完成條件",
            "NATIVE_MEDIA_UNAVAILABLE",
            "reader-canonical-capability-degraded",
            "# 每日新聞讀者版",
            "PRE_MANIFEST_RECOVERY_BUNDLE_GATE",
            "recover_news_run.py plan",
            "--bootstrap-receipt",
        ):
            self.assertIn(requirement, install)
        for skill in (
            "acquire-news-candidates", "select-news-events", "audit-news-candidates",
            "verify-news-events", "build-news-maps", "build-news-charts",
            "collect-news-images", "recover-news-run", "daily-news-brief",
        ):
            self.assertIn(f".agents/skills/{skill}/SKILL.md", install)
        self.assertNotIn("YYYY/MM/DD 每日新聞`；下一行", install)

    def test_candidate_discovery_uses_dynamic_verification_selection(self):
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
            "任一來源未完成、未按站內前 30 則",
            "prevalidated daily-news sources",
        )
        for label, document in documents.items():
            for phrase in forbidden:
                self.assertNotIn(phrase, document, f"{label} retains a retired gate")

        schema = json.loads(
            (ROOT / "schemas" / "news-source-candidate-list.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual({"type": "integer", "minimum": 1}, schema["properties"]["source_count"])
        self.assertEqual(1, schema["properties"]["sources"]["minItems"])
        self.assertNotIn("maxItems", schema["properties"]["sources"])

    def test_configured_discovery_routes_are_candidate_schema_admissible(self):
        route_config = json.loads(
            (ROOT / "source-route-config.json").read_text(encoding="utf-8")
        )
        schema = json.loads(
            (ROOT / "schemas" / "news-source-candidate-list.schema.json").read_text(
                encoding="utf-8"
            )
        )

        configured_routes = {route["route"] for route in route_config["routes"]}
        admissible_routes = set(
            schema["properties"]["items"]["items"]["properties"]
            ["acquisition_route"]["enum"]
        )

        self.assertLessEqual(configured_routes, admissible_routes)

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
            "CANONICAL_TODAY_OVERVIEW_NO_OMISSION_GATE",
            "CANONICAL_SECTIONED_READER_LAYOUT_GATE",
            "news-brief-template.md",
            "每日新聞讀者版",
            "時間｜事件｜評級",
            "不得省略、跨區集中或重新設計",
            "--reader-layout canonical-sectioned",
        ):
            self.assertIn(requirement, daily)

    def test_reader_excludes_internal_repair_log(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        template = (ROOT / "news-brief-template.md").read_text(encoding="utf-8")

        for document in (daily, template):
            self.assertIn("READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE", document)
            self.assertIn("修復紀錄", document)
            self.assertIn("不得出現在讀者版", document)

    def test_reader_preserves_canonical_sectioned_story_layout(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        scheduled = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        template = (ROOT / "news-brief-template.md").read_text(encoding="utf-8")

        for document in (daily, scheduled):
            self.assertIn("CANONICAL_SECTIONED_READER_LAYOUT_GATE", document)
            self.assertIn("不得改成欄位式逐條詳報", document)
        for requirement in (
            "# 每日新聞讀者版",
            "統計期間：",
            "評級綜合考量：",
            "## 今日總覽",
            "## 🇹🇼 台灣新聞",
            "| 時間 | 事件 | 評級 |",
            "### 事件名稱｜A",
            "評為A級",
        ):
            self.assertIn(requirement, template)
        for forbidden_example in (
            "### TWN-01. 事件名稱 - A",
            "**時間：**新聞時間：",
            "**事件細節：**說明發生什麼",
            "**分析：**說明真正值得注意",
        ):
            self.assertNotIn(forbidden_example, template)

    def test_canonical_run_bundle_persists_recomputable_audit_and_image_evidence(self):
        scheduled = (ROOT / "daily-schedule-prompt.md").read_text(encoding="utf-8")
        matrix = (ROOT / "docs/news-rule-matrix.json").read_text(encoding="utf-8")
        for requirement in (
            "CANONICAL_RUN_BUNDLE_GATE",
            "candidate-audit.json",
            "article_dispositions",
            "image-evidence/",
            "materialized-images.json",
            "logs/current.json",
            "byte identity",
        ):
            self.assertIn(requirement, scheduled)
        for requirement in (
            "scripts/manage_canonical_run_bundle.py",
            "storage.mode=chunked",
            "encoding=base64",
            "atomic tree/commit",
        ):
            self.assertIn(requirement, scheduled)
            self.assertIn(requirement, matrix)

    def test_mobile_increment_recovers_without_blocking_daily_reader(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        ledger = (ROOT / "docs/mobile-run-ledger.md").read_text(encoding="utf-8")

        for requirement in (
            "TYPE_CONSISTENT_COVERAGE_SANITY",
            "不得拿前輪來源掃描的 `raw_item_count`",
            "RECOVERABLE_14_DAY_BASELINE_WITHOUT_READER_BLOCK",
            "不得因此阻止本日讀者版",
            "DAILY_COVERAGE_IS_NOT_HISTORICAL_PROOF",
            "不得把可用、來源可核對且符合模板的每日讀者版改判失敗",
        ):
            self.assertIn(requirement, daily)

        for document in (daily, install, ledger):
            self.assertIn("FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE", document)
            self.assertIn("run-scoped candidate audit", document)
        for document in (daily, install):
            self.assertIn("不得設為 `last_error`", document)
        self.assertIn("must not be set as `last_error`", ledger)
        self.assertIn("COUNT_RECEIPT_REPAIR_ONCE", daily)
        self.assertIn("直接依 `events` 陣列重算並覆寫", daily)
        self.assertIn("不得把 32/33 這類可重算差額升級為整輪失敗", daily)
        self.assertNotIn("本輪完整十四天海選清單寫入", daily)
        self.assertNotIn("本輪及十四天清單內所有 C 級以上新聞", daily)

    def test_mobile_native_rolls_forward_only_current_schema_history(self):
        daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        skill = (ROOT / ".agents/skills/audit-news-candidates/SKILL.md").read_text(
            encoding="utf-8"
        )

        for document in (daily, skill):
            for requirement in (
                "MOBILE_NATIVE_AUDIT_ROLLING_MERGE",
                "CURRENT_SCHEMA_ONLY_DURABLE_AUDIT",
                "不相容物件不合併",
                "GitHub contents API 整檔 replacement",
                "不得因此阻止本日讀者版",
            ):
                self.assertIn(requirement, document)
        self.assertIn("只重評本輪新增或有實質更新的候選", daily)
        self.assertIn("full-runtime", skill)
        self.assertIn("mobile-native", skill)

    def test_candidate_audit_schema_has_unbounded_raw_count_and_stage_receipt(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(encoding="utf-8")
        )
        run = schema["$defs"]["run"]
        self.assertNotIn("maximum", run["properties"]["raw_item_count"])
        self.assertNotIn("processing_counts", run["required"])
        required = set(run["properties"]["processing_counts"]["required"])
        self.assertEqual({
            "merged_article_row_count",
            "in_window_article_row_count",
            "canonical_url_count",
            "provisional_title_cluster_count",
            "semantic_event_count",
            "scored_event_count",
            "c_or_higher_scored_event_count",
            "selected_event_count",
            "event_evidence_article_row_count",
            "non_news_article_row_count",
            "unresolved_article_row_count",
        }, required)
        for document_path in (
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/audit-news-candidates/SKILL.md",
        ):
            document = document_path.read_text(encoding="utf-8")
            self.assertIn("PIPELINE_COUNT_RECEIPT", document)
            self.assertNotIn("PIPELINE_COUNT_RECEIPT_" + "V1", document)
            self.assertIn("文章列數不得稱為語意事件數", document)
            for field in required:
                self.assertIn(f"`{field}`", document)

    def test_semantic_event_ledger_schema_contract(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(encoding="utf-8")
        )
        run = schema["$defs"]["run"]
        dispositions = run["properties"]["article_dispositions"]
        self.assertEqual("#/$defs/articleDisposition", dispositions["items"]["$ref"])
        self.assertEqual(
            ["event_evidence", "non_news", "unresolved"],
            schema["$defs"]["articleDisposition"]["properties"]["disposition"]["enum"],
        )
        candidate_required = set(schema["$defs"]["v2Candidate"]["required"])
        self.assertNotIn("semantic_event_id", candidate_required)
        self.assertNotIn("event_identity", candidate_required)
        self.assertIn("semantic_event_id", schema["$defs"]["v2Candidate"]["properties"])
        self.assertIn("event_identity", schema["$defs"]["v2Candidate"]["properties"])
        self.assertEqual({
            "who_or_what", "what_happened", "where", "when", "semantic_merge_basis"
        }, set(schema["$defs"]["eventIdentity"]["required"]))
        count_fields = set(run["properties"]["processing_counts"]["required"])
        self.assertTrue({
            "event_evidence_article_row_count",
            "non_news_article_row_count",
            "unresolved_article_row_count",
        }.issubset(count_fields))
        for document_path in (
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/daily-news-brief/SKILL.md",
            ROOT / ".agents/skills/select-news-events/SKILL.md",
            ROOT / ".agents/skills/audit-news-candidates/SKILL.md",
        ):
            document = document_path.read_text(encoding="utf-8")
            self.assertIn("SEMANTIC_EVENT_LEDGER_GATE", document)
            self.assertIn("只有語意事件才算新聞", document)
            self.assertIn("`article_dispositions`", document)
            self.assertIn("`semantic_event_id`", document)
            self.assertIn("`event_identity`", document)

    def test_event_region_and_time_identity_gate_contract(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(encoding="utf-8")
        )
        identity = schema["$defs"]["eventIdentity"]
        structured_fields = {
            "country_codes", "primary_country_code", "location_evidence",
            "event_occurred_at", "material_update_at", "material_update_type",
            "material_update_evidence",
        }
        self.assertTrue(structured_fields.issubset(identity["properties"]))
        temporal_review = identity["properties"]["temporal_review"]
        self.assertEqual("model_content_comparison", temporal_review["properties"]["review_method"]["const"])
        self.assertIn("ongoing_current_impact", temporal_review["properties"]["window_status"]["enum"])
        self.assertIn("old_restatement", temporal_review["properties"]["window_status"]["enum"])
        documents = (
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / "news-brief-settings.md",
            ROOT / ".agents/skills/daily-news-brief/SKILL.md",
            ROOT / ".agents/skills/select-news-events/SKILL.md",
            ROOT / ".agents/skills/audit-news-candidates/SKILL.md",
        )
        for path in documents:
            document = path.read_text(encoding="utf-8")
            self.assertIn("EVENT_REGION_AND_TIME_IDENTITY_GATE", document)
            self.assertIn("來源分桶", document)
            self.assertIn("`event_occurred_at`", document)
            self.assertIn("`material_update_at`", document)
            self.assertIn("舊事件", document)
            self.assertIn("模型", document)
            self.assertIn("`temporal_review`", document)

    def test_policy_governance_evidence_gate_contract(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(encoding="utf-8")
        )
        review = schema["$defs"]["policyGovernanceReview"]
        self.assertIn("score_consistency_review", review["properties"])
        self.assertIn(
            "policy_governance_review",
            schema["$defs"]["v2Candidate"]["properties"]["grading_evidence"]["properties"],
        )
        documents = (
            ROOT / "news-brief-settings.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / ".agents/skills/select-news-events/SKILL.md",
        )
        for path in documents:
            document = path.read_text(encoding="utf-8")
            self.assertIn("POLICY_GOVERNANCE_EVIDENCE_GATE", document, path.name)
            self.assertIn("`policy_governance_review`", document, path.name)
            self.assertIn("`why_not_b`", document, path.name)
            self.assertIn("必須退回重審", document, path.name)
            self.assertIn("未經證實", document, path.name)

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
            "dimension_evidence",
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
                "事件年齡本身不得設定日數等級上限",
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
