import copy
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from pilot_url_recovery_batched_triage import (  # noqa: E402
    build_model_batches,
    build_recovered_report,
    recover_title_from_url,
    validate_model_batch_response,
    verify_recovered_report,
)


def item(candidate_id, section, title, url, minute):
    return {
        "candidate_id": candidate_id,
        "source_id": "gdelt",
        "section": section,
        "title": title,
        "url": url,
        "published_at": f"2026-08-20T01:{minute:02d}:00Z",
    }


def fixture_payload():
    return {
        "items": [
            item("original", "GLB", "Government closes three airports after eruption", "https://a.test/100", 0),
            item("recover-1", "GLB", "a.test news report", "https://a.test/world/massive-fire-closes-three-airports-1234.html", 1),
            item("recover-2", "GLB", "b.test news report", "https://b.test/news/massive-fire-closes-three-airports-9876/", 2),
            item("cross-section", "TWN", "c.test news report", "https://c.test/massive-fire-closes-three-airports-5555", 3),
            item("numeric", "GLB", "article 906031", "https://d.test/article/906031", 4),
            item("opaque", "GLB", "d.test news report", "https://d.test/IMSZEDBKTRHKNOPFXL4RKGGJZQ", 5),
        ]
    }


class UrlRecoveryBatchedTriageTests(unittest.TestCase):
    def test_descriptive_url_slug_recovers_title(self):
        self.assertEqual(
            recover_title_from_url("https://site.test/world/massive-fire-closes-three-airports-1234.html"),
            "massive fire closes three airports",
        )

    def test_numeric_opaque_and_navigation_paths_do_not_recover(self):
        self.assertIsNone(recover_title_from_url("https://site.test/article/906031"))
        self.assertIsNone(recover_title_from_url("https://site.test/IMSZEDBKTRHKNOPFXL4RKGGJZQ"))
        self.assertIsNone(recover_title_from_url("https://site.test/news/world/latest"))
        self.assertIsNone(recover_title_from_url("https://site.test/posts/150d5a14-9a1a-4b02-a9b5-a93ef1ede4b2"))
        self.assertIsNone(recover_title_from_url("https://site.test/Detail/2026/08/20/774699/Press-TV-s-news-headlines-"))
        self.assertIsNone(recover_title_from_url("https://site.test/oil_and_gas/262634.html"))
        payload = {
            "items": [
                item("bad-1", "GLB", "www.koreaherald.com news report", "https://www.koreaherald.com/article/10847330", 1),
                item("bad-2", "GLB", "www.koreaherald.com:443 news report", "https://www.koreaherald.com/article/10847063", 2),
            ]
        }
        report = build_recovered_report(payload, batch_size=2, sample_size=10, seed=7)
        self.assertEqual(report["review_queues"]["suspected_missed_merges"], [])

    def test_original_usable_title_wins(self):
        report = build_recovered_report(fixture_payload(), batch_size=3, sample_size=3, seed=7)
        group = next(group for group in report["groups"] if "original" in group["candidate_ids"])
        self.assertEqual(group["effective_title"], "Government closes three airports after eruption")
        self.assertEqual(group["title_provenance"], "original")

    def test_same_recovered_title_in_same_section_groups(self):
        report = build_recovered_report(fixture_payload(), batch_size=3, sample_size=3, seed=7)
        group = next(group for group in report["groups"] if "recover-1" in group["candidate_ids"])
        self.assertEqual(set(group["candidate_ids"]), {"recover-1", "recover-2"})
        self.assertEqual(group["group_kind"], "recovered_exact_title")

    def test_same_recovered_title_in_different_section_stays_separate(self):
        report = build_recovered_report(fixture_payload(), batch_size=3, sample_size=3, seed=7)
        group = next(group for group in report["groups"] if "cross-section" in group["candidate_ids"])
        self.assertEqual(group["candidate_ids"], ["cross-section"])

    def test_every_row_is_conserved_even_when_candidate_id_repeats(self):
        payload = fixture_payload()
        payload["items"][1]["candidate_id"] = payload["items"][0]["candidate_id"]
        report = build_recovered_report(payload, batch_size=3, sample_size=3, seed=7)
        assigned = [row_id for group in report["groups"] for row_id in group["row_ids"]]
        self.assertEqual(sorted(assigned), sorted(report["input_row_ids"]))
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_model_batches_cover_every_group_once_with_size_limit(self):
        groups = [
            {
                "group_id": f"g-{index:03d}",
                "section": "GLB",
                "effective_title": str(index),
                "evidence": [{"url": f"https://source.test/{index}/{source}", "source_id": str(source)} for source in range(5)],
            }
            for index in range(205)
        ]
        batches = build_model_batches(groups, batch_size=100)
        ids = [group["group_id"] for batch in batches for group in batch["items"]]
        self.assertEqual(len(batches), 3)
        self.assertEqual(sorted(ids), sorted(group["group_id"] for group in groups))
        self.assertTrue(all(len(batch["items"]) <= 100 for batch in batches))
        allowed = {"group_id", "section", "effective_title", "evidence_count", "earliest_published_at"}
        self.assertTrue(all(set(group) == allowed for batch in batches for group in batch["items"]))

    def test_report_is_deterministic(self):
        first = build_recovered_report(fixture_payload(), batch_size=3, sample_size=3, seed=7)
        second = build_recovered_report(copy.deepcopy(fixture_payload()), batch_size=3, sample_size=3, seed=7)
        self.assertEqual(json.dumps(first, ensure_ascii=False, sort_keys=True), json.dumps(second, ensure_ascii=False, sort_keys=True))

    def test_verifier_rejects_duplicate_batch_group(self):
        report = build_recovered_report(fixture_payload(), batch_size=3, sample_size=3, seed=7)
        report["model_batches"][0]["items"].append(copy.deepcopy(report["model_batches"][0]["items"][0]))
        with self.assertRaisesRegex(ValueError, "model batch coverage failed"):
            verify_recovered_report(report)

    def test_model_response_validator_accepts_exact_batch_contract(self):
        batch = build_model_batches(
            [{"group_id": "g-001", "section": "GLB", "effective_title": "event", "evidence": []}],
            batch_size=100,
        )[0]
        response = {
            "batch_id": batch["batch_id"],
            "sha256": batch["sha256"],
            "results": [{"group_id": "g-001", "event_fingerprint": "event-1"}],
        }
        self.assertEqual(validate_model_batch_response(batch, response), {"validated_results": 1})

    def test_model_response_validator_rejects_hash_and_id_mismatches(self):
        batch = build_model_batches(
            [
                {"group_id": "g-001", "section": "GLB", "effective_title": "event one", "evidence": []},
                {"group_id": "g-002", "section": "GLB", "effective_title": "event two", "evidence": []},
            ],
            batch_size=100,
        )[0]
        valid = {
            "batch_id": batch["batch_id"],
            "sha256": batch["sha256"],
            "results": [{"group_id": "g-001"}, {"group_id": "g-002"}],
        }
        cases = []
        wrong_hash = copy.deepcopy(valid)
        wrong_hash["sha256"] = "0" * 64
        cases.append(wrong_hash)
        missing_id = copy.deepcopy(valid)
        missing_id["results"] = [{"group_id": "g-001"}]
        cases.append(missing_id)
        duplicate_id = copy.deepcopy(valid)
        duplicate_id["results"] = [{"group_id": "g-001"}, {"group_id": "g-001"}]
        cases.append(duplicate_id)
        extra_id = copy.deepcopy(valid)
        extra_id["results"].append({"group_id": "g-003"})
        cases.append(extra_id)
        for response in cases:
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    validate_model_batch_response(batch, response)


if __name__ == "__main__":
    unittest.main()

