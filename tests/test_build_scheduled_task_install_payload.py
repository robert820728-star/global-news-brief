import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_scheduled_task_install_payload import build_payload
from scripts.build_bootstrap_capsule import collect_runtime_paths


MAIN_SHA = "8417e198468e2ebb64147f180ce3f4a717d6a2ab"
REGION_PLACEHOLDER = "區域：<使用者指定區域；未指定則台灣、中國、世界>"
MONITOR_PLACEHOLDER = "監控類型：<使用者指定監控類型；未指定則預設>"


class BuildScheduledTaskInstallPayloadTests(unittest.TestCase):
    def test_builder_and_extension_contract_ship_in_runtime_capsule(self):
        root = Path(__file__).resolve().parents[1]
        paths = {path.relative_to(root).as_posix() for path in collect_runtime_paths(root)}
        self.assertIn("scripts/build_scheduled_task_install_payload.py", paths)
        self.assertIn("scheduled-task-test-extension.example.json", paths)

    def _template(self, root: Path, text: str | None = None) -> Path:
        path = root / "scheduled-task-prompt-template.md"
        path.write_text(
            text
            or (
                "canonical header\n"
                f"{REGION_PLACEHOLDER}\n"
                f"{MONITOR_PLACEHOLDER}\n"
                "canonical footer\n"
            ),
            encoding="utf-8",
            newline="",
        )
        return path

    def _extension(self, root: Path, **updates) -> Path:
        data = {
            "schema_version": "1.0",
            "scope": "installation_only",
            "saved_prompt_mutation_allowed": False,
            "one_time_delay_minutes": 5,
            "smoke_fixture": {
                "source_media_url": "https://img.example.test/smoke.jpg",
                "source_page_url": "https://www.example.test/story",
                "expected_byte_size": 171909,
                "expected_width": 1024,
                "expected_height": 478,
                "expected_sha256": (
                    "6262c2e8d26f1881e8a2aeb800a13820"
                    "f23c6192f42d5d7e8152709f7ccbb8c1"
                ),
            },
        }
        data.update(updates)
        path = root / "extension.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_saved_prompt_is_exact_template_after_only_two_line_substitutions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = self._template(root)
            result = build_payload(
                template_path=template,
                output_dir=root / "out",
                region="台灣、中國、世界",
                monitor_type="預設",
                main_sha=MAIN_SHA,
            )

            saved = Path(result["saved_prompt_path"]).read_bytes()
            expected = (
                "canonical header\n"
                "區域：台灣、中國、世界\n"
                "監控類型：預設\n"
                "canonical footer\n"
            ).encode("utf-8")
            self.assertEqual(expected, saved)

            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(MAIN_SHA, receipt["resolved_main_sha"])
            self.assertEqual(len(expected), receipt["saved_prompt_byte_size"])
            self.assertEqual(
                hashlib.sha256(expected).hexdigest(), receipt["saved_prompt_sha256"]
            )
            self.assertEqual(2, receipt["authorized_substitution_count"])
            self.assertTrue(receipt["extension_embedded_in_saved_prompt"] is False)

    def test_extension_is_a_separate_sidecar_and_never_enters_saved_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = build_payload(
                template_path=self._template(root),
                output_dir=root / "out",
                region="台灣、中國、世界",
                monitor_type="預設",
                main_sha=MAIN_SHA,
                extension_path=self._extension(root),
            )

            saved = Path(result["saved_prompt_path"]).read_text(encoding="utf-8")
            sidecar = json.loads(
                Path(result["extension_path"]).read_text(encoding="utf-8")
            )
            self.assertNotIn("one_time_delay_minutes", saved)
            self.assertNotIn("img.example.test", saved)
            self.assertEqual("installation_only", sidecar["scope"])
            self.assertFalse(sidecar["saved_prompt_mutation_allowed"])

    def test_missing_or_duplicate_placeholder_is_rejected_before_writing(self):
        for name, text in {
            "missing": f"header\n{REGION_PLACEHOLDER}\nfooter\n",
            "duplicate": (
                f"{REGION_PLACEHOLDER}\n{REGION_PLACEHOLDER}\n"
                f"{MONITOR_PLACEHOLDER}\n"
            ),
        }.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaisesRegex(ValueError, "exactly once"):
                    build_payload(
                        template_path=self._template(root, text),
                        output_dir=root / "out",
                        region="台灣、中國、世界",
                        monitor_type="預設",
                        main_sha=MAIN_SHA,
                    )
                self.assertFalse((root / "out" / "saved-prompt.txt").exists())

    def test_extension_cannot_request_saved_prompt_mutation_or_unknown_keys(self):
        for name, updates in {
            "mutation": {"saved_prompt_mutation_allowed": True},
            "unknown": {"append_to_saved_prompt": "diagnostic launcher"},
            "scope": {"scope": "occurrence"},
        }.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(ValueError):
                    build_payload(
                        template_path=self._template(root),
                        output_dir=root / "out",
                        region="台灣、中國、世界",
                        monitor_type="預設",
                        main_sha=MAIN_SHA,
                        extension_path=self._extension(root, **updates),
                    )
                self.assertFalse((root / "out" / "saved-prompt.txt").exists())


if __name__ == "__main__":
    unittest.main()
