import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".json", ".md", ".py", ".yaml", ".yml"}


class NoObsoleteContractsTests(unittest.TestCase):
    def test_repository_contains_no_retired_source_or_scoring_contract(self):
        forbidden = (
            "fixed" + "_source",
            "fixed" + "-source",
            "fixed" + " source",
            "固定" + "來源",
            "固定" + "媒體站",
            "十五" + "個來源",
            "15" + "個來源",
            "15" + " sources",
            "mandatory" + "_overflow",
            "fixed" + "_top_n",
            "public" + "_value" + "_v1",
            "legacy" + "ImportanceBreakdown",
            "legacy" + "Candidate",
            "V1" + "_HISTORY",
            "Dual " + "V1/V2 runtime",
            "Compatibility adapter around " + "V1 scores",
            "Historical " + "V1 runs",
            "schema accepts " + "legacy identity fields",
            "legacy" + "_identity_fields",
        )
        hits = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if "__pycache__" in path.parts or path.name.startswith("capsule.part"):
                continue
            text = path.read_text(encoding="utf-8", errors="strict")
            for phrase in forbidden:
                if phrase.casefold() in text.casefold():
                    hits.append(f"{path.relative_to(ROOT)}: {phrase}")
        self.assertEqual([], hits)

    def test_source_configuration_has_only_current_dynamic_selection_contract(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))

        self.assertNotIn("verification_source_selection", pool)
        self.assertEqual(
            ["gdelt", "cna", "chinanews"],
            [item["source_id"] for item in pool["discovery_sources"]],
        )
        self.assertEqual("public_value_v2", pool["ranking"]["method"])

    def test_install_names_the_uncapped_discovery_contract(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("FULL_DISCOVERY_POOL_UNCAPPED", install)

    def test_install_names_the_native_media_capability_fallback(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("NATIVE_MEDIA_CAPABILITY_FALLBACK", install)

    def test_candidate_audit_schema_has_only_current_v2_shapes(self):
        schema = json.loads(
            (ROOT / "schemas/news-candidate-audit.schema.json").read_text(
                encoding="utf-8"
            )
        )
        defs = schema["$defs"]
        coverage = defs["sourceCoverage"]

        self.assertEqual({"const": "public_value_v2"}, coverage["properties"]["ranking_method"])
        self.assertEqual(
            {"$ref": "#/$defs/importanceBreakdown"},
            coverage["properties"]["ranked_items"]["items"]["properties"]["importance_breakdown"],
        )
        self.assertEqual(
            [
                {"$ref": "#/$defs/v2Candidate"},
                {"$ref": "#/$defs/compactHistoricalCandidate"},
            ],
            defs["candidate"]["anyOf"],
        )
        self.assertFalse(any(name.casefold().startswith("legacy") for name in defs))
        self.assertTrue(coverage["additionalProperties"] is False)


if __name__ == "__main__":
    unittest.main()
