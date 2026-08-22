import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_local_source_admission.py"
    spec = importlib.util.spec_from_file_location("validate_local_source_admission", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def source_pool():
    return {
        "discovery_sources": [
            {"source_id": "gdelt", "role": "primary_aggregator"},
            {"source_id": "cna", "role": "regional_supplement"},
            {"source_id": "chinanews", "role": "regional_supplement"},
        ]
    }


def preprocessed():
    return {
        "normalized_articles": [
            {"candidate_id": "cna-1", "source_id": "cna"},
            {"candidate_id": "cna-2", "source_id": "cna"},
            {"candidate_id": "cn-1", "source_id": "chinanews"},
            {"candidate_id": "gdelt-1", "source_id": "gdelt"},
        ],
        "provisional_article_groups": [
            {"cluster_id": "local-tw", "candidate_ids": ["cna-1", "cna-2"]},
            {"cluster_id": "local-cn", "candidate_ids": ["cn-1"]},
            {"cluster_id": "global-only", "candidate_ids": ["gdelt-1"]},
        ],
    }


def complete_selection():
    return {
        "candidate_groups": [
            {"group_id": "local-tw", "candidate_ids": ["cna-1", "cna-2"]},
            {"group_id": "local-cn", "candidate_ids": ["cn-1"]},
        ]
    }


class LocalSourceAdmissionTests(unittest.TestCase):
    def test_accepts_every_regional_group_without_requiring_gdelt_only_group(self):
        validator = load_validator()
        errors, counts = validator.validate_local_source_admission(
            preprocessed(), complete_selection(), source_pool()
        )
        self.assertEqual([], errors)
        self.assertEqual(2, counts["required_regional_group_count"])
        self.assertEqual(3, counts["required_regional_article_row_count"])
        self.assertEqual(2, counts["admitted_regional_group_count"])
        self.assertEqual(3, counts["admitted_regional_article_row_count"])

    def test_rejects_regional_groups_omitted_by_heat_or_keyword_queue(self):
        validator = load_validator()
        errors, _ = validator.validate_local_source_admission(
            preprocessed(), {"candidate_groups": []}, source_pool()
        )
        self.assertTrue(any("missing regional group: local-tw" in error for error in errors), errors)
        self.assertTrue(any("missing regional group: local-cn" in error for error in errors), errors)

    def test_rejects_regional_article_row_omitted_from_present_group(self):
        validator = load_validator()
        selection = complete_selection()
        selection["candidate_groups"][0]["candidate_ids"] = ["cna-1"]
        errors, _ = validator.validate_local_source_admission(
            preprocessed(), selection, source_pool()
        )
        self.assertTrue(any("local-tw missing regional candidate rows: cna-2" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()

