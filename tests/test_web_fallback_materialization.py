import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import hydrate_source_rows as hydration
from scripts import build_source_candidate_list as candidates
from scripts import remote_acquisition_bridge_v2 as bridge
from scripts import validate_source_scan_evidence as validator


MAIN_SHA = "a" * 40
RUN_ID = "gnb-20260906T000000Z-a1b2c3d4"
WINDOW = {
    "start": "2026-09-05T06:00:00+08:00",
    "end": "2026-09-06T06:00:00+08:00",
}


def request(**updates):
    value = {
        "schema_version": "1.0",
        "operation": "web_fallback_materialize",
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "batch_sequence": 1,
        "search_provider": "host_web_search",
        "search_query": "global major news 2026-09-06",
        "search_evidence_url": "https://github.com/example/news/issues/3",
        "searched_at": "2026-09-06T05:50:00+08:00",
        "primary_failure_evidence": ["GDELT ZIP transport unavailable"],
        "terminal_reason": "bounded_search_complete",
        "results": [{
            "result_id": "result-001",
            "search_rank": 1,
            "url": "https://news.example/world/story-1",
            "title": "Global fixture",
            "summary": "A verified global search result.",
            "published_at": "2026-09-06T04:30:00+08:00",
            "url_evidence": "https://news.example/world/story-1",
            "published_evidence": "2026-09-06T04:30:00+08:00",
            "discovery_priority_reason": "cross-border public impact",
            "section": "GLB",
        }],
    }
    value.update(updates)
    return value


class WebFallbackMaterializationTests(unittest.TestCase):
    def test_validates_bounded_truthful_request(self):
        self.assertEqual(
            "web_fallback_materialize",
            bridge.validate(request(), MAIN_SHA)["operation"],
        )

    def test_rejects_private_url_and_non_global_section(self):
        bad_url = request()
        bad_url["results"][0]["url"] = "https://127.0.0.1/story"
        with self.assertRaisesRegex(ValueError, "public HTTPS"):
            bridge.validate(bad_url, MAIN_SHA)
        bad_section = request()
        bad_section["results"][0]["section"] = "TWN"
        with self.assertRaisesRegex(ValueError, "GLB"):
            bridge.validate(bad_section, MAIN_SHA)

    def test_rejects_result_outside_window(self):
        value = request()
        value["results"][0]["published_at"] = "2026-09-05T05:59:59+08:00"
        with self.assertRaisesRegex(ValueError, "exact run window"):
            bridge.validate(value, MAIN_SHA)

    def test_materializes_validator_and_candidate_builder_inputs_without_claiming_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runlogs = root / "runlogs"
            runtime = root / "runtime"
            runtime.mkdir()
            output = bridge.execute(request(), runtime, runlogs)
            scan = json.loads((output / "source-scans" / "web_fallback.json").read_text(encoding="utf-8"))
            coverage = json.loads((output / "source-coverage.json").read_text(encoding="utf-8"))
            web_coverage = next(item for item in coverage if item["source_id"] == "web_fallback")
            self.assertFalse(scan["coverage_complete"])
            self.assertEqual("degraded_partial", scan["coverage_status"])
            self.assertEqual(1, web_coverage["within_window_count"])
            self.assertEqual([], validator.validate_scan(
                scan,
                web_coverage,
                {"source_id": "web_fallback", "homepage": "", "allow_external_article_urls": True},
            ))
            snapshot = Path(scan["pages"][0]["snapshot_path"])
            self.assertTrue(snapshot.is_file())
            self.assertIn("bounded_search_complete", snapshot.read_text(encoding="utf-8"))
            pool = {
                "discovery_sources": [{"source_id": "gdelt", "name": "GDELT", "default_section": "GLB"}],
                "discovery_policy": {"minimum_ready_sources": 1},
                "acquisition_policy": {"cross_source_fallback_may_add_candidates": True},
            }
            built = candidates.build(
                pool,
                output / "source-scans",
                bridge.v1._parse_time(WINDOW["start"], "start"),
                bridge.v1._parse_time(WINDOW["end"], "end"),
            )
            self.assertEqual("web_fallback", built["items"][0]["source_id"])
            self.assertEqual("GLB", built["items"][0]["section"])

    def test_same_batch_is_idempotent_and_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runlogs = root / "runlogs"
            runtime = root / "runtime"
            runtime.mkdir()
            bridge.execute(request(), runtime, runlogs)
            bridge.execute(request(), runtime, runlogs)
            receipt = runlogs / "logs" / "runs" / RUN_ID / "remote-acquisition" / "web-fallback" / "batch-0001.jsonl"
            self.assertEqual(2, len(receipt.read_text(encoding="utf-8").splitlines()))
            conflict = request(search_query="different query")
            with self.assertRaisesRegex(ValueError, "does not match"):
                bridge.execute(conflict, runtime, runlogs)

    def test_prepare_receipt_survives_before_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = bridge.prepare_web_fallback(request(), root / "runlogs")
            records = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(records))
            self.assertEqual("running", json.loads(records[0])["status"])
            bridge.execute(request(), root / "runtime", root / "runlogs")
            self.assertEqual(2, len(path.read_text(encoding="utf-8").splitlines()))

    def test_merges_existing_regional_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "runlogs" / "logs" / "runs" / RUN_ID / "remote-acquisition"
            output.mkdir(parents=True)
            regional = [{"source_id": "cna", "scan_status": "completed"}]
            (output / "source-coverage.json").write_text(json.dumps(regional), encoding="utf-8")
            bridge.execute(request(), root / "runtime", root / "runlogs")
            coverage = json.loads((output / "source-coverage.json").read_text(encoding="utf-8"))
            self.assertEqual(["cna", "web_fallback"], [item["source_id"] for item in coverage])

    def test_cross_batch_duplicate_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge.execute(request(), root / "runtime", root / "runlogs")
            second = request(batch_sequence=2, search_query="second bounded query")
            second["results"][0]["url"] = "https://another.example/story-2"
            with self.assertRaisesRegex(ValueError, "identity repeated across batches"):
                bridge.execute(second, root / "runtime", root / "runlogs")

    def test_web_fallback_article_hydration_allows_public_cross_site_url(self):
        candidates = {
            "items": [{
                "row_id": "row-" + "1" * 24,
                "candidate_id": "candidate-1",
                "source_id": "web_fallback",
                "canonical_url": "https://news.example/world/story-1",
            }],
        }
        html = b'<meta property="article:published_time" content="2026-09-06T04:30:00+08:00">'
        with patch.object(hydration, "fetch", return_value=(html, "https://news.example/world/story-1", "text/html")):
            rows = hydration.hydrate(
                candidates,
                ["row-" + "1" * 24],
                bridge.v1._parse_time(WINDOW["start"], "start"),
                bridge.v1._parse_time(WINDOW["end"], "end"),
            )
        self.assertEqual("content_ready", rows[0]["status"])


if __name__ == "__main__":
    unittest.main()
