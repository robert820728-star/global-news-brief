import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_unique_delivery_gate.py"
SPEC = importlib.util.spec_from_file_location("check_unique_delivery_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

PROMPT = """DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py
python3 scripts/publish_news_brief.py --checkpoint <checkpoint> --manifest <manifest>
python3 scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>
"""


class UniqueDeliveryGateTests(unittest.TestCase):
    def make_repo(self, root: Path):
        scripts = root / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "publish_news_brief.py").write_text("# canonical\n", encoding="utf-8")
        (scripts / "check_unique_delivery_gate.py").write_text("# checker\n", encoding="utf-8")
        (root / "daily-schedule-prompt.md").write_text(PROMPT, encoding="utf-8")

    def test_single_gate_contract_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.assertEqual(MODULE.validate_repository(root), [])

    def test_second_script_with_reserved_release_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "scripts" / "alternate.py").write_text(
                'Path("news-brief.md").write_text("bypass")\n', encoding="utf-8"
            )
            errors = MODULE.validate_repository(root)
            self.assertTrue(any("替代交付路徑" in item for item in errors))

    def test_duplicate_canonical_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            prompt = root / "daily-schedule-prompt.md"
            prompt.write_text(PROMPT + "DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py\n", encoding="utf-8")
            errors = MODULE.validate_repository(root)
            self.assertTrue(any("只能宣告一次" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
