import json
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


if __name__ == "__main__":
    unittest.main()
