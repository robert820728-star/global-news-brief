import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_validate_news_brief import valid_brief, valid_manifest


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_news_brief.py"


class PublisherTests(unittest.TestCase):
    def test_publish_requires_existing_attachments_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "map.png"
            image_path = root / "image.png"
            map_path.write_bytes(b"map")
            image_path.write_bytes(b"image")
            manifest = valid_manifest()
            manifest["events"][0]["map"]["assets"][0]["path"] = str(map_path)
            manifest["events"][0]["images"]["assets"][0]["path"] = str(image_path)
            brief = valid_brief().replace(
                "sandbox:/tmp/map.png", str(map_path)
            ).replace(
                "sandbox:/tmp/image.png", str(image_path)
            )
            manifest_path = root / "manifest.json"
            brief_path = root / "brief.md"
            release_dir = root / "release"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            brief_path.write_text(brief, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--manifest",
                    str(manifest_path),
                    "--brief",
                    str(brief_path),
                    "--output-dir",
                    str(release_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((release_dir / "news-brief.md").is_file())
            receipt = json.loads(
                (release_dir / "release-receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["status"], "ready")

    def test_publish_blocks_missing_attachment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = valid_manifest()
            manifest_path = root / "manifest.json"
            brief_path = root / "brief.md"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            brief_path.write_text(valid_brief(), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--manifest",
                    str(manifest_path),
                    "--brief",
                    str(brief_path),
                    "--output-dir",
                    str(root / "release"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("附件不存在或為空", result.stderr)
            self.assertFalse((root / "release" / "news-brief.md").exists())


if __name__ == "__main__":
    unittest.main()
