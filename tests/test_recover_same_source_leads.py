import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recover_same_source_leads.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_source_scan_evidence", ROOT / "scripts" / "validate_source_scan_evidence.py"
)
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
assert VALIDATOR_SPEC.loader is not None
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


def load_module():
    if not SCRIPT.is_file():
        return None
    spec = importlib.util.spec_from_file_location("recover_same_source_leads", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SameSourceRecoveryTests(unittest.TestCase):
    def fixture(self, root: Path):
        ranking = json.loads(
            (ROOT / "news-source-pool.json").read_text(encoding="utf-8")
        )["ranking"]
        pool = {
            "ranking": ranking,
            "discovery_sources": [{
                "source_id": "wire", "name": "Wire", "homepage": "https://example.com/",
                "section": "TWN", "categories": ["politics"],
            }]
        }
        scan_dir = root / "scans"
        scan_dir.mkdir()
        primary_text = "https://example.com/news/old 2026-08-16T00:00:00+08:00"
        primary = root / "primary.html"
        primary.write_text(primary_text, encoding="utf-8")
        old = {
            "url": "https://example.com/news/old", "title": "Old", "summary": "Old",
            "published_at": "2026-08-16T00:00:00+08:00",
            "url_evidence": "https://example.com/news/old",
            "published_evidence": "2026-08-16T00:00:00+08:00",
            "discovery_priority_reason": "Old", "acquisition_route": "html_direct", "categories": [],
        }
        scan = {
            "schema_version": "1.0.0", "source_id": "wire", "collector": "html_direct",
            "generated_at": "2026-08-17T20:00:00+08:00",
            "window_start": "2026-08-16T20:00:00+08:00",
            "window_end": "2026-08-17T20:00:00+08:00",
            "pages": [{
                "request_url": "https://example.com/latest", "fetched_at": "2026-08-17T20:00:00+08:00",
                "http_status": 200, "snapshot_path": str(primary),
                "sha256": hashlib.sha256(primary_text.encode()).hexdigest(), "next_url": None,
                "extracted_items": [old],
            }],
            "terminal_proof": {"type": "crossed_window_start", "page_index": 1,
                               "witness_url": old["url"]},
        }
        (scan_dir / "wire.json").write_text(json.dumps(scan), encoding="utf-8")
        coverage = [{
            "source_id": "wire", "status": "completed", "within_window_count": 0,
            "ranked_count": 0, "ranked_items": [], "selected_for_pool_count": 0,
            "selected_item_urls": [], "discovery_ranking_completed": True,
            "discovery_ranking_method": "discovery_priority_v1", "failure_reason": None,
            "scan_window_start": scan["window_start"], "scan_window_end": scan["window_end"],
            "scan_evidence_path": str(scan_dir / "wire.json"),
        }]
        return pool, scan_dir, coverage

    def article_html(self, url="https://example.com/news/policy"):
        return json.dumps({
            "@context": "https://schema.org", "@type": "NewsArticle", "url": url,
            "headline": "中央政策正式生效", "description": "全國公共服務規則已改變。",
            "datePublished": "2026-08-17T13:54:00+08:00",
        }, ensure_ascii=False).join(("<script type='application/ld+json'>", "</script>"))

    def test_direct_same_source_lead_is_added_to_supplemental_pages(self):
        self.assertTrue(SCRIPT.is_file(), "missing canonical same-source recovery tool")
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool, scan_dir, coverage = self.fixture(root)
            raw = self.article_html().encode("utf-8")

            def fetcher(url, timeout_seconds):
                if url.endswith("/alternate-feed"):
                    return url, 200, "text/html; charset=utf-8", self.article_html(
                        "https://example.com/news/alternate"
                    ).encode("utf-8")
                return url, 200, "text/html; charset=utf-8", raw

            report = module.recover(
                pool, scan_dir, coverage,
                [
                    {"lead_id": "lead-1", "sweep_id": "central_policy_institutions",
                     "source_id": "wire", "url": "https://example.com/news/policy"},
                    {"lead_id": "lead-1b", "sweep_id": "central_policy_institutions",
                     "source_id": "wire", "url": "https://example.com/news/alternate",
                     "alternate_url": "https://example.com/alternate-feed"},
                ],
                root / "snapshots", fetcher=fetcher,
            )
            scan = json.loads((scan_dir / "wire.json").read_text(encoding="utf-8"))
            self.assertEqual("completed", report["status"])
            self.assertEqual("same_source_direct", scan["supplemental_pages"][0]["recovery_route"])
            self.assertEqual("https://example.com/news/policy",
                             scan["supplemental_pages"][0]["extracted_items"][0]["url"])
            self.assertEqual("same_source_alternate", scan["supplemental_pages"][1]["recovery_route"])
            self.assertEqual(2, coverage[0]["within_window_count"])
            self.assertIn("https://example.com/news/policy", coverage[0]["selected_item_urls"])
            self.assertEqual([], VALIDATOR.validate_scan(scan, coverage[0], pool["discovery_sources"][0]))

    def test_browser_dom_snapshot_uses_the_same_validation_path(self):
        self.assertTrue(SCRIPT.is_file(), "missing canonical same-source recovery tool")
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool, scan_dir, coverage = self.fixture(root)
            snapshot = root / "browser.html"
            snapshot.write_text(self.article_html(), encoding="utf-8")
            base_lead = {
                "lead_id": "lead-2", "sweep_id": "central_policy_institutions",
                "source_id": "wire", "url": "https://example.com/news/policy",
                "acquisition_route": "browser_rendered", "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            }
            with self.assertRaisesRegex(ValueError, "final fallback"):
                module.recover(
                    pool, scan_dir, coverage, [base_lead], root / "snapshots",
                    fetcher=lambda *_: self.fail("browser snapshot must not refetch"),
                )
            base_lead["prior_attempts"] = [
                {"route": "same_source_direct", "status": "failed"},
                {"route": "same_source_alternate", "status": "failed"},
            ]
            report = module.recover(
                pool, scan_dir, coverage,
                [base_lead],
                root / "snapshots", fetcher=lambda *_: self.fail("browser snapshot must not refetch"),
            )
            scan = json.loads((scan_dir / "wire.json").read_text(encoding="utf-8"))
            self.assertEqual("completed", report["status"])
            self.assertEqual("browser_rendered", scan["supplemental_pages"][0]["recovery_route"])

    def test_cross_source_redirect_is_rejected_without_mutating_scan(self):
        self.assertTrue(SCRIPT.is_file(), "missing canonical same-source recovery tool")
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool, scan_dir, coverage = self.fixture(root)
            before = (scan_dir / "wire.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "same-source"):
                module.recover(
                    pool, scan_dir, coverage,
                    [{"lead_id": "lead-3", "sweep_id": "central_policy_institutions",
                      "source_id": "wire", "url": "https://example.com/news/policy"}],
                    root / "snapshots",
                    fetcher=lambda *_: ("https://evil.example/news/policy", 200, "text/html", b"x"),
                )
            self.assertEqual(before, (scan_dir / "wire.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
