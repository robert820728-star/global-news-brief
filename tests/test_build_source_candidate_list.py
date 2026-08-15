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
    def test_builds_fifteen_source_dedup_ready_list(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            scan_dir = Path(tmp)
            for source in pool["sources"]:
                source_id = source["source_id"]
                (scan_dir / f"{source_id}.json").write_text(json.dumps({
                    "source_id": source_id,
                    "collector": "browser_rendered",
                    "pages": [{
                        "snapshot_path": f"snapshots/{source_id}.html",
                        "extracted_items": [{
                            "title": f"{source_id} major event",
                            "summary": "Material policy change affecting the public.",
                            "importance_hint": "May change public policy and affect a broad population.",
                            "published_at": "2026-08-16T01:00:00+00:00",
                            "url": f"https://example.com/{source_id}?utm_source=test",
                            "acquisition_route": "browser_rendered"
                        }]
                    }]
                }), encoding="utf-8")
            result = builder.build(pool, scan_dir, builder.parse_time("2026-08-15T02:00:00+00:00"), builder.parse_time("2026-08-16T02:00:00+00:00"))
        self.assertEqual(result["source_count"], 15)
        self.assertEqual(len(result["items"]), 15)
        self.assertTrue(all(item["summary"] and item["importance_hint"] for item in result["items"]))
        self.assertTrue(all("utm_source" not in item["canonical_url"] for item in result["items"]))

    def test_missing_source_fails_closed(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "缺少來源掃描"):
                builder.build(pool, Path(tmp), builder.parse_time("2026-08-15T02:00:00+00:00"), builder.parse_time("2026-08-16T02:00:00+00:00"))


if __name__ == "__main__":
    unittest.main()
