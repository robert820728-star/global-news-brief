import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.materialize_news_images import materialize, materialize_image_bytes


def jpeg_bytes(size=(320, 240), color=(30, 90, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


class MaterializeNewsImagesTests(unittest.TestCase):
    def test_valid_jpeg_creates_decodable_asset_and_manifest_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = materialize_image_bytes(
                jpeg_bytes(),
                output_dir=Path(tmp),
                event_id="GLB-01",
                source_url="https://images.example.test/event.jpg",
                alt="Event image",
                credit="Example",
            )

            self.assertEqual("ready", record["status"])
            self.assertEqual("https://images.example.test/event.jpg", record["source_image_url"])
            self.assertEqual("scripts/materialize_news_images.py", record["materialized_by"])
            self.assertEqual("image/jpeg", record["mime_type"])
            self.assertEqual(64, len(record["sha256"]))
            asset = Path(record["local_path"])
            self.assertTrue(asset.is_file())
            with Image.open(asset) as image:
                self.assertEqual("JPEG", image.format)
                self.assertEqual((320, 240), image.size)

    def test_corrupt_bytes_are_rejected_without_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            record = materialize_image_bytes(
                b"not an image",
                output_dir=output_dir,
                event_id="TWN-02",
                source_url="https://images.example.test/broken.jpg",
            )

            self.assertEqual("failed", record["status"])
            self.assertIn("decode", record["error"])
            self.assertEqual([], list(output_dir.glob("*.*")))

    def test_large_image_is_resized_to_640_pixel_long_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = materialize_image_bytes(
                jpeg_bytes(size=(1280, 800)),
                output_dir=Path(tmp),
                event_id="CHN-03",
                source_url="https://images.example.test/large.jpg",
            )

            self.assertEqual("ready", record["status"])
            self.assertEqual(640, record["width"])
            self.assertEqual(400, record["height"])

    def test_local_screenshot_may_be_materialized_without_downloading_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screenshot = root / "captured-page-image.png"
            Image.new("RGB", (420, 260), (20, 120, 70)).save(screenshot, format="PNG")

            records = materialize(
                [
                    {
                        "event_id": "TWN-01",
                        "source_page_url": "https://news.example.test/story",
                        "source_image_url": "https://cdn.example.test/story.jpg",
                        "screenshot_path": str(screenshot),
                        "alt": "Visible same-event screenshot",
                        "credit": "Example News",
                    }
                ],
                root / "assets",
            )

            self.assertEqual("ready", records[0]["status"])
            self.assertTrue(Path(records[0]["local_path"]).is_file())
            self.assertEqual("https://cdn.example.test/story.jpg", records[0]["source_image_url"])


if __name__ == "__main__":
    unittest.main()

