import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "materialize_source_scans", ROOT / "scripts" / "materialize_source_scans.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_source_scan_evidence", ROOT / "scripts" / "validate_source_scan_evidence.py"
)
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
assert VALIDATOR_SPEC.loader is not None
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


class MaterializeSourceScansTests(unittest.TestCase):
    def test_more_than_thirty_items_all_enter_candidate_pool(self):
        articles = [
            {
                "url": f"https://example.net/world/event-{index}",
                "title": f"World event {index}",
                "seendate": f"20260818T10{index:02d}00Z",
            }
            for index in range(35)
        ]
        payload = json.dumps({"articles": articles}, separators=(",", ":"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "gdelt.json"
            snapshot.write_bytes(payload.encode("utf-8"))
            route = {
                "source_id": "gdelt", "route": "aggregate_api",
                "request_url": "https://api.gdeltproject.org/api/v2/doc/doc",
                "http_status": 200, "content_type": "application/json",
                "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "route_ready": True, "source_exhaustion_marker": '"articles"',
            }
            source = {
                "source_id": "gdelt", "homepage": "https://api.gdeltproject.org/",
                "section": "GLB", "allow_external_article_urls": True,
            }
            _scan, coverage = MODULE.materialize_source(
                source, route, "2026-08-18T09:00:00+00:00",
                "2026-08-18T12:00:00+00:00", root,
            )
            self.assertEqual(35, coverage["ranked_count"])
            self.assertEqual(35, coverage["selected_for_pool_count"])
            self.assertEqual(
                [item["url"] for item in coverage["ranked_items"]],
                coverage["selected_item_urls"],
            )

    def test_gdelt_json_discovers_external_articles_and_image_hints(self):
        payload = json.dumps({"articles": [{
            "url": "https://example.net/world/major-event",
            "title": "Major international event",
            "seendate": "20260818T101500Z",
            "socialimage": "https://images.example.net/event.jpg",
            "domain": "example.net",
            "language": "English",
            "sourcecountry": "United States",
        }]})
        items = MODULE.parse_json_items(
            payload,
            "https://api.gdeltproject.org/api/v2/doc/doc",
            "https://api.gdeltproject.org/",
            "aggregate_api",
            2026,
            allow_external_links=True,
        )
        article = items["https://example.net/world/major-event"]
        self.assertEqual("2026-08-18T10:15:00+00:00", article["published_at"])
        self.assertEqual("https://images.example.net/event.jpg", article["image_url_hint"])

    def test_anchor_title_attribute_beats_numeric_slug(self):
        html = """<html><body>
<time class="story-list__time">2026-08-17 06:11</time>
<a href="/news/story/1/9695476" title="全國食安回收擴大"><img alt=""></a>
</body></html>"""
        items = MODULE.parse_html(
            html,
            "https://udn.com/news/breaknews/1",
            "https://udn.com/news/index",
            "html_direct",
            2026,
        )
        article = items["https://udn.com/news/story/1/9695476"]
        self.assertEqual("全國食安回收擴大", article["title"])

    def test_descriptive_duplicate_replaces_numeric_equal_time_title(self):
        html = """<html><body>
<time class="story-list__time">2026-08-17 06:11</time>
<a href="/news/story/1/9695476"><img alt=""></a>
<a href="/news/story/1/9695476" title="中央預算解凍案進入實質審查">中央預算解凍案進入實質審查</a>
</body></html>"""
        items = MODULE.parse_html(
            html,
            "https://udn.com/news/breaknews/1",
            "https://udn.com/news/index",
            "html_direct",
            2026,
        )
        article = items["https://udn.com/news/story/1/9695476"]
        self.assertEqual("中央預算解凍案進入實質審查", article["title"])

    def test_compact_month_day_time_and_url_date_are_supported(self):
        self.assertEqual("2026-08-15T23:54:00+08:00", MODULE.parse_time("8-15 23:54", 2026).isoformat())
        html = "<html><body><a href='https://www.news.cn/world/20260816/abc/c.html'>World report</a></body></html>"
        items = MODULE.parse_html(html, "https://www.news.cn/world/", "https://www.news.cn/", "html_direct", 2026)
        self.assertEqual("2026-08-16T12:00:00+08:00", items["https://www.news.cn/world/20260816/abc/c.html"]["published_at"])

    def test_rss_materialization_preserves_boundary_and_score_breakdown(self):
        rss = """<?xml version="1.0" encoding="utf-8"?>
<rss><channel>
<item><title>Major policy update</title><link>https://example.com/news/new</link>
<pubDate>Sun, 16 Aug 2026 08:00:00 +0800</pubDate><description>National policy takes effect.</description></item>
<item><title>Older report</title><link>https://example.com/news/old</link>
<pubDate>Sat, 15 Aug 2026 06:00:00 +0800</pubDate><description>Boundary witness.</description></item>
</channel></rss>"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "route.bin"
            snapshot.write_bytes(rss.encode("utf-8"))
            route = {
                "source_id": "wire", "route": "structured_direct",
                "request_url": "https://example.com/rss", "http_status": 200,
                "content_type": "application/xml; charset=utf-8", "bytes": len(rss.encode()),
                "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(rss.encode()).hexdigest(), "route_ready": True,
            }
            source = {"source_id": "wire", "homepage": "https://example.com/", "section": "GLB"}
            scan, coverage = MODULE.materialize_source(
                source, route, "2026-08-15T12:00:00+08:00", "2026-08-16T12:00:00+08:00", root
            )
            self.assertEqual("crossed_window_start", scan["terminal_proof"]["type"])
            self.assertEqual(1, coverage["within_window_count"])
            ranked = coverage["ranked_items"][0]
            self.assertEqual(set(MODULE.WEIGHTS), set(ranked["importance_breakdown"]))
            self.assertAlmostEqual(ranked["importance_score"], sum(ranked["importance_breakdown"].values()))
            self.assertEqual([], VALIDATOR.validate_scan(scan, coverage, source))

    def test_dynamic_html_page_cannot_use_closing_tag_as_exhaustion_proof(self):
        html = """<!doctype html><html><body>
<a href="/news/current">Current report</a><time>2026-08-16T09:00:00+08:00</time>
</body></html>"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "route.bin"
            snapshot.write_bytes(html.encode("utf-8"))
            route = {
                "source_id": "wire", "route": "html_direct",
                "request_url": "https://example.com/latest", "http_status": 200,
                "content_type": "text/html; charset=utf-8", "bytes": len(html.encode()),
                "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(html.encode()).hexdigest(), "route_ready": True,
            }
            source = {"source_id": "wire", "homepage": "https://example.com/", "section": "GLB"}
            with self.assertRaisesRegex(ValueError, "HTML route did not reach window boundary"):
                MODULE.materialize_source(
                    source, route, "2026-08-15T12:00:00+08:00", "2026-08-16T12:00:00+08:00", root
                )

    def test_cna_json_api_materializes_items_and_proves_source_exhaustion(self):
        payload = json.dumps({
            "Result": "Y",
            "ResultData": {
                "Items": [
                    {
                        "PageUrl": "https://www.cna.com.tw/news/aipl/202608170117.aspx",
                        "HeadLine": "中央政策最新進展",
                        "CreateTime": "2026/08/17 13:54",
                    },
                    {
                        "PageUrl": "https://www.cna.com.tw/news/aipl/202608160321.aspx",
                        "HeadLine": "前一日政策報導",
                        "CreateTime": "2026/08/16 22:06",
                    },
                ],
                "NextPageIdx": "",
            },
        }, ensure_ascii=False, separators=(",", ":"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "cna.json"
            snapshot.write_bytes(payload.encode("utf-8"))
            route = {
                "source_id": "cna", "route": "structured_direct",
                "request_url": "https://www.cna.com.tw/cna2018api/api/WNewsList",
                "request_method": "POST",
                "json_exhaustion_path": ["ResultData", "NextPageIdx"],
                "http_status": 200, "content_type": "application/json; charset=utf-8",
                "bytes": len(payload.encode("utf-8")), "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "route_ready": True,
            }
            source = {"source_id": "cna", "homepage": "https://www.cna.com.tw/", "section": "TWN"}
            scan, coverage = MODULE.materialize_source(
                source, route, "2026-08-16T21:17:00+08:00", "2026-08-17T21:17:00+08:00", root
            )
            self.assertEqual(2, coverage["within_window_count"])
            self.assertEqual("source_exhausted", scan["terminal_proof"]["type"])
            self.assertIn("NextPageIdx", scan["terminal_proof"]["terminal_marker"])
            self.assertEqual([], VALIDATOR.validate_scan(scan, coverage, source))

    def test_udn_multipage_json_uses_title_link_nested_local_time_and_escaped_evidence(self):
        payload = r'''[{"state":true,"page":"2","end":false,"lists":[
          {"titleLink":"\/news\/story\/7266\/9697340","title":"中央政策最新進展",
           "paragraph":"政策說明","time":{"date":"2026-08-17 21:28","dateTime":"2026-08-17T21:28:03Z"}},
          {"titleLink":"\/news\/story\/6656\/9696001","title":"前一日政策報導",
           "paragraph":"邊界證據","time":{"date":"2026-08-16 22:40","dateTime":"2026-08-16T22:40:00Z"}}
        ]}]'''
        parsed = MODULE.parse_json_items(
            payload, "https://udn.com/api/more", "https://udn.com/", "structured_direct", 2026
        )
        self.assertEqual(2, len(parsed))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "udn-pages.json"
            snapshot.write_bytes(payload.encode("utf-8"))
            route = {
                "source_id": "udn", "route": "structured_direct",
                "request_url": "https://udn.com/api/more", "http_status": 200,
                "content_type": "application/json; charset=utf-8",
                "bytes": len(payload.encode("utf-8")), "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "route_ready": True,
            }
            source = {"source_id": "udn", "homepage": "https://udn.com/", "section": "TWN"}
            scan, coverage = MODULE.materialize_source(
                source, route, "2026-08-16T22:57:00+08:00", "2026-08-17T22:57:00+08:00", root
            )
            self.assertEqual("crossed_window_start", scan["terminal_proof"]["type"])
            self.assertEqual(1, coverage["within_window_count"])
            self.assertEqual(
                "2026-08-17T21:28:00+08:00", coverage["ranked_items"][0]["published_at"]
            )
            self.assertEqual([], VALIDATOR.validate_scan(scan, coverage, source))

    def test_route_page_snapshots_form_one_scan_and_cross_boundary_on_later_page(self):
        primary = """<html><body>
<time>2026-08-17 21:40</time>
<a href="/news/story/1/1001" title="首頁最新報導">首頁最新報導</a>
</body></html>"""
        page_two = json.dumps({"lists": [{
            "titleLink": "/news/story/1/1002", "title": "第二頁報導",
            "time": {"date": "2026-08-17 20:30"},
        }]}, ensure_ascii=False)
        page_three = json.dumps({"lists": [
            {
                "titleLink": "/news/story/1/1003", "title": "第三頁仍在窗內",
                "time": {"date": "2026-08-16 22:30"},
            },
            {
                "titleLink": "/news/story/1/1004", "title": "跨過時間邊界",
                "time": {"date": "2026-08-16 21:30"},
            },
        ]}, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def snapshot(name, body, page_index, request_url, content_type):
                path = root / name
                raw = body.encode("utf-8")
                path.write_bytes(raw)
                return {
                    "page_index": page_index, "request_url": request_url,
                    "http_status": 200, "content_type": content_type,
                    "bytes": len(raw), "snapshot_path": str(path),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }

            first = snapshot(
                "primary.html", primary, 1, "https://udn.com/news/breaknews/1",
                "text/html; charset=utf-8",
            )
            route = {
                "source_id": "udn", "route": "html_direct", "route_ready": True,
                **{key: value for key, value in first.items() if key != "page_index"},
                "page_snapshots": [
                    snapshot("page-2.json", page_two, 2, "https://udn.com/api/more?page=2", "application/json; charset=utf-8"),
                    snapshot("page-3.json", page_three, 3, "https://udn.com/api/more?page=3", "application/json; charset=utf-8"),
                ],
            }
            source = {"source_id": "udn", "homepage": "https://udn.com/", "section": "TWN"}

            scan, coverage = MODULE.materialize_source(
                source, route, "2026-08-16T22:00:00+08:00",
                "2026-08-17T22:00:00+08:00", root,
            )

            self.assertEqual(3, len(scan["pages"]))
            self.assertEqual("https://udn.com/api/more?page=2", scan["pages"][0]["next_url"])
            self.assertEqual("https://udn.com/api/more?page=3", scan["pages"][1]["next_url"])
            self.assertIsNone(scan["pages"][2]["next_url"])
            self.assertEqual(
                {"type": "crossed_window_start", "page_index": 3,
                 "witness_url": "https://udn.com/news/story/1/1004"},
                scan["terminal_proof"],
            )
            self.assertEqual(3, coverage["within_window_count"])
            self.assertEqual([], VALIDATOR.validate_scan(scan, coverage, source))

    def test_tvbs_serialized_article_props_are_materialized(self):
        html = """<html><body><astro-island props="{&quot;article&quot;:[0,{&quot;articleId&quot;:[0,4008088],&quot;title&quot;:[0,&quot;重大政策更新&quot;],&quot;articleUrl&quot;:[0,&quot;https://news.tvbs.com.tw/politics/4008088&quot;],&quot;firstParagraph&quot;:[0,&quot;全國政策今日生效。&quot;],&quot;publishedAt&quot;:[0,1786878175]}]}"></astro-island></body></html>"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "route.bin"
            snapshot.write_bytes(html.encode("utf-8"))
            route = {
                "source_id": "tvbs", "route": "html_direct",
                "source_exhaustion_marker": "</html>",
                "request_url": "https://news.tvbs.com.tw/", "http_status": 200,
                "content_type": "text/html; charset=utf-8", "bytes": len(html.encode()),
                "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(html.encode()).hexdigest(), "route_ready": True,
            }
            source = {"source_id": "tvbs", "homepage": "https://news.tvbs.com.tw/", "section": "TWN"}
            scan, coverage = MODULE.materialize_source(
                source, route, "2026-08-15T12:00:00+08:00", "2026-08-16T20:00:00+08:00", root
            )
            self.assertEqual(1, coverage["ranked_count"])
            self.assertEqual("https://news.tvbs.com.tw/politics/4008088", coverage["ranked_items"][0]["url"])
            self.assertEqual([], VALIDATOR.validate_scan(scan, coverage, source))


if __name__ == "__main__":
    unittest.main()
