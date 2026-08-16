import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "preprocess_news_candidates", ROOT / "scripts" / "preprocess_news_candidates.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PreprocessNewsCandidatesTests(unittest.TestCase):
    def candidate(self):
        return {
            "candidate_id": "wire-1", "section": "GLB", "title": "Major policy update",
            "published_at": "2026-08-16T08:00:00+08:00",
            "url": "https://example.com/news/1?utm_source=test",
        }

    def test_accepts_canonical_source_list_items_key(self):
        result = MODULE.preprocess({
            "window_start": "2026-08-15T12:00:00+08:00",
            "window_end": "2026-08-16T12:00:00+08:00",
            "items": [self.candidate()],
        }, 0.55)
        self.assertEqual(1, result["candidate_count"])
        self.assertEqual(1, result["within_window_count"])
        self.assertEqual(1, len(result["normalized_candidates"]))
        self.assertEqual(1, len(result["clusters"]))

    def test_legacy_candidates_key_remains_supported(self):
        result = MODULE.preprocess({
            "window_start": "2026-08-15T12:00:00+08:00",
            "window_end": "2026-08-16T12:00:00+08:00",
            "candidates": [self.candidate()],
        }, 0.55)
        self.assertEqual(1, result["candidate_count"])


if __name__ == "__main__":
    unittest.main()
