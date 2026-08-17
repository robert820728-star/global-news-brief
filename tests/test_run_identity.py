import importlib.util
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_identity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_identity", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunIdentityTests(unittest.TestCase):
    def test_fixed_utc_second_and_suffix_have_canonical_format(self):
        module = load_module()
        value = module.generate_run_id(
            datetime(2026, 8, 17, 10, 28, 0, tzinfo=timezone.utc),
            suffix="6a82b2e0",
        )
        self.assertEqual("gnb-20260817T102800Z-6a82b2e0", value)
        self.assertTrue(module.is_valid_run_id(value))

    def test_same_second_generates_collision_resistant_ids(self):
        module = load_module()
        instant = datetime(2026, 8, 17, 10, 28, 0, tzinfo=timezone.utc)
        values = {module.generate_run_id(instant) for _ in range(32)}
        self.assertEqual(32, len(values))

    def test_legacy_or_malformed_ids_are_rejected(self):
        module = load_module()
        invalid = [
            "run-001",
            "mobile-20260817T102800Z",
            "gnb-20260817T102800Z",
            "gnb-20260817T102800Z-ABCDEF12",
            "gnb-20260817T102800Z-123",
        ]
        self.assertTrue(all(not module.is_valid_run_id(value) for value in invalid))

    def test_generate_cli_prints_one_valid_identifier(self):
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "generate"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        module = load_module()
        self.assertTrue(module.is_valid_run_id(result.stdout.strip()))


if __name__ == "__main__":
    unittest.main()
