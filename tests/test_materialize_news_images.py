import hashlib
import io
import base64
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.materialize_news_images import (
    materialize,
    materialize_image_bytes,
    resolve_source_image_url,
)


def jpeg_bytes(size=(320, 240), color=(30, 90, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


class MaterializeNewsImagesTests(unittest.TestCase):
    def test_relative_image_url_is_resolved_against_article_url(self):
        self.assertEqual(
            "https://www.news.cn/politics/leaders/20260830/story/photo.jpg",
            resolve_source_image_url(
                "photo.jpg",
                source_page_url="https://www.news.cn/politics/leaders/20260830/story/c.html",
            ),
        )

    def test_protocol_relative_image_url_uses_article_scheme(self):
        self.assertEqual(
            "https://cdn.example.test/photo.jpg",
            resolve_source_image_url(
                "//cdn.example.test/photo.jpg",
                source_page_url="https://news.example.test/story",
            ),
        )

    def test_explicit_page_base_precedes_article_url(self):
        self.assertEqual(
            "https://media.example.test/gallery/photo.jpg",
            resolve_source_image_url(
                "photo.jpg",
                source_page_url="https://news.example.test/story/c.html",
                source_base_url="https://media.example.test/gallery/",
            ),
        )

    def test_valid_jpeg_creates_decodable_asset_and_manifest_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = jpeg_bytes()
            record = materialize_image_bytes(
                raw,
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
            self.assertEqual(len(raw), record["source_byte_size"])
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                record["source_sha256"],
            )
            self.assertEqual(320, record["source_width"])
            self.assertEqual(240, record["source_height"])
            self.assertEqual("JPEG", record["source_format"])
            self.assertEqual("provided_source_bytes", record["acquisition_method"])
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
            self.assertEqual(
                "webpage_region_screenshot", records[0]["acquisition_method"]
            )

    def test_complete_source_bytes_path_has_distinct_verified_acquisition_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = jpeg_bytes(size=(1024, 478))
            source = root / "source.jpg"
            source.write_bytes(raw)
            records = materialize(
                [
                    {
                        "event_id": "TWN-SMOKE",
                        "source_page_url": "https://www.example.test/story",
                        "source_image_url": "https://img.example.test/source.jpg",
                        "source_bytes_path": str(source.resolve()),
                        "expected_source_byte_size": len(raw),
                        "expected_source_sha256": hashlib.sha256(raw).hexdigest(),
                        "expected_source_width": 1024,
                        "expected_source_height": 478,
                    }
                ],
                root / "assets",
            )

            self.assertEqual("ready", records[0]["status"])
            self.assertEqual("source_bytes_path", records[0]["acquisition_method"])
            self.assertEqual(len(raw), records[0]["source_byte_size"])
            self.assertEqual(1024, records[0]["source_width"])
            self.assertEqual(478, records[0]["source_height"])

    def test_connector_base64_source_bytes_are_decoded_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = jpeg_bytes(size=(1024, 478))
            records = materialize(
                [{
                    "event_id": "TWN-BRIDGE",
                    "source_page_url": "https://www.cna.com.tw/news/ahel/202609050001.aspx",
                    "source_image_url": "https://imgcdn.cna.com.tw/example.jpg",
                    "source_bytes_base64": base64.b64encode(raw).decode("ascii"),
                    "expected_source_byte_size": len(raw),
                    "expected_source_sha256": hashlib.sha256(raw).hexdigest(),
                    "expected_source_width": 1024,
                    "expected_source_height": 478,
                }],
                root / "assets",
            )
            self.assertEqual("ready", records[0]["status"])
            self.assertEqual("connector_base64", records[0]["acquisition_method"])
            self.assertTrue(Path(records[0]["local_path"]).is_file())

    def test_expected_source_integrity_mismatch_creates_no_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jpg"
            source.write_bytes(jpeg_bytes())
            records = materialize(
                [
                    {
                        "event_id": "GLB-BAD",
                        "source_image_url": "https://img.example.test/source.jpg",
                        "source_bytes_path": str(source.resolve()),
                        "expected_source_sha256": "0" * 64,
                    }
                ],
                root / "assets",
            )

            self.assertEqual("failed", records[0]["status"])
            self.assertIn("source_sha256 mismatch", records[0]["error"])
            self.assertEqual([], list((root / "assets").glob("*.*")))


if __name__ == "__main__":
    unittest.main()

