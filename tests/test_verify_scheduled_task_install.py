import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_scheduled_task_install_payload import build_payload
from scripts.verify_scheduled_task_install import verify_install


MAIN_SHA = "a9a8ec2d3340fc123b1aae116b6226d1ece6f86e"


class VerifyScheduledTaskInstallTests(unittest.TestCase):
    def _payload(self, root: Path):
        template = root / "template.md"
        template.write_text(
            "header\n區域：<使用者指定區域；未指定則台灣、中國、世界>\n"
            "監控類型：<使用者指定監控類型；未指定則預設>\nfooter\n",
            encoding="utf-8",
        )
        result = build_payload(
            template_path=template,
            output_dir=root / "out",
            region="台灣、中國、世界",
            monitor_type="預設",
            main_sha=MAIN_SHA,
        )
        return template, result

    def test_exact_outbound_and_normalized_exact_readback_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, result = self._payload(root)
            saved = Path(result["saved_prompt_path"])
            readback = root / "readback.txt"
            normalized = saved.read_bytes().decode("utf-8").replace("\r\n", "\n").rstrip("\n")
            readback.write_text(normalized.replace("\n", "\r\n") + "\r\n", encoding="utf-8", newline="")
            report = verify_install(
                template_path=template,
                saved_prompt_path=saved,
                receipt_path=Path(result["receipt_path"]),
                expected_main_sha=MAIN_SHA,
                readback_path=readback,
            )
            self.assertTrue(report["verified"])
            self.assertEqual([], report["errors"])
            self.assertTrue(report["readback_verified"])

    def test_launcher_or_extension_contamination_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, result = self._payload(root)
            saved = Path(result["saved_prompt_path"])
            saved.write_text("請依 INSTALL 執行\n診斷：fault penetration", encoding="utf-8")
            report = verify_install(
                template_path=template,
                saved_prompt_path=saved,
                receipt_path=Path(result["receipt_path"]),
                expected_main_sha=MAIN_SHA,
            )
            self.assertFalse(report["verified"])
            self.assertTrue(any("saved prompt" in error for error in report["errors"]))

    def test_documented_direct_cli_entrypoint_can_import_its_sibling_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, result = self._payload(root)
            saved = Path(result["saved_prompt_path"])
            readback = root / "readback.txt"
            readback.write_bytes(saved.read_bytes())
            command = [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "verify_scheduled_task_install.py"),
                "--template",
                str(template),
                "--saved-prompt",
                str(saved),
                "--receipt",
                result["receipt_path"],
                "--expected-main-sha",
                MAIN_SHA,
                "--readback",
                str(readback),
            ]
            completed = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
