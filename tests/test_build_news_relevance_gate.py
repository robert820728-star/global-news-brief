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
    def test_live_scale_heat_only_rows_do_not_create_an_unbounded_model_workload(self):
        rows = [
            {
                "candidate_id": f"heat-{index:05d}",
                "source_id": "gdelt",
                "section": "GLB",
                "title": f"Routine bilateral statement {index}",
                "summary": f"Routine bilateral statement {index}",
                "summary_quality": "structured_event_context",
                "discovery_signals": {
                    "event_root_code": "04",
                    "num_articles": 8,
                    "num_sources": 5,
                    "num_mentions": 20,
                },
                "canonical_url": f"https://example.test/heat/{index}",
            }
            for index in range(9967)
        ] + [{
            "candidate_id": "high-impact-1",
            "source_id": "gdelt",
            "section": "GLB",
            "title": "Regional conflict emergency",
            "summary": "Regional conflict emergency",
            "summary_quality": "structured_event_context",
            "discovery_signals": {
                "event_root_code": "19",
                "num_articles": 5,
                "num_sources": 3,
                "num_mentions": 10,
            },
            "canonical_url": "https://example.test/high-impact",
        }]

        gate = MODULE.build_gate({"items": rows})
        admitted = MODULE.build_admitted_candidates({"items": rows}, gate)

        self.assertEqual(9968, gate["input_article_row_count"])
        self.assertEqual(9968, len(gate["decisions"]))
        self.assertEqual(1, admitted["admitted_article_row_count"])
        self.assertEqual("high-impact-1", admitted["items"][0]["candidate_id"])

    def test_gate_is_lossless_while_model_input_uses_hydration_route(self):
        keyword_rows = [
            {
                "candidate_id": f"gdelt-{index:04d}",
                "source_id": "gdelt",
                "section": "GLB",
                "title": f"Government election policy update {index}",
                "summary": f"Government election policy update {index}",
                "summary_quality": "title_only",
                "discovery_signals": {
                    "event_root_code": "04",
                    "num_articles": 8,
                    "num_sources": 5,
                    "num_mentions": 20,
                },
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
            result["content_hydration_count"] + result["lightweight_semantic_review_count"],
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

    def test_live_scale_weak_gdelt_rows_remain_auditable_without_overloading_model_input(self):
        weak_count = 19800
        strong_count = 40
        rows = [
            {
                "candidate_id": f"weak-{index:05d}",
                "source_id": "gdelt",
                "section": "GLB",
                "title": f"Routine local report {index}",
                "summary": f"Routine local report {index}",
                "summary_quality": "title_only",
                "discovery_signals": {"num_articles": 1, "num_sources": 1},
                "canonical_url": f"https://example.test/weak/{index}",
            }
            for index in range(weak_count)
        ] + [
            {
                "candidate_id": f"strong-{index:03d}",
                "source_id": "gdelt",
                "section": "GLB",
                "title": f"Emergency conflict update {index}",
                "summary": f"Emergency conflict update {index}",
                "summary_quality": "structured_event_context",
                "discovery_signals": {
                    "event_root_code": "19",
                    "num_articles": 8,
                    "num_sources": 5,
                    "num_mentions": 20,
                },
                "canonical_url": f"https://example.test/strong/{index}",
            }
            for index in range(strong_count)
        ] + [
            {
                "candidate_id": f"regional-{index}",
                "source_id": "cna" if index < 2 else "chinanews",
                "section": "TWN" if index < 2 else "CHN",
                "title": f"區域新聞 {index}",
                "summary": f"區域新聞 {index}",
                "summary_quality": "title_only",
                "discovery_signals": {},
                "canonical_url": f"https://example.test/regional/{index}",
            }
            for index in range(3)
        ]
        source_candidates = {"items": rows}

        gate = MODULE.build_gate(source_candidates)
        admitted = MODULE.build_admitted_candidates(source_candidates, gate)

        self.assertEqual(19843, gate["input_article_row_count"])
        self.assertEqual(19843, len(gate["decisions"]))
        self.assertEqual(43, admitted["admitted_article_row_count"])
        self.assertEqual(
            {f"strong-{index:03d}" for index in range(strong_count)}
            | {f"regional-{index}" for index in range(3)},
            {item["candidate_id"] for item in admitted["items"]},
        )

    def test_gate_requires_compound_evidence_instead_of_keyword_or_heat_alone(self):
        rows = [
            {
                "candidate_id": "keyword-only", "source_id": "gdelt",
                "title": "Government election policy update", "summary": "Government election policy update",
                "summary_quality": "title_only", "discovery_signals": {"num_articles": 1},
                "canonical_url": "https://example.test/keyword-only",
            },
            {
                "candidate_id": "heat-only", "source_id": "gdelt",
                "title": "Lifestyle feature", "summary": "Lifestyle feature",
                "summary_quality": "structured_event_context",
                "discovery_signals": {"event_root_code": "04", "num_sources": 6},
                "canonical_url": "https://example.test/heat-only",
            },
            {
                "candidate_id": "compound", "source_id": "gdelt",
                "title": "Government election policy update", "summary": "Government election policy update",
                "summary_quality": "structured_event_context",
                "discovery_signals": {
                    "event_root_code": "04", "num_articles": 8, "num_sources": 5,
                },
                "canonical_url": "https://example.test/compound",
            },
            {
                "candidate_id": "high-impact", "source_id": "gdelt",
                "title": "Regional developments", "summary": "Regional developments",
                "summary_quality": "structured_event_context",
                "discovery_signals": {
                    "event_root_code": "19", "num_sources": 3, "num_mentions": 10,
                },
                "canonical_url": "https://example.test/high-impact",
            },
        ]

        decisions = {
            item["candidate_id"]: item for item in MODULE.build_gate({"items": rows})["decisions"]
        }

        self.assertEqual("lightweight_semantic_review", decisions["keyword-only"]["route"])
        self.assertEqual("lightweight_semantic_review", decisions["heat-only"]["route"])
        self.assertEqual("content_hydration", decisions["compound"]["route"])
        self.assertEqual("content_hydration", decisions["high-impact"]["route"])

    def test_weak_global_science_row_reaches_lightweight_semantic_review(self):
        source_candidates = {
            "schema_version": "1.0.0",
            "window_start": "2026-08-24T00:00:00+00:00",
            "window_end": "2026-08-25T00:00:00+00:00",
            "source_count": 1,
            "sources": ["gdelt"],
            "items": [{
                "candidate_id": "science-weak",
                "source_id": "gdelt",
                "canonical_url": "https://example.test/novel-protein-folding-result",
                "title": "Researchers report a novel protein-folding result",
                "summary": "A peer-reviewed study describes the measured result.",
                "discovery_signals": {"num_articles": 1, "num_sources": 1},
            }],
        }

        gate = MODULE.build_gate(source_candidates)
        admitted = MODULE.build_admitted_candidates(source_candidates, gate)

        self.assertEqual("lightweight_semantic_review", gate["decisions"][0]["route"])
        self.assertEqual(0, admitted["admitted_article_row_count"])
        self.assertEqual([], admitted["items"])

    def test_corroborated_science_row_reaches_model_input(self):
        row = {
            "candidate_id": "science-corroborated",
            "source_id": "gdelt",
            "canonical_url": "https://example.test/semiconductor-breakthrough",
            "title": "Scientists report a semiconductor technology breakthrough",
            "summary": "Independent research groups report the measured result.",
            "summary_quality": "structured_event_context",
            "discovery_signals": {
                "num_articles": 9,
                "num_sources": 5,
                "num_mentions": 22,
            },
        }

        gate = MODULE.build_gate({"items": [row]})
        admitted = MODULE.build_admitted_candidates({"items": [row]}, gate)

        self.assertEqual("content_hydration", gate["decisions"][0]["route"])
        self.assertEqual([row], admitted["items"])


if __name__ == "__main__":
    unittest.main()

