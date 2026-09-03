import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FaultPenetrationContractTests(unittest.TestCase):
    def test_bootstrap_transport_failure_routes_same_occurrence_to_mobile(self):
        daily = read("daily-schedule-prompt.md")
        install = read("INSTALL.md")
        bootstrap = read("bootstrap-workspace.md")

        for document in (daily, install, bootstrap):
            self.assertIn("BOOTSTRAP_TRANSPORT_DOWNGRADE_GATE", document)
            self.assertIn("same occurrence", document)
            self.assertIn("mobile-native", document)

        self.assertNotIn("不得改走 production `mobile-native`", daily)
        self.assertNotIn("不得改走 mobile-native", install)

    def test_execution_bootstrap_and_workspace_capabilities_are_independent(self):
        for path in ("daily-schedule-prompt.md", "INSTALL.md", "bootstrap-workspace.md"):
            document = read(path)
            for marker in (
                "local_execution_capable",
                "bootstrap_transport_capable",
                "verified_workspace_ready",
            ):
                self.assertIn(marker, document, path)

        bootstrap = read("bootstrap-workspace.md")
        self.assertIn("only after full-runtime remains selected", bootstrap)

    def test_schedule_and_timezone_are_occurrence_authority(self):
        mobile = read("mobile-chatgpt-daily-prompt.md")
        self.assertIn("SCHEDULE_AND_TIMEZONE_OCCURRENCE_AUTHORITY", mobile)
        self.assertIn("task／occurrence", mobile)
        self.assertNotIn("排程：每天 06:00，`Asia/Taipei`", mobile)

    def test_visible_media_capabilities_are_probed_independently(self):
        paths = (
            "INSTALL.md",
            "scheduled-task-prompt-template.md",
            "mobile-chatgpt-daily-prompt.md",
            "news-brief-settings.md",
            ".agents/skills/collect-news-images/SKILL.md",
        )
        markers = (
            "native_image_search",
            "webpage_region_screenshot",
            "source_media_byte_fetch",
            "local_attachment_media_handoff",
        )
        for path in paths:
            document = read(path)
            self.assertIn("INDEPENDENT_VISIBLE_MEDIA_CAPABILITY_PROBE", document, path)
            for marker in markers:
                self.assertIn(marker, document, path)
            self.assertIn("page_open", document, path)
            self.assertIn("不得推導", document, path)

    def test_local_attachment_requires_complete_verified_media_pipeline(self):
        paths = (
            "INSTALL.md",
            "scheduled-task-prompt-template.md",
            "daily-schedule-prompt.md",
            "mobile-chatgpt-daily-prompt.md",
            "news-brief-settings.md",
            ".agents/skills/collect-news-images/SKILL.md",
        )
        for path in paths:
            document = read(path)
            self.assertIn("VERIFIED_LOCAL_MEDIA_PIPELINE_ROUTE", document, path)
            self.assertIn("source_media_byte_fetch", document, path)
            self.assertIn("local_attachment_media_handoff", document, path)
            self.assertNotIn("LOCAL_ATTACHMENT_FIRST_WHEN_RUNTIME_AVAILABLE_GATE", document, path)

    def test_mobile_discovery_has_executable_degraded_adapters_and_freshness_gate(self):
        mobile = read("mobile-chatgpt-daily-prompt.md")
        for marker in (
            "MOBILE_DISCOVERY_TRANSPORT_ADAPTERS",
            "ARTICLE_BODY_TIMESTAMP_AUTHORITY_GATE",
            "SEARCH_OPEN_FRESHNESS_CONSISTENCY_GATE",
        ):
            self.assertIn(marker, mobile)
        for source in ("GDELT", "CNA", "China News Service"):
            self.assertIn(source, mobile)
        self.assertIn("degraded_partial", mobile)
        self.assertIn("文章本體", mobile)
        self.assertIn("stale-open", mobile)

    def test_reader_text_bytes_and_native_media_have_ordered_anchor_contract(self):
        for path in (
            "INSTALL.md",
            "scheduled-task-prompt-template.md",
            "mobile-chatgpt-daily-prompt.md",
        ):
            document = read(path)
            self.assertIn("MULTIMODAL_READER_ORDERED_BLOCK_CONTRACT", document, path)
            self.assertIn("串接所有 text blocks", document, path)
            self.assertIn("media anchor", document, path)
            self.assertIn("caption", document, path)

    def test_old_audit_schema_is_preserved_without_blocking_today_reader(self):
        mobile = read("mobile-chatgpt-daily-prompt.md")
        self.assertIn("CURRENT_SCHEMA_ONLY_DURABLE_AUDIT", mobile)
        self.assertIn("不相容物件不合併", mobile)
        self.assertIn("Git history", mobile)
        self.assertIn("不得因此阻止本日讀者版", mobile)


if __name__ == "__main__":
    unittest.main()
