import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_news_relevance_gate", ROOT / "scripts" / "build_news_relevance_gate.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildNewsRelevanceGateTests(unittest.TestCase):
    def test_gate_is_lossless_uncapped_and_always_admits_regional_supplements(self):
        keyword_rows = [
            {
                "candidate_id": f"gdelt-{index:04d}",
                "source_id": "gdelt",
                "section": "GLB",
                "title": f"Government election policy update {index}",
                "summary": f"Government election policy update {index}",
                "summary_quality": "title_only",
                "discovery_signals": {"num_articles": 1},
                "canonical_url": f"https://example.test/news/{index}",
            }
            for index in range(1500)
        ]
        quiet_rows = [
            {
                "candidate_id": f"quiet-{index}",
                "source_id": "gdelt",
                "section": "GLB",
                "title": f"Lifestyle feature {index}",
                "summary": f"Lifestyle feature {index}",
                "summary_quality": "title_only",
                "discovery_signals": {"num_articles": 1},
                "canonical_url": f"https://example.test/lifestyle/{index}",
            }
            for index in range(3)
        ]
        supplements = [
            {
                "candidate_id": "cna-1", "source_id": "cna", "section": "TWN",
                "title": "地方活動消息", "summary": "地方活動消息",
                "summary_quality": "title_only", "discovery_signals": {},
                "canonical_url": "https://www.cna.com.tw/news/aloc/1.aspx",
            },
            {
                "candidate_id": "cns-1", "source_id": "chinanews", "section": "CHN",
                "title": "地方活動消息", "summary": "地方活動消息",
                "summary_quality": "title_only", "discovery_signals": {},
                "canonical_url": "https://www.chinanews.com.cn/sh/2026/08-22/1.shtml",
            },
        ]
        source_candidates = {"items": keyword_rows + quiet_rows + supplements}

        result = MODULE.build_gate(source_candidates)

        decisions = result["decisions"]
        self.assertEqual(len(source_candidates["items"]), len(decisions))
        self.assertEqual(
            {item["candidate_id"] for item in source_candidates["items"]},
            {item["candidate_id"] for item in decisions},
        )
        self.assertEqual(
            len(decisions),
            result["content_hydration_count"] + result["structured_review_count"],
        )
        self.assertEqual(1502, result["content_hydration_count"])
        admitted = {
            item["candidate_id"] for item in decisions
            if item["route"] == "content_hydration"
        }
        self.assertIn("cna-1", admitted)
        self.assertIn("cns-1", admitted)
        self.assertTrue(all(item["reasons"] for item in decisions))
        filtered = MODULE.build_admitted_candidates(source_candidates, result)
        self.assertEqual(1502, len(filtered["items"]))
        self.assertEqual(
            admitted,
            {item["candidate_id"] for item in filtered["items"]},
        )
        self.assertEqual(len(decisions), filtered["discovery_article_row_count"])
        self.assertEqual(1502, filtered["admitted_article_row_count"])


if __name__ == "__main__":
    unittest.main()
