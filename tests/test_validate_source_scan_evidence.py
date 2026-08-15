import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_source_scan_evidence", ROOT / "scripts" / "validate_source_scan_evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SourceScanEvidenceTests(unittest.TestCase):
    def make_snapshot(self, directory, text):
        path = Path(directory) / "page.html"
        path.write_text(text, encoding="utf-8")
        return str(path), hashlib.sha256(text.encode()).hexdigest()

    def source(self):
        return {"source_id": "wire", "homepage": "https://example.com/"}

    def coverage(self, ranked=None, count=0):
        return {
            "scan_window_start": "2026-08-14T06:00:00+08:00",
            "scan_window_end": "2026-08-15T06:00:00+08:00",
            "within_window_count": count,
            "ranked_items": ranked or [],
        }

    def test_zero_items_allowed_when_source_exhaustion_is_proven(self):
        with tempfile.TemporaryDirectory() as directory:
            path, digest = self.make_snapshot(directory, "NO_MORE_RESULTS")
            scan = {
                "schema_version": "1.0.0", "collector": "fixture", "generated_at": "2026-08-15T06:00:00+08:00",
                "window_start": "2026-08-14T06:00:00+08:00", "window_end": "2026-08-15T06:00:00+08:00",
                "pages": [{"request_url": "https://example.com/feed", "fetched_at": "2026-08-15T06:00:00+08:00", "http_status": 200, "snapshot_path": path, "sha256": digest, "next_url": None, "extracted_items": []}],
                "terminal_proof": {"type": "source_exhausted", "page_index": 1, "terminal_marker": "NO_MORE_RESULTS"},
            }
            self.assertEqual([], MODULE.validate_scan(scan, self.coverage(), self.source()))

    def test_crossed_boundary_recomputes_window_items(self):
        with tempfile.TemporaryDirectory() as directory:
            text = "https://example.com/new 2026-08-15T05:00:00+08:00 https://example.com/old 2026-08-14T05:00:00+08:00"
            path, digest = self.make_snapshot(directory, text)
            items = [
                {"url": "https://example.com/new", "title": "new", "published_at": "2026-08-15T05:00:00+08:00", "url_evidence": "https://example.com/new", "published_evidence": "2026-08-15T05:00:00+08:00"},
                {"url": "https://example.com/old", "title": "old", "published_at": "2026-08-14T05:00:00+08:00", "url_evidence": "https://example.com/old", "published_evidence": "2026-08-14T05:00:00+08:00"},
            ]
            scan = {
                "schema_version": "1.0.0", "collector": "fixture", "generated_at": "2026-08-15T06:00:00+08:00",
                "window_start": "2026-08-14T06:00:00+08:00", "window_end": "2026-08-15T06:00:00+08:00",
                "pages": [{"request_url": "https://example.com/feed", "fetched_at": "2026-08-15T06:00:00+08:00", "http_status": 200, "snapshot_path": path, "sha256": digest, "next_url": None, "extracted_items": items}],
                "terminal_proof": {"type": "crossed_window_start", "page_index": 1, "witness_url": "https://example.com/old"},
            }
            ranked = [{"url": "https://example.com/new"}]
            self.assertEqual([], MODULE.validate_scan(scan, self.coverage(ranked, 1), self.source()))

    def test_homepage_cannot_masquerade_as_article(self):
        with tempfile.TemporaryDirectory() as directory:
            text = "https://example.com/ 2026-08-15T05:00:00+08:00 DONE"
            path, digest = self.make_snapshot(directory, text)
            item = {"url": "https://example.com/", "title": "首頁", "published_at": "2026-08-15T05:00:00+08:00", "url_evidence": "https://example.com/", "published_evidence": "2026-08-15T05:00:00+08:00"}
            scan = {
                "schema_version": "1.0.0", "collector": "fixture", "generated_at": "2026-08-15T06:00:00+08:00",
                "window_start": "2026-08-14T06:00:00+08:00", "window_end": "2026-08-15T06:00:00+08:00",
                "pages": [{"request_url": "https://example.com/feed", "fetched_at": "2026-08-15T06:00:00+08:00", "http_status": 200, "snapshot_path": path, "sha256": digest, "next_url": None, "extracted_items": [item]}],
                "terminal_proof": {"type": "source_exhausted", "page_index": 1, "terminal_marker": "DONE"},
            }
            errors = MODULE.validate_scan(scan, self.coverage([{"url": "https://example.com/"}], 1), self.source())
            self.assertTrue(any("首頁冒充" in error for error in errors))

    def test_declared_count_cannot_override_snapshot_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path, digest = self.make_snapshot(directory, "DONE")
            scan = {
                "schema_version": "1.0.0", "collector": "fixture", "generated_at": "2026-08-15T06:00:00+08:00",
                "window_start": "2026-08-14T06:00:00+08:00", "window_end": "2026-08-15T06:00:00+08:00",
                "pages": [{"request_url": "https://example.com/feed", "fetched_at": "2026-08-15T06:00:00+08:00", "http_status": 200, "snapshot_path": path, "sha256": digest, "next_url": None, "extracted_items": []}],
                "terminal_proof": {"type": "source_exhausted", "page_index": 1, "terminal_marker": "DONE"},
            }
            errors = MODULE.validate_scan(scan, self.coverage([], 1), self.source())
            self.assertTrue(any("不得自行填寫" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
