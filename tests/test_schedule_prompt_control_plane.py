import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchedulePromptControlPlaneTests(unittest.TestCase):
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

    def test_prompt_verification_is_capability_aware_without_becoming_best_effort(self):
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
            "明確不提供 saved-prompt readback",
            "task ID",
            "完整 prompt",
            "每天 06:00",
            "目前對話",
            "不得盲建重複排程",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertNotIn("再讀回並逐字比較；", install)
        self.assertNotIn("先更新並讀回完整 task prompt", install)

    def test_only_exact_id_same_control_plane_readback_can_negate_create_success(self):
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

        self.assertIn("只有 exact-ID view 明確回傳不存在或內容不一致", install)

    def test_paste_ready_starter_is_concise_and_capability_aware(self):
        starter = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        prompt = starter.split("```text", 1)[1].split("```", 1)[0].strip()

        self.assertLess(len(prompt), 1400)
        for requirement in (
            "每天 06:00",
            "台灣、中國、世界",
            "監控類型：預設",
            "目前這個對話",
            "更新同名既有排程",
        ):
            self.assertIn(requirement, starter)

        self.assertIn("同一控制面的 exact task ID", prompt)
        self.assertIn("正式 create／update 回傳", prompt)
        self.assertIn("一般 list／search 空結果", prompt)
        self.assertNotIn("仍不一致或無法讀回時，不得宣稱排程設置完成", starter)

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

    def test_relative_one_time_schedule_requires_persisted_future_trigger_evidence(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

        self.assertIn("RELATIVE_ONE_TIME_SCHEDULE_ANCHOR_GATE", install)
        for requirement in (
            "對話開始時間",
            "安裝 smoke 完成後",
            "啟用前",
            "當下控制面時間",
            "next_run_time",
            "非 null 時",
            "仍晚於讀回當下時間",
            "為 null 時，安裝尚未驗證",
            "不得宣稱排程已完成",
            "停用同一 exact task ID",
            "一次 fresh-create fallback",
            "最終絕對執行時間",
            "再次讀回",
            "仍為 null",
            "trigger／persistence failure",
            "不得等待已錯過的時間點",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, install)

        self.assertNotIn("為 null 時不得停用", install)
        self.assertNotIn("不得把 null 單獨判定為觸發失敗", install)

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


if __name__ == "__main__":
    unittest.main()

