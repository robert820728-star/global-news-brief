from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FILES = [
    ROOT / "news-brief-settings.md",
    ROOT / "docs/history/mobile-chatgpt-daily-prompt.md",
    ROOT / ".agents/skills/select-news-events/references/severity-rubric.md",
]
REQUIRED_RULES = [
    "INTEGRATED_SIX_DIMENSION_NO_HARD_CAP",
    "PUBLIC_VALUE_V2_NORMALIZED_WEIGHTED_SCORING",
    "SCORE_TO_GRADE_BANDS_V2",
    "CASUALTY_PUBLIC_IMPACT_FLOORS_V2",
    "URGENCY_SAFETY_ANCHORS_V2",
    "RISK_GROUP_4_NOT_AUTOMATIC_A_PLUS",
    "MASS_CASUALTY_REQUIRES_INTEGRATED_SCORING",
]


class SeverityContractTests(unittest.TestCase):
    def test_all_execution_surfaces_share_high_severity_rules(self):
        for path in CONTRACT_FILES:
            text = path.read_text(encoding="utf-8")
            for rule in REQUIRED_RULES:
                with self.subTest(path=path.name, rule=rule):
                    self.assertIn(f"`{rule}`", text)

    def test_old_grade_ceiling_conflicts_are_removed(self):
        for path in CONTRACT_FILES:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("DISASTER_2500_DEATHS_A_CEILING", text)
            self.assertNotIn("A_PLUS_REQUIRES_SEPARATE_ESCALATION_EVIDENCE", text)


if __name__ == "__main__":
    unittest.main()
