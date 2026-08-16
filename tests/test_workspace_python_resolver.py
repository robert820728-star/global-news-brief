import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_RESOLVER = ROOT / "scripts" / "resolve_bundled_python.py"


class CrossPlatformPythonResolverTests(unittest.TestCase):
    def test_preferred_host_python_is_probed_for_pillow(self):
        self.assertTrue(PYTHON_RESOLVER.is_file())
        completed = subprocess.run(
            [sys.executable, str(PYTHON_RESOLVER), "--preferred-python", sys.executable],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(Path(result["python"]).resolve(), Path(sys.executable).resolve())
        self.assertTrue(result["pillow"])
        self.assertEqual(result["source"], "preferred")

    def test_invalid_preferred_candidate_is_rejected_without_path_fallback(self):
        self.assertTrue(PYTHON_RESOLVER.is_file())
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "not-python"
            invalid.write_text("not an executable", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PYTHON_RESOLVER),
                    "--preferred-python",
                    str(invalid),
                    "--only-preferred",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("dependency probe failed", completed.stderr)


if __name__ == "__main__":
    unittest.main()
