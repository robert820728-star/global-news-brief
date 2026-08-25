import importlib.util
import unittest
from pathlib import Path

from tests.test_manage_candidate_audit import candidate
from tests.test_validate_news_brief import valid_manifest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_event_manifest.py"


class MaterializeEventManifestTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(SCRIPT.is_file(), "missing canonical manifest materializer")
        spec = importlib.util.spec_from_file_location("materialize_event_manifest", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def audit(self):
        item = candidate("B")
        item["selected_event_id"] = "TWN-01"
        return {"runs": [{"candidates": [item]}]}

    def test_binds_validated_candidate_score_fields_into_manifest(self):
        module = self.load_module()

        output = module.bind_validated_scores(self.audit(), valid_manifest())
        event = output["events"][0]

        self.assertEqual("public_value_v2", event["scoring_method"])
        self.assertEqual(60, event["validated_importance_score"])
        self.assertEqual("B", event["validated_grade"])
        self.assertEqual("validated", event["grade_status"])
        self.assertEqual(85, event["evidence_confidence"])
        self.assertEqual("high", event["confidence_band"])

    def test_rejects_provisional_candidate(self):
        module = self.load_module()
        audit = self.audit()
        audit["runs"][0]["candidates"][0]["grade_status"] = "provisional"

        with self.assertRaisesRegex(ValueError, "validated"):
            module.bind_validated_scores(audit, valid_manifest())

    def test_rejects_event_set_mismatch(self):
        module = self.load_module()
        manifest = valid_manifest()
        manifest["events"][0]["event_id"] = "TWN-02"

        with self.assertRaisesRegex(ValueError, "event set"):
            module.bind_validated_scores(self.audit(), manifest)


if __name__ == "__main__":
    unittest.main()
