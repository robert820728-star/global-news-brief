import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "fetch_source_routes", ROOT / "scripts" / "fetch_source_routes.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FetchSourceRoutesTests(unittest.TestCase):
    def test_dated_route_keeps_two_successful_days_when_local_today_is_missing(self):
        requested_days = []
        today = datetime.now().astimezone().date()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                day = self.path.rsplit("/", 1)[-1]
                requested_days.append(day)
                if day == today.strftime("%Y%m%d"):
                    body = b"not published"
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                else:
                    body = (
                        "<?xml version='1.0'?><urlset>"
                        f"<url><loc>http://example.test/news/{day}</loc>"
                        f"<lastmod>{day[:4]}-{day[4:6]}-{day[6:]}T12:00:00+00:00</lastmod>"
                        "</url></urlset>"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/xml")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                port = server.server_address[1]
                config = root / "routes.json"
                config.write_text(json.dumps({"routes": [{
                    "source_id": "dated",
                    "route": "structured_direct",
                    "request_url_template": f"http://127.0.0.1:{port}/sitemap/{{yyyyMMdd}}",
                    "snapshot_name": "dated.xml",
                    "date_offsets_days": [0, -1, -2],
                    "minimum_ready_variants": 2,
                }]}), encoding="utf-8")

                coverage = MODULE.fetch_routes(config, root / "out", 5)

                result = coverage["results"][0]
                self.assertTrue(result["route_ready"])
                self.assertEqual(2, result["date_variant_ready_count"])
                self.assertEqual(1, len(result["page_snapshots"]))
                self.assertEqual(3, len(result["date_variant_attempts"]))
                self.assertEqual(
                    [
                        today.strftime("%Y%m%d"),
                        today.strftime("%Y%m%d"),
                        (today + timedelta(days=-1)).strftime("%Y%m%d"),
                        (today + timedelta(days=-2)).strftime("%Y%m%d"),
                    ],
                    requested_days,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_config_uses_small_discovery_set_instead_of_fifteen_mandatory_routes(self):
        config = json.loads((ROOT / "source-route-config.json").read_text(encoding="utf-8"))
        self.assertEqual(1, config["minimum_ready_routes"])
        self.assertEqual(
            ["gdelt", "cna", "chinanews"],
            [item["source_id"] for item in config["routes"]],
        )
        gdelt = config["routes"][0]
        self.assertEqual("aggregate_api", gdelt["route"])
        self.assertIn("api.gdeltproject.org/api/v2/doc/doc", gdelt["request_url_template"])

    def test_configured_json_pagination_stops_after_crossing_window_start(self):
        requested_pages = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/primary":
                    body = b"<html><body>primary</body></html>"
                    content_type = "text/html; charset=utf-8"
                else:
                    page = int(self.path.split("page=", 1)[1])
                    requested_pages.append(page)
                    dates = {
                        2: ["2026-08-17 20:00", "2026-08-17 19:00"],
                        3: ["2026-08-17 18:00", "2026-08-16 21:30"],
                        4: ["2026-08-16 20:00"],
                    }[page]
                    body = json.dumps({
                        "lists": [
                            {
                                "titleLink": f"/news/story/1/{page}{index}",
                                "title": f"page {page} item {index}",
                                "time": {"date": value},
                            }
                            for index, value in enumerate(dates)
                        ]
                    }).encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                port = server.server_address[1]
                config = root / "routes.json"
                config.write_text(json.dumps({"routes": [{
                    "source_id": "udn",
                    "route": "html_direct",
                    "request_url_template": f"http://127.0.0.1:{port}/primary",
                    "snapshot_name": "udn.route-probe.bin",
                    "pagination": {
                        "request_url_template": f"http://127.0.0.1:{port}/api/more?page={{page}}",
                        "start_page": 2,
                        "max_pages": 5,
                        "items_path": ["lists"],
                        "published_path": ["time", "date"],
                    },
                }]}), encoding="utf-8")

                coverage = MODULE.fetch_routes(
                    config, root / "out", 5, "2026-08-16T22:00:00+08:00"
                )

                result = coverage["results"][0]
                self.assertTrue(result["route_ready"])
                self.assertEqual([2, 3], requested_pages)
                self.assertEqual([2, 3], [page["page_index"] for page in result["page_snapshots"]])
                self.assertTrue(all(Path(page["snapshot_path"]).is_file() for page in result["page_snapshots"]))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
