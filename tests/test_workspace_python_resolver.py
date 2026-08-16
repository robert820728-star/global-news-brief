import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "resolve_bundled_python.ps1"


@unittest.skipUnless(os.name == "nt", "workspace Python resolver is Windows-specific")
class WorkspacePythonResolverTests(unittest.TestCase):
    def test_resolver_returns_existing_python_with_pillow(self):
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        self.assertIsNotNone(powershell)
        completed = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(RESOLVER),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "ready")
        python_path = Path(result["python"])
        self.assertTrue(python_path.is_file())
        pillow = subprocess.run(
            [str(python_path), "-c", "from PIL import Image; print(Image.__version__)"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(pillow.returncode, 0, pillow.stderr)


if __name__ == "__main__":
    unittest.main()
