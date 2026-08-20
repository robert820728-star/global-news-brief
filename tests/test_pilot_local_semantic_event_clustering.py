import copy
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from pilot_local_semantic_event_clustering import (  # noqa: E402
    build_semantic_texts,
    cluster_from_neighbor_pairs,
    embed_texts,
    extract_fact_anchors,
    is_semantic_title_eligible,
    nearest_neighbor_pairs,
    pair_decision,
    select_embedding_groups,
    verify_semantic_report,
)


CONFIG = {
    "auto_merge_similarity": 0.94,
    "review_similarity": 0.82,
    "max_auto_merge_hours": 48,
    "max_death_magnitude_gap": 1,
}


def group(group_id, title, hour, row_id, kind="exact_title"):
    return {
        "group_id": group_id,
        "group_kind": kind,
        "section": "GLB",
        "effective_title": title,
        "row_ids": [row_id],
        "candidate_ids": [group_id],
        "evidence": [
            {
                "row_id": row_id,
                "published_at": f"2026-08-20T{hour:02d}:00:00+00:00",
                "original_title": title,
                "effective_title": title,
                "url": f"https://example.test/{group_id}",
            }
        ],
    }


def report(groups):
    return {
        "schema_version": "url-recovery-batched-triage-pilot/v1",
        "input_row_ids": [row_id for item in groups for row_id in item["row_ids"]],
        "groups": groups,
    }


class LocalSemanticEventClusteringTests(unittest.TestCase):
    def test_high_similarity_same_event_merges(self):
        groups = [
            group("g1", "Typhoon closes schools across northern Taiwan", 1, "r1"),
            group("g2", "Northern Taiwan schools closed as typhoon arrives", 2, "r2"),
        ]
        result = cluster_from_neighbor_pairs(
            report(groups),
            [{"left_group_id": "g1", "right_group_id": "g2", "similarity": 0.97}],
            CONFIG,
        )
        self.assertEqual(result["counts"]["semantic_event_clusters"], 1)
        self.assertEqual(result["counts"]["automatically_deleted_rows"], 0)
        texts = build_semantic_texts(groups, {"r1": "Classes and offices were suspended.", "r2": "Schools will not open."})
        self.assertIn("Classes and offices were suspended.", texts[0])

        class FakeEmbedder:
            def embed(self, documents):
                return [[3.0, 4.0] for _ in documents]

        vectors = embed_texts(texts, "fake-model", "unused-cache", embedder_factory=lambda **_: FakeEmbedder())
        self.assertAlmostEqual(sum(value * value for value in vectors[0]), 1.0)

    def test_evolving_casualty_counts_use_typed_magnitude_and_preserve_values(self):
        first = group("g1", "Brazil bus crash kills 21 people", 1, "r1")
        updated = group("g2", "Death toll rises to 23 in Brazil bus crash", 3, "r2")
        huge_gap = group("g3", "Brazil bus crash kills 2300 people", 3, "r3")
        injured = extract_fact_anchors("Brazil bus crash injures 23 people")
        self.assertEqual(injured["injured"], [23])
        self.assertEqual(injured["deaths"], [])
        self.assertEqual(pair_decision(first, updated, 0.97, CONFIG), "auto_merge")
        self.assertEqual(pair_decision(first, huge_gap, 0.97, CONFIG), "review")
        result = cluster_from_neighbor_pairs(
            report([first, updated]),
            [{"left_group_id": "g1", "right_group_id": "g2", "similarity": 0.97}],
            CONFIG,
        )
        event = result["semantic_clusters"][0]
        self.assertEqual(event["fact_variants"]["deaths"], [21, 23])
        self.assertEqual(event["fact_magnitudes"]["deaths"], ["tens"])

    def test_large_time_gap_is_not_automatically_merged(self):
        first = group("g1", "Volcano eruption closes regional airport", 1, "r1")
        later = copy.deepcopy(group("g2", "Regional airport closed after volcano eruption", 2, "r2"))
        later["evidence"][0]["published_at"] = "2026-08-23T02:00:00+00:00"
        self.assertEqual(pair_decision(first, later, 0.98, CONFIG), "review")

    def test_unresolved_title_stays_singleton(self):
        self.assertFalse(is_semantic_title_eligible("a1802471"))
        self.assertFalse(is_semantic_title_eligible("arid 41898676"))
        self.assertFalse(is_semantic_title_eligible("27a45602 b49e 5d98 a1bc"))
        self.assertTrue(is_semantic_title_eligible("Mossad chief discussed Syrian military deployments"))
        unresolved = group("g1", "example.com news report", 1, "r1", kind="unresolved_title")
        other = group("g2", "example.com report", 1, "r2", kind="unresolved_title")
        result = cluster_from_neighbor_pairs(
            report([unresolved, other]),
            [{"left_group_id": "g1", "right_group_id": "g2", "similarity": 0.99}],
            CONFIG,
        )
        self.assertEqual(result["counts"]["semantic_event_clusters"], 2)

    def test_every_input_row_is_conserved_exactly_once(self):
        groups = [
            group("g1", "Earthquake damages homes in eastern county", 1, "r1"),
            group("g2", "Homes damaged after eastern county earthquake", 2, "r2"),
            group("g3", "Parliament passes annual budget bill", 3, "r3"),
        ]
        result = cluster_from_neighbor_pairs(
            report(groups),
            [{"left_group_id": "g1", "right_group_id": "g2", "similarity": 0.97}],
            CONFIG,
        )
        self.assertEqual(verify_semantic_report(result)["input_rows"], 3)
        assigned = [row_id for item in result["semantic_clusters"] for row_id in item["row_ids"]]
        self.assertEqual(sorted(assigned), ["r1", "r2", "r3"])

    def test_output_is_deterministic(self):
        groups = [
            group("g2", "Northern Taiwan schools closed as typhoon arrives", 2, "r2"),
            group("g1", "Typhoon closes schools across northern Taiwan", 1, "r1"),
        ]
        pairs = [{"left_group_id": "g1", "right_group_id": "g2", "similarity": 0.97}]
        first = cluster_from_neighbor_pairs(report(groups), pairs, CONFIG)
        second = cluster_from_neighbor_pairs(copy.deepcopy(report(groups)), copy.deepcopy(pairs), CONFIG)
        self.assertEqual(json.dumps(first, ensure_ascii=False, sort_keys=True), json.dumps(second, ensure_ascii=False, sort_keys=True))
        vectors = [[1.0, 0.0], [0.999, 0.001], [0.0, 1.0]]
        neighbors = nearest_neighbor_pairs(vectors, top_k=2, minimum_similarity=0.95)
        self.assertEqual([(item["left_index"], item["right_index"]) for item in neighbors], [(0, 1)])
        sampled = select_embedding_groups(groups + [group("g3", "Budget bill passes parliament", 3, "r3")], 2, 20260821)
        self.assertEqual([item["group_id"] for item in sampled], [item["group_id"] for item in select_embedding_groups(groups + [group("g3", "Budget bill passes parliament", 3, "r3")], 2, 20260821)])


if __name__ == "__main__":
    unittest.main()

