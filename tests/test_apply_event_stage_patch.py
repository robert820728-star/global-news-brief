import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import apply_event_stage_patch as subject


class ApplyEventStagePatchTests(unittest.TestCase):
    def manifest(self):
        return {
            "schema_version": "1.1.0",
            "run": {"run_id": "gnb-test"},
            "events": [
                {
                    "event_id": "TWN-01",
                    "title": "one",
                    "verification": {"status": "pending"},
                    "images": {"status": "pending"},
                },
                {
                    "event_id": "GLB-01",
                    "title": "two",
                    "verification": {"status": "pending"},
                    "images": {"status": "pending"},
                },
            ],
        }

    def test_applies_only_verification_by_event_id(self):
        before = self.manifest()
        expected_unowned = copy.deepcopy(before["events"][1]["images"])
        patch = {
            "stage": "verify-news-events",
            "events": [
                {
                    "event_id": "GLB-01",
                    "verification": {"status": "completed", "finding": "corroborated"},
                }
            ],
        }
        after = subject.apply_stage_patch(before, patch, "verify-news-events")
        self.assertEqual("pending", after["events"][0]["verification"]["status"])
        self.assertEqual("completed", after["events"][1]["verification"]["status"])
        self.assertEqual(expected_unowned, after["events"][1]["images"])

    def test_rejects_unknown_or_duplicate_event_ids(self):
        for events in (
            [{"event_id": "CHN-99", "verification": {}}],
            [
                {"event_id": "TWN-01", "verification": {}},
                {"event_id": "TWN-01", "verification": {}},
            ],
        ):
            with self.subTest(events=events), self.assertRaises(ValueError):
                subject.apply_stage_patch(
                    self.manifest(),
                    {"stage": "verify-news-events", "events": events},
                    "verify-news-events",
                )

    def test_cli_writes_valid_json_without_shell_interpolation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            manifest_path = directory / "manifest.json"
            patch_path = directory / "patch.json"
            output_path = directory / "after.json"
            manifest_path.write_text(json.dumps(self.manifest()), encoding="utf-8")
            patch_path.write_text(
                json.dumps(
                    {
                        "stage": "verify-news-events",
                        "events": [
                            {
                                "event_id": "TWN-01",
                                "verification": {
                                    "status": "completed",
                                    "reader_wording": "quote: '$n $d $e'",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "apply_event_stage_patch.py"),
                    "--stage",
                    "verify-news-events",
                    "--manifest",
                    str(manifest_path),
                    "--patch",
                    str(patch_path),
                    "--output",
                    str(output_path),
                ],
                check=True,
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "quote: '$n $d $e'",
                result["events"][0]["verification"]["reader_wording"],
            )


if __name__ == "__main__":
    unittest.main()
