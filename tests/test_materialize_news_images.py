import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.materialize_news_images import materialize_image_bytes


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


if __name__ == "__main__":
    unittest.main()
