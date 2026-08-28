import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "build_source_candidate_list.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class CandidateListTests(unittest.TestCase):
    def test_builds_from_available_gdelt_scan_without_publisher_gate(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            scan_dir = Path(tmp)
            (scan_dir / "gdelt.json").write_text(json.dumps({
                "source_id": "gdelt",
                "collector": "aggregate_api",
                "pages": [{
                    "snapshot_path": "snapshots/gdelt.json",
                    "extracted_items": [{
                        "title": "Major international event",
                        "summary": "Material policy change affecting the public.",
                        "discovery_priority_reason": "May change policy across a broad population.",
                        "published_at": "2026-08-16T01:00:00+00:00",
                        "url": "https://example.com/world-event?utm_source=gdelt",
                        "section": "GLB",
                        "acquisition_route": "aggregate_api",
                    }],
                }],
            }), encoding="utf-8")

            result = builder.build(
                pool,
                scan_dir,
                builder.parse_time("2026-08-15T02:00:00+00:00"),
                builder.parse_time("2026-08-16T02:00:00+00:00"),
            )

        self.assertEqual(1, result["source_count"])
        self.assertEqual(["gdelt"], result["sources"])
        self.assertEqual("GLB", result["items"][0]["section"])
        self.assertEqual("https://example.com/world-event", result["items"][0]["canonical_url"])

    def test_builds_all_available_discovery_lists_and_supplemental_pages(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            scan_dir = Path(tmp)
            for source in pool["discovery_sources"]:
                source_id = source["source_id"]
                (scan_dir / f"{source_id}.json").write_text(json.dumps({
                    "source_id": source_id,
                    "collector": "browser_rendered",
                    "pages": [{
                        "snapshot_path": f"snapshots/{source_id}.html",
                        "extracted_items": [{
                            "title": f"{source_id} major event",
                            "summary": "Material policy change affecting the public.",
                            "discovery_priority_reason": "May change public policy and affect a broad population.",
                            "published_at": "2026-08-16T01:00:00+00:00",
                            "url": f"https://example.com/{source_id}?utm_source=test",
                            "section": source.get("default_section") or source["sections"][0],
                            "acquisition_route": "browser_rendered"
                        }]
                    }],
                    "supplemental_pages": ([{
                        "snapshot_path": "snapshots/cna-supplement.html",
                        "extracted_items": [{
                            "title": "cna recovered policy event",
                            "summary": "Recovered through verified same-source evidence.",
                            "discovery_priority_reason": "Central policy changed public services.",
                            "published_at": "2026-08-16T01:30:00+00:00",
                            "url": "https://example.com/cna-recovered",
                            "acquisition_route": "same_source_direct",
                        }],
                    }] if source_id == "cna" else []),
                }), encoding="utf-8")
            result = builder.build(pool, scan_dir, builder.parse_time("2026-08-15T02:00:00+00:00"), builder.parse_time("2026-08-16T02:00:00+00:00"))
        self.assertEqual(result["source_count"], 3)
        self.assertEqual(len(result["items"]), 4)
        self.assertTrue(any(item["url"] == "https://example.com/cna-recovered" for item in result["items"]))
        self.assertTrue(all(item["summary"] and item["discovery_priority_reason"] for item in result["items"]))
        self.assertTrue(all("utm_source" not in item["canonical_url"] for item in result["items"]))

    def test_no_available_discovery_list_fails_closed(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "可用新聞發現清單不足"):
                builder.build(pool, Path(tmp), builder.parse_time("2026-08-15T02:00:00+00:00"), builder.parse_time("2026-08-16T02:00:00+00:00"))

    def test_verified_web_fallback_enters_candidate_list_with_truthful_provenance(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            scan_dir = Path(tmp)
            (scan_dir / "web_fallback.json").write_text(json.dumps({
                "source_id": "web_fallback",
                "collector": "verified-web-search-fallback",
                "coverage_complete": False,
                "coverage_status": "degraded_partial",
                "pages": [{
                    "snapshot_path": "snapshots/web-fallback.json",
                    "extracted_items": [{
                        "title": "Verified global event",
                        "summary": "A verified international event with public impact.",
                        "discovery_priority_reason": "Restores global recall after the primary route failed.",
                        "published_at": "2026-08-16T01:00:00+00:00",
                        "url": "https://www.reuters.com/world/example",
                        "section": "GLB",
                    }],
                }],
            }), encoding="utf-8")

            result = builder.build(
                pool, scan_dir,
                builder.parse_time("2026-08-15T02:00:00+00:00"),
                builder.parse_time("2026-08-16T02:00:00+00:00"),
            )

        self.assertEqual(["web_fallback"], result["sources"])
        self.assertEqual("web_fallback", result["items"][0]["source_id"])
        self.assertEqual("web_search_fallback", result["items"][0]["acquisition_route"])


if __name__ == "__main__":
    unittest.main()
