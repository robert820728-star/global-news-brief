import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_selection_freshness.py"
    spec = importlib.util.spec_from_file_location("validate_selection_freshness", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SelectionFreshnessTests(unittest.TestCase):
    def test_rejects_selected_event_url_outside_current_pool(self):
        validator = load_validator()
        source = {"items": [{"url": "https://example.test/fresh", "canonical_url": "https://example.test/fresh"}]}
        selection = {
            "selected_events": [
                {"event_id": "GLB-01", "selection": {"candidate_urls": ["https://example.test/stale"]}}
            ],
            "candidates": [],
        }
        errors = validator.validate_selection_freshness(selection, source)
        self.assertTrue(any("fresh pool" in error for error in errors), errors)

    def test_accepts_current_pool_and_complete_c_or_above_mapping(self):
        validator = load_validator()
        url = "https://example.test/fresh"
        source = {"items": [{"url": url, "canonical_url": url}]}
        selection = {
            "selected_events": [
                {"event_id": "GLB-01", "selection": {"candidate_urls": [url]}}
            ],
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "provisional_grade": "C",
                    "selected_event_id": "GLB-01",
                    "candidate_urls": [url],
                }
            ],
        }
        self.assertEqual([], validator.validate_selection_freshness(selection, source))

    def test_rejects_unmapped_c_or_above_candidate(self):
        validator = load_validator()
        url = "https://example.test/fresh"
        source = {"items": [{"url": url, "canonical_url": url}]}
        selection = {
            "selected_events": [],
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "provisional_grade": "C+",
                    "selected_event_id": None,
                    "candidate_urls": [url],
                }
            ],
        }
        errors = validator.validate_selection_freshness(selection, source)
        self.assertTrue(any("C-or-above" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
