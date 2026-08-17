from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FILES = [
    ROOT / "news-brief-settings.md",
    ROOT / "mobile-chatgpt-daily-prompt.md",
    ROOT / ".agents/skills/select-news-events/references/severity-rubric.md",
]
REQUIRED_RULES = [
    "DISASTER_2500_DEATHS_A_CEILING",
    "A_PLUS_REQUIRES_SEPARATE_ESCALATION_EVIDENCE",
    "RISK_GROUP_4_NOT_AUTOMATIC_A_PLUS",
    "PANDEMIC_S_MINUS_WORLD_CHANGE_GATE",
    "MASS_CASUALTY_S_SYSTEMIC_IMPACT_PRESUMPTION",
    "COVID_GLOBAL_LOCKDOWN_S_MINUS_REFERENCE",
]


class SeverityContractTests(unittest.TestCase):
    def test_all_execution_surfaces_share_high_severity_rules(self):
        for path in CONTRACT_FILES:
            text = path.read_text(encoding="utf-8")
            for rule in REQUIRED_RULES:
                with self.subTest(path=path.name, rule=rule):
                    self.assertIn(f"`{rule}`", text)

    def test_old_a_ceiling_conflict_is_removed(self):
        rubric = CONTRACT_FILES[-1].read_text(encoding="utf-8")
        self.assertNotIn("死亡數本身不得把事件推到 A", rubric)


if __name__ == "__main__":
    unittest.main()
