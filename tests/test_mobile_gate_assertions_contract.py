import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import mobile_gate_assertions

class MobileGateAssertionsContractTests(unittest.TestCase):
    def test_registry_matches_schema_runtime_and_mobile_prompt(self):
        schema = json.loads((ROOT / "schemas/mobile-gate-assertions.schema.json").read_text(encoding="utf-8"))
        schema_ids = schema["properties"]["assertions"]["items"]["properties"]["contract_id"]["enum"]
        prompt = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        block = prompt.split("`MOBILE_MANDATORY_GATE_REGISTRY`", 1)[1].split("每筆 assertion", 1)[0]
        prompt_ids = re.findall(r"^- `([A-Z0-9_]+)`$", block, re.MULTILINE)
        self.assertEqual(list(mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS), schema_ids)
        self.assertEqual(list(mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS), prompt_ids)
        self.assertEqual(len(prompt_ids), len(set(prompt_ids)))
        for contract_id in mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS:
            self.assertIn(f"`{contract_id}`", prompt)
        for required in (
            "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
            "DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE",
            "IMAGE_FALLBACK_EXHAUSTION_GATE",
            "IMAGE_READER_VISIBLE_DELIVERY_GATE",
            "NATIVE_MEDIA_BLOCK_DELIVERY_GATE",
            "QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL",
            "VISUAL_DELIVERY_ONLY_RECOVERY",
        ):
            self.assertIn(required, mobile_gate_assertions.IMAGE_CONTRACT_IDS)

    def test_active_authorities_require_release_assertion(self):
        for relative in (
            "INSTALL.md", "mobile-chatgpt-daily-prompt.md", "news-brief-settings.md",
            ".agents/skills/daily-news-brief/SKILL.md", ".agents/skills/recover-news-run/SKILL.md",
        ):
            self.assertIn("MANDATORY_GATE_EXECUTION_ASSERTION", (ROOT / relative).read_text(encoding="utf-8"), relative)
        schema = json.loads((ROOT / "schemas/mobile-run-log.schema.json").read_text(encoding="utf-8"))
        self.assertEqual("1.7.0", schema["properties"]["schema_version"]["const"] )
        self.assertIn("gate_assertions_artifact", schema["required"])

    def test_active_surfaces_have_no_retired_mobile_gate_or_alternate_result_conversation(self):
        paths = [
            ROOT / "INSTALL.md", ROOT / "README.md", ROOT / "mobile-chatgpt-start-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md", ROOT / "daily-schedule-prompt.md", ROOT / "news-brief-settings.md",
        ]
        paths.extend((ROOT / ".agents/skills").rglob("*.md"))
        forbidden = (
            "MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE",
            "以獨立結果對話輸出當日新聞",
            "GitHub 規則來源：https://github.com/robert820728-star/global-news-brief/blob/main/mobile-chatgpt-daily-prompt.md",
        )
        hits = []
        for path in paths:
            body = path.read_text(encoding="utf-8")
            for phrase in forbidden:
                if phrase in body:
                    hits.append(f"{path.relative_to(ROOT)}: {phrase}")
        self.assertEqual([], hits)

    def test_start_prompt_is_compatibility_redirect_only(self):
        text = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        self.assertIn("唯一安裝入口", text)
        self.assertIn("INSTALL.md", text)
        self.assertIn("不要把本檔", text)
        self.assertNotIn("最低驗收不可省略", text)
        self.assertNotIn("不要使用 Thinking 或 Pro", text)

    def test_post_handoff_byte_identity_gate_is_not_falsely_preasserted(self):
        prompt = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        block = prompt.split("`MOBILE_MANDATORY_GATE_REGISTRY`", 1)[1].split("每筆 assertion", 1)[0]
        self.assertNotIn("CONVERSATION_READER_BYTE_IDENTITY_GATE", block)
        self.assertIn("CONVERSATION_READER_BYTE_IDENTITY_GATE", prompt)

if __name__ == "__main__":
    unittest.main()
