import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from pilot_lossless_article_grouping import (  # noqa: E402
    build_report,
    canonicalize_url,
    verify_report,
)


def fixture_payload():
    return {
        "items": [
            {
                "candidate_id": "url-1",
                "source_id": "alpha",
                "section": "world",
                "title": "Major storm closes ports",
                "url": "https://example.com/story?id=7&utm_source=test",
                "published_at": "2026-08-20T01:00:00Z",
            },
            {
                "candidate_id": "url-2",
                "source_id": "alpha-feed",
                "section": "world",
                "title": "Port closures after a major storm",
                "url": "https://EXAMPLE.com/story?id=7#top",
                "published_at": "2026-08-20T01:05:00Z",
            },
            {
                "candidate_id": "title-1",
                "source_id": "beta",
                "section": "china",
                "title": "多省啟動跨區防汛應急響應",
                "url": "https://beta.example/1",
                "published_at": "2026-08-20T02:00:00Z",
            },
            {
                "candidate_id": "title-2",
                "source_id": "gamma",
                "section": "china",
                "title": "多省啟動跨區防汛應急響應！",
                "url": "https://gamma.example/2",
                "published_at": "2026-08-20T02:10:00Z",
            },
            {
                "candidate_id": "placeholder-1",
                "source_id": "delta",
                "section": "taiwan",
                "title": "Delta News Report",
                "url": "https://delta.example/a",
                "published_at": "2026-08-20T03:00:00Z",
            },
            {
                "candidate_id": "placeholder-2",
                "source_id": "delta",
                "section": "taiwan",
                "title": "Delta News Report",
                "url": "https://delta.example/b",
                "published_at": "2026-08-20T03:15:00Z",
            },
            {
                "candidate_id": "singleton",
                "source_id": "epsilon",
                "section": "world",
                "title": "Country declares a nationwide emergency",
                "url": "https://epsilon.example/emergency",
                "published_at": "2026-08-20T04:00:00Z",
            },
            {
                "candidate_id": "opaque-1",
                "source_id": "zeta",
                "section": "world",
                "title": "C07R3YLYKN8O",
                "url": "https://zeta.example/opaque-a",
                "published_at": "2026-08-20T04:10:00Z",
            },
            {
                "candidate_id": "opaque-2",
                "source_id": "zeta",
                "section": "world",
                "title": "C07R3YLYKN8O",
                "url": "https://zeta.example/opaque-b",
                "published_at": "2026-08-20T04:20:00Z",
            },
            {
                "candidate_id": "container-1",
                "source_id": "eta",
                "section": "world",
                "title": "Comment Page 1",
                "url": "https://eta.example/container-a",
                "published_at": "2026-08-20T04:30:00Z",
            },
            {
                "candidate_id": "container-2",
                "source_id": "eta",
                "section": "world",
                "title": "Comment Page 1",
                "url": "https://eta.example/container-b",
                "published_at": "2026-08-20T04:40:00Z",
            },
        ]
    }


class LosslessArticleGroupingTests(unittest.TestCase):
    def test_canonical_url_removes_tracking_and_fragment(self):
        left = canonicalize_url("https://Example.com/a?id=2&utm_medium=social#part")
        right = canonicalize_url("https://example.com/a?id=2")
        self.assertEqual(left, right)

    def test_every_input_row_is_assigned_exactly_once(self):
        payload = fixture_payload()
        report = build_report(payload, sample_size=10, seed=7)
        assigned = [row_id for group in report["groups"] for row_id in group["row_ids"]]
        expected = report["input_row_ids"]
        self.assertEqual(sorted(assigned), sorted(expected))
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_same_canonical_url_is_consolidated_as_evidence(self):
        report = build_report(fixture_payload(), sample_size=10, seed=7)
        group = next(group for group in report["groups"] if "url-1" in group["candidate_ids"])
        self.assertEqual(group["group_kind"], "canonical_url")
        self.assertEqual(set(group["candidate_ids"]), {"url-1", "url-2"})

    def test_same_usable_title_and_section_is_consolidated(self):
        report = build_report(fixture_payload(), sample_size=10, seed=7)
        group = next(group for group in report["groups"] if "title-1" in group["candidate_ids"])
        self.assertEqual(group["group_kind"], "exact_title")
        self.assertEqual(set(group["candidate_ids"]), {"title-1", "title-2"})

    def test_placeholder_titles_are_preserved_as_separate_recovery_rows(self):
        report = build_report(fixture_payload(), sample_size=10, seed=7)
        placeholder_groups = [
            group for group in report["groups"]
            if set(group["candidate_ids"]) & {"placeholder-1", "placeholder-2"}
        ]
        self.assertEqual(len(placeholder_groups), 2)
        self.assertTrue(all(group["group_kind"] == "needs_title_recovery" for group in placeholder_groups))
        recovery_ids = {row["candidate_id"] for row in report["review_queues"]["title_recovery"]}
        self.assertTrue({"placeholder-1", "placeholder-2"} <= recovery_ids)
        for candidate_id in ("opaque-1", "opaque-2", "container-1", "container-2"):
            group = next(group for group in report["groups"] if candidate_id in group["candidate_ids"])
            self.assertEqual(group["group_kind"], "needs_title_recovery")

    def test_report_does_not_make_importance_or_non_news_decisions(self):
        report = build_report(fixture_payload(), sample_size=10, seed=7)
        forbidden = {"grade", "score", "importance", "non_news", "publish", "drop"}
        for group in report["groups"]:
            self.assertTrue(forbidden.isdisjoint(group))

    def test_duplicate_candidate_ids_preserve_both_input_rows(self):
        payload = fixture_payload()
        payload["items"][1]["candidate_id"] = payload["items"][0]["candidate_id"]
        report = build_report(payload, sample_size=10, seed=7)
        assigned = [row_id for group in report["groups"] for row_id in group["row_ids"]]
        self.assertEqual(len(assigned), len(payload["items"]))
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_output_is_deterministic(self):
        first = build_report(fixture_payload(), sample_size=2, seed=7)
        second = build_report(copy.deepcopy(fixture_payload()), sample_size=2, seed=7)
        self.assertEqual(
            json.dumps(first, ensure_ascii=False, sort_keys=True),
            json.dumps(second, ensure_ascii=False, sort_keys=True),
        )

    def test_verify_report_rejects_tampered_assignments(self):
        report = build_report(fixture_payload(), sample_size=10, seed=7)
        report["groups"][0]["row_ids"].append(report["input_row_ids"][0])
        with self.assertRaisesRegex(ValueError, "article-row conservation failed"):
            verify_report(report)

    def test_report_round_trips_through_json(self):
        report = build_report(fixture_payload(), sample_size=10, seed=7)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(verify_report(loaded)["input_article_rows"], 11)


if __name__ == "__main__":
    unittest.main()

