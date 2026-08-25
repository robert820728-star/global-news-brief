import json
import tempfile
import threading
import unittest
from unittest import mock
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
    def test_gdelt_export_row_preserves_structured_discovery_signals(self):
        columns = [""] * 61
        columns[7] = "TWN"
        columns[17] = "CHN"
        columns[26] = "190"
        columns[28] = "19"
        columns[29] = "4"
        columns[30] = "-10.0"
        columns[31] = "42"
        columns[32] = "8"
        columns[33] = "11"
        columns[34] = "-3.5"
        columns[53] = "TWN"
        columns[59] = "20260822120000"
        columns[60] = "https://example.test/world/major-event"

        parsed = MODULE.parse_gdelt_export_row(columns)

        self.assertEqual("20260822120000", parsed["seen_date"])
        self.assertEqual("https://example.test/world/major-event", parsed["url"])
        self.assertEqual(
            {
                "actor_country_codes": ["CHN", "TWN"],
                "action_geo_country_code": "TWN",
                "event_code": "190",
                "event_root_code": "19",
                "quad_class": 4,
                "goldstein_scale": -10.0,
                "num_mentions": 42,
                "num_sources": 8,
                "num_articles": 11,
                "avg_tone": -3.5,
            },
            parsed["discovery_signals"],
        )

    def test_gdelt_official_export_is_primary_and_skips_doc_api_when_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "routes.json"
            config.write_text(json.dumps({
                "minimum_ready_routes": 1,
                "routes": [{
                    "source_id": "gdelt", "route": "aggregate_api",
                    "request_url_template": "http://127.0.0.1:1/unavailable",
                    "snapshot_name": "gdelt.json", "max_attempts": 1,
                    "fallback": {
                        "type": "gdelt_export_24h",
                        "request_url_template": "http://official.test/{yyyyMMddHHmm}.zip",
                    },
                }],
            }), encoding="utf-8")
            fallback_result = {
                "source_id": "gdelt", "route": "aggregate_api",
                "request_url": "http://official.test/archive", "http_status": 200,
                "route_ready": True, "acquisition_mode": "gdelt_export_24h",
                "gdelt_live_ready": True, "archive_complete": True,
            }
            with mock.patch.object(
                MODULE, "fetch_gdelt_export_fallback", return_value=fallback_result
            ) as archive, mock.patch.object(
                MODULE, "fetch_date_variants"
            ) as doc_api:
                coverage = MODULE.fetch_routes(
                    config, root / "out", 1,
                    "2026-08-19T03:00:00+00:00", "2026-08-20T03:00:00+00:00",
                )
            archive.assert_called_once()
            doc_api.assert_not_called()
            self.assertTrue(coverage["publication_ready"])
            self.assertEqual("gdelt_export_24h", coverage["gdelt_acquisition_mode"])
            self.assertEqual("ready", coverage["status"])

    def test_partial_gdelt_archive_is_usable_but_never_live_or_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "routes.json"
            config.write_text(json.dumps({
                "minimum_ready_routes": 1,
                "routes": [{
                    "source_id": "gdelt", "route": "aggregate_api",
                    "request_url_template": "http://127.0.0.1:1/unavailable",
                    "snapshot_name": "gdelt.json", "max_attempts": 1,
                    "fallback": {
                        "type": "gdelt_export_24h",
                        "request_url_template": "http://official.test/{yyyyMMddHHmm}.zip",
                    },
                }],
            }), encoding="utf-8")
            fallback_result = {
                "source_id": "gdelt", "route": "aggregate_api",
                "request_url": "http://official.test/archive", "http_status": 200,
                "route_ready": True, "acquisition_mode": "gdelt_export_24h",
                "gdelt_live_ready": True, "archive_complete": False,
                "archive_requested_count": 97, "archive_ready_count": 96,
            }
            with mock.patch.object(
                MODULE, "fetch_gdelt_export_fallback", return_value=fallback_result
            ), mock.patch.object(MODULE, "fetch_date_variants") as doc_api:
                coverage = MODULE.fetch_routes(
                    config, root / "out", 1,
                    "2026-08-19T03:00:00+00:00", "2026-08-20T03:00:00+00:00",
                )
            doc_api.assert_not_called()
            self.assertTrue(coverage["publication_ready"])
            self.assertFalse(coverage["gdelt_live_ready"])
            self.assertEqual("degraded", coverage["status"])
            self.assertFalse(coverage["results"][0]["coverage_complete"])
            self.assertEqual("degraded_partial", coverage["results"][0]["coverage_status"])

    def test_total_gdelt_failure_is_explicit_but_supplement_keeps_publication_running(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"<html>supplement</html>"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
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
                config = root / "routes.json"
                config.write_text(json.dumps({
                    "minimum_ready_routes": 1,
                    "routes": [
                        {
                            "source_id": "gdelt", "route": "aggregate_api",
                            "request_url_template": "http://127.0.0.1:1/unavailable",
                            "snapshot_name": "gdelt.json", "max_attempts": 1,
                        },
                        {
                            "source_id": "cna", "route": "structured_direct",
                            "request_url_template": f"http://127.0.0.1:{server.server_port}/news",
                            "snapshot_name": "cna.html",
                        },
                    ],
                }), encoding="utf-8")
                coverage = MODULE.fetch_routes(config, root / "out", 1)
                self.assertTrue(coverage["publication_ready"])
                self.assertFalse(coverage["gdelt_live_ready"])
                self.assertEqual("unavailable", coverage["gdelt_acquisition_mode"])
                self.assertEqual("degraded", coverage["status"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

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
        self.assertEqual(
            ["gdelt_export_24h", "doc_api_optional", "last_known_good_cache"],
            gdelt["acquisition_order"],
        )
        self.assertEqual(1, gdelt["max_attempts"])
        routes = {item["source_id"]: item for item in config["routes"]}
        self.assertEqual([0, -1], routes["chinanews"]["date_offsets_days"])
        self.assertEqual(2, routes["chinanews"]["minimum_ready_variants"])
        self.assertEqual("POST", routes["cna"]["pagination"]["request_method"])
        self.assertEqual("pageidx", routes["cna"]["pagination"]["page_field"])

    def test_post_pagination_updates_page_index_and_crosses_window_start(self):
        requested_pages = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                request_json = json.loads(self.rfile.read(length).decode("utf-8"))
                page_index = int(request_json["pageidx"])
                requested_pages.append(page_index)
                payloads = {
                    1: {
                        "Items": [{"CreateTime": "2026/08/17 20:00"}],
                        "NextPageIdx": "2",
                    },
                    2: {
                        "Items": [
                            {"CreateTime": "2026/08/17 19:00"},
                            {"CreateTime": "2026/08/16 21:30"},
                        ],
                        "NextPageIdx": "3",
                    },
                }
                body = json.dumps({"ResultData": payloads[page_index]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
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
                config = root / "routes.json"
                config.write_text(json.dumps({"routes": [{
                    "source_id": "cna", "route": "structured_direct",
                    "request_url_template": f"http://127.0.0.1:{server.server_port}/api",
                    "request_method": "POST",
                    "request_json": {"pageidx": 1, "pagesize": 500},
                    "snapshot_name": "cna.json",
                    "pagination": {
                        "request_method": "POST", "page_field": "pageidx",
                        "start_page": 2, "max_pages": 5,
                        "items_path": ["ResultData", "Items"],
                        "published_path": ["CreateTime"],
                        "next_page_path": ["ResultData", "NextPageIdx"],
                    },
                }]}), encoding="utf-8")

                coverage = MODULE.fetch_routes(
                    config, root / "out", 5, "2026-08-16T22:00:00+08:00"
                )

                result = coverage["results"][0]
                self.assertEqual([1, 2], requested_pages)
                self.assertTrue(result["route_ready"])
                self.assertTrue(result["coverage_complete"])
                self.assertEqual("complete", result["coverage_status"])
                self.assertEqual([2], [page["page_index"] for page in result["page_snapshots"]])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

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
                    "source_id": "regional_a",
                    "route": "html_direct",
                    "request_url_template": f"http://127.0.0.1:{port}/primary",
                    "snapshot_name": "regional-a.route-probe.bin",
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
