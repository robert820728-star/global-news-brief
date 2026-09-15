import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchedulePromptControlPlaneTests(unittest.TestCase):
    def test_every_paste_ready_starter_delegates_to_fresh_install_contract(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        mobile = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(
            encoding="utf-8"
        )
        starters = {
            "INSTALL.md": install.split("在全新對話貼上：", 1)[1].split(
                "收到後", 1
            )[0],
            "README.md": readme.split("> 每日新聞排程", 1)[1].split(
                "安裝時確認", 1
            )[0],
            "mobile-chatgpt-start-prompt.md": mobile.split("```text", 1)[1].split(
                "```", 1
            )[0],
        }

        for name, starter in starters.items():
            with self.subTest(document=name):
                for requirement in (
                    "robert820728-star/global-news-brief",
                    "fresh resolve 最新 main",
                    "完整遵循",
                    "台灣、中國、世界",
                    "每天 06:00",
                    "目前這個對話",
                    "不得建立重複排程",
                ):
                    self.assertIn(requirement, starter)

                self.assertNotIn("new_without_exact_id", starter)
                self.assertNotIn("authoritative task inventory", starter)

    def test_singleton_starter_can_adopt_or_create_without_blind_duplication(self):
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        prompt = starter.split("```text", 1)[1].split("```", 1)[0]

        self.assertIn("只有一個", prompt)
        self.assertIn("若已有符合排程就更新", prompt)
        self.assertIn("不得建立重複排程", prompt)
        self.assertNotIn("本次安裝意圖：create_new", prompt)
        self.assertNotIn("authoritative task inventory", prompt)

    def test_install_payload_builder_keeps_diagnostics_outside_saved_prompt(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in ("INSTALL.md", "README.md", "mobile-chatgpt-start-prompt.md")
        }
        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn("build_scheduled_task_install_payload.py", document)
                self.assertIn("install-extension.json", document)
                self.assertIn("不得寫入 saved-prompt.txt", document)

        example = json.loads(
            (ROOT / "scheduled-task-test-extension.example.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("installation_only", example["scope"])
        self.assertFalse(example["saved_prompt_mutation_allowed"])
        self.assertEqual(171909, example["smoke_fixture"]["expected_byte_size"])
        self.assertEqual(1024, example["smoke_fixture"]["expected_width"])
        self.assertEqual(478, example["smoke_fixture"]["expected_height"])
        self.assertEqual(
            "6262c2e8d26f1881e8a2aeb800a13820f23c6192f42d5d7e8152709f7ccbb8c1",
            example["smoke_fixture"]["expected_sha256"],
        )

    def test_prompt_verification_is_capability_aware_and_nonblocking_after_ack(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "INSTALL.md",
                "README.md",
                "mobile-chatgpt-start-prompt.md",
                "daily-schedule-prompt.md",
            )
        }

        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn(
                    "SCHEDULE_PROMPT_CAPABILITY_AWARE_VERIFICATION_GATE", document
                )

        install = documents["INSTALL.md"]
        for requirement in (
            "支援 saved-prompt readback",
            "exact task ID",
            "完整 prompt",
            "每天 06:00",
            "目前對話",
            "verification_partial",
            "不得倒判 create／update 失敗",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertNotIn("再讀回並逐字比較；", install)
        self.assertNotIn("先更新並讀回完整 task prompt", install)

    def test_only_exact_id_same_control_plane_can_contradict_create_success(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("SCHEDULE_PROMPT_EXACT_ID_READBACK_ONLY_GATE", install)
        for requirement in (
            "同一控制面",
            "exact task ID",
            "一般 list／search 回傳空集合",
            "不得推翻正式 create／update 成功回傳",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertIn("exact-ID view 明確回傳不存在時才把安裝改列失敗", install)
        self.assertIn("內容不一致時只對同一 ID 冪等重送", install)

    def test_paste_ready_starter_is_concise_and_capability_aware(self):
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        prompt = starter.split("```text", 1)[1].split("```", 1)[0].strip()

        self.assertLess(len(prompt), 700)
        for requirement in (
            "每天 06:00",
            "台灣、中國、世界",
            "監控類型：預設",
            "目前這個對話",
            "更新同名既有排程",
        ):
            self.assertIn(requirement, starter)

        self.assertIn("fresh resolve 最新 main", prompt)
        self.assertIn("完整遵循 INSTALL.md", prompt)
        self.assertIn("不得建立重複排程", prompt)
        self.assertNotIn("仍不一致或無法讀回時，不得宣稱排程設置完成", starter)

    def test_fresh_conversation_uses_capability_aware_singleton_transaction(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        prompt = starter.split("```text", 1)[1].split("```", 1)[0].strip()

        self.assertIn("SINGLETON_SCHEDULE_INSTALL_GATE", install)
        self.assertIn("只有一個", prompt)

        for requirement in (
            "present",
            "absent",
            "multiple_present",
            "unknown",
            "authoritative task inventory",
            "恰有一個",
            "證明不存在",
            "不得盲建",
            "不得再次 create",
            "update_existing 必須先有 exact task ID",
            "actual control-plane error",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertNotIn("create_new 不得把同名 list／search 當成首次 create 的必要前置", install)
        self.assertNotIn("authoritative task inventory", prompt)

    def test_install_fast_path_reaches_control_plane_before_runtime_contracts(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")

        for document in (install, starter):
            self.assertIn("INSTALL_CONTROL_PLANE_FAST_PATH", document)
            self.assertIn("新聞 runtime 文件", document)
            self.assertIn("第一次 create／update", document)

        self.assertIn("只讀安裝必要檔案", starter)

    def test_current_conversation_binding_uses_available_control_plane_evidence(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")

        for document in (install, starter):
            self.assertIn("目前對話內的正式 task 回傳或 task 卡", document)
            self.assertIn("不要求不存在的 destination 欄位", document)

        self.assertNotIn("沒有回傳 destination 欄位即失敗", install)

    def test_prompt_is_updated_before_any_media_smoke(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        update = install.index("SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE")
        smoke = install.index("SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE")
        self.assertLess(update, smoke)
        self.assertIn("舊 prompt 不得繼續啟用", install)
        self.assertIn("不得因後續 smoke／readback 診斷失敗而被暫停", install)

    def test_install_smoke_does_not_require_repository_bootstrap(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        block = install[
            install.index("SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE") :
            install.index("## Scheduled Task 排程指令唯一契約")
        ]
        self.assertNotIn("maps/generated/taiwan-counties-yellow-v2.png", block)
        self.assertIn("不得要求 verified workspace", block)
        self.assertIn("直接截圖", block)

    def test_install_smoke_is_not_a_scheduled_occurrence_trigger(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(
            encoding="utf-8"
        )

        for document in (install, starter):
            self.assertIn("在建立或更新排程的目前對話直接執行", document)
            self.assertIn("不是 Scheduled Task occurrence", document)
            self.assertIn("不要求立即觸發指定 task ID", document)

        self.assertNotIn("等待 Scheduled Task occurrence", starter)

    def test_install_smoke_rejects_serialized_content_references(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "INSTALL.md",
                "mobile-chatgpt-start-prompt.md",
            )
        }

        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn("NON_TEXT_SMOKE_OUTPUT_GATE", document)
                self.assertIn("!:chatgpt-content-reference", document)
                self.assertIn("attachments=[]", document)
                self.assertIn("不能單獨否定", document)
                self.assertIn("不得宣稱 smoke 通過", document)

    def test_relative_one_time_schedule_uses_one_acknowledged_mutation(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

        self.assertIn("RELATIVE_ONE_TIME_SCHEDULE_ANCHOR_GATE", install)
        for requirement in (
            "當下控制面時間",
            "最終絕對執行時間",
            "同一 mutation",
            "enabled=true",
            "成功回傳 exact task ID",
            "next_run_time",
            "verification_partial",
            "不得因 null／缺失 readback 停用",
            "不得用人工 follow-up 冒充 Scheduled Task occurrence",
            "正式每日 06:00 排程不適用",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertNotIn("一次 fresh-create fallback", install)

    def test_saved_task_template_probes_media_routes_independently(self):
        prompt = (ROOT / "scheduled-task-prompt-template.md").read_text(encoding="utf-8")
        self.assertIn("INDEPENDENT_VISIBLE_MEDIA_CAPABILITY_PROBE", prompt)
        self.assertIn("page_open", prompt)
        self.assertIn("webpage_region_screenshot", prompt)
        self.assertIn("不得推導", prompt)
        self.assertIn("不要求原始檔或原畫質", prompt)
        self.assertNotIn("maps/generated/taiwan-counties-yellow-v2.png", prompt)
        self.assertNotIn("只能在已通過", prompt)

    def test_scheduled_host_path_is_active_and_cannot_degrade_after_discovery(self):
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        self.assertIn("SCHEDULED_HOST_VISIBLE_SCREENSHOT_ROUTE", mobile)
        self.assertIn("不得在 discovery 後宣告 NATIVE_MEDIA_UNAVAILABLE", mobile)
        self.assertNotIn("本檔只保留給 mobile-native 的流程外能力診斷", mobile)
        self.assertIn("直接截圖", mobile)

    def test_chat_continuation_is_not_a_scheduled_occurrence(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "INSTALL.md",
                "README.md",
                "scheduled-task-prompt-template.md",
                "daily-schedule-prompt.md",
                "mobile-chatgpt-start-prompt.md",
                "mobile-chatgpt-daily-prompt.md",
                ".agents/skills/daily-news-brief/SKILL.md",
            )
        }

        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn(
                    "CHAT_CONTINUATION_IS_NOT_SCHEDULED_OCCURRENCE_GATE",
                    document,
                )
                self.assertIn("scheduled_for", document)
                self.assertIn("重新執行", document)
                self.assertIn("lifecycle blocker receipt", document)

        prompt = documents["scheduled-task-prompt-template.md"]
        self.assertIn("不得 fresh resolve main", prompt)
        self.assertIn("不得建立或恢復 run", prompt)
        self.assertIn("不得執行新聞 discovery", prompt)
        self.assertIn("不得輸出 Reader", prompt)

    def test_verified_scheduled_host_start_is_the_only_scheduled_for_fallback(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "INSTALL.md",
                "scheduled-task-prompt-template.md",
                "daily-schedule-prompt.md",
                "mobile-chatgpt-daily-prompt.md",
                ".agents/skills/daily-news-brief/SKILL.md",
            )
        }
        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn("VERIFIED_SCHEDULED_HOST_START_FALLBACK", document)
                self.assertIn("exact task ID", document)
                self.assertIn("首次實際執行時間", document)
                self.assertIn("scheduled_for", document)
                self.assertIn("一般對話", document)

    def test_runtime_occurrence_cannot_mutate_formal_daily_task(self):
        runtime_documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "scheduled-task-prompt-template.md",
                "daily-schedule-prompt.md",
                "mobile-chatgpt-daily-prompt.md",
                ".agents/skills/daily-news-brief/SKILL.md",
            )
        }
        for name, document in runtime_documents.items():
            with self.subTest(document=name):
                self.assertIn("FORMAL_DAILY_TASK_RUNTIME_IMMUTABILITY_GATE", document)
                self.assertIn("正式每日 06:00", document)
                self.assertIn(
                    "create／update／pause／disable／delete／reschedule／replace",
                    document,
                )
                self.assertIn("只能更新同一 run", document)
                self.assertIn("不得停用", document)

    def test_installation_task_mutation_is_scoped_outside_runtime_occurrence(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("FORMAL_DAILY_TASK_RUNTIME_IMMUTABILITY_GATE", install)
        self.assertIn("安裝／修復控制面", install)
        self.assertIn("尚未開始 occurrence", install)
        self.assertIn("執行期 occurrence", install)
        self.assertIn("只能更新同一 run", install)

    def test_context_loss_resumes_same_install_transaction_from_authorities(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        starters = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "README.md",
                "mobile-chatgpt-start-prompt.md",
            )
        }

        self.assertIn("INSTALL_CONTEXT_LOSS_RECOVERY_GATE", install)
        for requirement in (
            "上下文截斷",
            "同一安裝 transaction",
            "已鎖定的 immutable SHA",
            "exact task ID 仍可識別",
            "重建 canonical prompt 與 fingerprint",
            "enabled",
            "每天 06:00",
            "帳號時區",
            "目前對話",
            "不得重新 inventory",
            "不得再次 create",
            "不得改用新 main",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertIn("known_exact_id_resume 可對同一 exact task ID 冪等提交", install)
        self.assertIn("readback 遺失只記為 `verification_partial`", install)
        for name, document in starters.items():
            with self.subTest(starter=name):
                self.assertIn("POST_INSTALL_DIAGNOSTICS_GATE", document)
                self.assertIn("verification_partial", document)

    def test_control_plane_entry_is_state_disjoint_after_context_loss(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "INSTALL.md",
                "README.md",
                "mobile-chatgpt-start-prompt.md",
                "daily-schedule-prompt.md",
            )
        }

        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn("new_without_exact_id", document)
                self.assertIn("known_exact_id_resume", document)
                self.assertIn("create_outcome_unknown", document)

        install = documents["INSTALL.md"]
        self.assertIn(
            "new_without_exact_id 才以 authoritative task inventory 作為第一個控制面操作",
            install,
        )
        self.assertIn(
            "known_exact_id_resume 只處理同一 exact task ID",
            install,
        )
        self.assertIn(
            "create_outcome_unknown 只依原 operation identity 查明第一次結果",
            install,
        )
        self.assertNotIn(
            "main pin 與 outbound payload 驗證後，第一個控制面操作必須是",
            install,
        )
        self.assertIn(
            "入口狀態解析完成後的第一個 mutation",
            install,
        )
        self.assertNotIn("控制面第一步必須先把", install)

    def test_acknowledged_install_is_usable_before_optional_diagnostics(self):
        documents = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "INSTALL.md",
                "README.md",
                "mobile-chatgpt-start-prompt.md",
                "daily-schedule-prompt.md",
            )
        }

        for name, document in documents.items():
            with self.subTest(document=name):
                self.assertIn("USABLE_FIRST_SCHEDULE_INSTALL_GATE", document)
                self.assertIn("POST_INSTALL_DIAGNOSTICS_GATE", document)
                self.assertIn("verification_partial", document)

        install = documents["INSTALL.md"]
        self.assertIn("成功回傳 exact task ID", install)
        self.assertIn("enabled=true", install)
        self.assertIn("同一 exact task ID 冪等", install)
        self.assertIn("不得暫停、停用、刪除、重建或另建正式 task", install)
        self.assertNotIn("smoke 通過才啟用", install)
        self.assertNotIn("後續 smoke 失敗時保留最新版 prompt 並暫停", install)
        self.assertNotIn("暫停 smoke 失敗的 candidate", install)
        self.assertNotIn("readback 回傳內容遺失不得授權 update", install)

    def test_paste_ready_starter_delegates_internal_state_machine_to_install(self):
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        prompt = starter.split("```text", 1)[1].split("```", 1)[0].strip()

        self.assertLess(len(prompt), 700)
        for requirement in (
            "robert820728-star/global-news-brief",
            "台灣、中國、世界",
            "監控類型：預設",
            "每天 06:00",
            "目前這個對話",
            "fresh resolve 最新 main",
            "完整遵循 INSTALL.md",
            "不得建立重複排程",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, prompt)

        for internal_detail in (
            "IMMUTABLE_INSTALL_MAIN_RESOLUTION_GATE",
            "new_without_exact_id",
            "known_exact_id_resume",
            "create_outcome_unknown",
            "multiple_present",
            "authoritative task inventory",
        ):
            with self.subTest(internal_detail=internal_detail):
                self.assertNotIn(internal_detail, prompt)


if __name__ == "__main__":
    unittest.main()

