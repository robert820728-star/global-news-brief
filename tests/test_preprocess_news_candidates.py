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
        self.assertEqual(1, result["article_row_count"])
        self.assertEqual(1, result["within_window_article_row_count"])
        self.assertEqual(1, len(result["normalized_articles"]))
        self.assertEqual(1, len(result["provisional_article_groups"]))
        self.assertNotIn("candidate_count", result)
        self.assertNotIn("clusters", result)
        self.assertFalse(result["semantic_event_creation_performed"])

    def test_legacy_candidates_key_remains_supported(self):
        result = MODULE.preprocess({
            "window_start": "2026-08-15T12:00:00+08:00",
            "window_end": "2026-08-16T12:00:00+08:00",
            "candidates": [self.candidate()],
        }, 0.55)
        self.assertEqual(1, result["article_row_count"])

    def test_article_count_receipt_conserves_each_preprocessing_stage(self):
        exact_duplicate = dict(self.candidate())
        exact_duplicate["candidate_id"] = "wire-2"
        exact_duplicate["url"] = "https://example.com/news/1?utm_campaign=copy"
        similar_title = dict(self.candidate())
        similar_title["candidate_id"] = "wire-3"
        similar_title["url"] = "https://example.net/news/3"
        outside = dict(self.candidate())
        outside["candidate_id"] = "wire-4"
        outside["url"] = "https://example.net/news/4"
        outside["published_at"] = "2026-08-14T08:00:00+08:00"

        result = MODULE.preprocess({
            "window_start": "2026-08-15T12:00:00+08:00",
            "window_end": "2026-08-16T12:00:00+08:00",
            "items": [self.candidate(), exact_duplicate, similar_title, outside],
        }, 0.55)

        self.assertEqual({
            "input_article_row_count": 4,
            "within_window_article_row_count": 3,
            "outside_window_article_row_count": 1,
            "canonical_url_count": 2,
            "exact_url_duplicate_row_count": 1,
            "provisional_title_cluster_count": 1,
            "title_cluster_merged_url_count": 1,
        }, result["article_count_receipt"])


if __name__ == "__main__":
    unittest.main()
