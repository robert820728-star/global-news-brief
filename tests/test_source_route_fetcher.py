import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.fetch_source_routes import fetch_one


ROOT = Path(__file__).resolve().parents[1]
PYTHON_FETCHER = ROOT / "scripts" / "fetch_source_routes.py"
ROUTES = ROOT / "source-route-config.json"


class _Handler(BaseHTTPRequestHandler):
    payload = "<html><body>route probe 測試</body></html>".encode("utf-8")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, _format, *_args):
        return


class _PostHandler(BaseHTTPRequestHandler):
    payload = json.dumps({
        "Result": "Y",
        "ResultData": {"Items": [], "NextPageIdx": ""},
    }, separators=(",", ":")).encode("utf-8")
    received_method = None
    received_json = None

    def do_POST(self):
        type(self).received_method = "POST"
        length = int(self.headers.get("Content-Length", "0"))
        type(self).received_json = json.loads(self.rfile.read(length))
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, _format, *_args):
        return


class _FlakyHandler(BaseHTTPRequestHandler):
    attempts = 0
    payload = b"recovered"

    def do_GET(self):
        type(self).attempts += 1
        if type(self).attempts == 1:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, _format, *_args):
        return


class _RateLimitedThenReadyHandler(BaseHTTPRequestHandler):
    attempts = 0
    payload = b'{"articles":[]}'

    def do_GET(self):
        type(self).attempts += 1
        if type(self).attempts == 1:
            self.send_response(429)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, _format, *_args):
        return


class SourceRouteFetcherTests(unittest.TestCase):
    def test_http_2xx_without_configured_text_exhaustion_marker_is_rejected(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"<html><body>WAF challenge, incomplete document"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = fetch_one(
                    {
                        "source_id": "chinanews",
                        "route": "html_direct",
                        "request_url_template": (
                            f"http://127.0.0.1:{server.server_port}/scroll-news/news1.html"
                        ),
                        "snapshot_name": "chinanews.html",
                        "response_integrity_marker": "</html>",
                        "max_attempts": 1,
                    },
                    root,
                    5,
                )

                self.assertFalse(result["route_ready"])
                self.assertIn("response_integrity_marker", result["error"])
                self.assertNotIn("source_exhaustion_marker", result)
                self.assertIsNone(result["snapshot_path"])
                self.assertFalse((root / "chinanews.html").exists())
        finally:
            server.shutdown()
            server.server_close()

    def test_http_2xx_json_without_configured_exhaustion_path_is_rejected(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"ResultData": {"Items": []}}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = fetch_one(
                    {
                        "source_id": "cna",
                        "route": "structured_direct",
                        "request_url_template": (
                            f"http://127.0.0.1:{server.server_port}/api/WNewsList"
                        ),
                        "snapshot_name": "cna.json",
                        "json_exhaustion_path": ["ResultData", "NextPageIdx"],
                        "max_attempts": 1,
                    },
                    root,
                    5,
                )

                self.assertFalse(result["route_ready"])
                self.assertIn("json_exhaustion_path", result["error"])
                self.assertIsNone(result["snapshot_path"])
                self.assertFalse((root / "cna.json").exists())
        finally:
            server.shutdown()
            server.server_close()

    def test_route_config_covers_every_primary_source(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8-sig"))
        config = json.loads(ROUTES.read_text(encoding="utf-8-sig"))
        self.assertEqual(
            {source["source_id"] for source in pool["discovery_sources"]},
            {route["source_id"] for route in config["routes"]},
        )
        self.assertEqual(3, len(config["routes"]))
        self.assertEqual(1, config["minimum_ready_routes"])
        gdelt = next(route for route in config["routes"] if route["source_id"] == "gdelt")
        self.assertEqual("aggregate_api", gdelt["route"])
        self.assertIn("api.gdeltproject.org/api/v2/doc/doc", gdelt["request_url_template"])
        self.assertIn("format=json", gdelt["request_url_template"])
        self.assertEqual(1, gdelt["max_attempts"])
        self.assertEqual(0, gdelt["retry_interval_seconds"])
        self.assertEqual('"articles"', gdelt["response_integrity_marker"])
        self.assertNotIn("source_exhaustion_marker", gdelt)
        self.assertEqual(
            ["gdelt_export_24h", "doc_api_optional", "last_known_good_cache"],
            gdelt["acquisition_order"],
        )
        self.assertEqual("gdelt_export_24h", gdelt["fallback"]["type"])
        self.assertIn("data.gdeltproject.org/gdeltv2", gdelt["fallback"]["request_url_template"])
        cna = next(route for route in config["routes"] if route["source_id"] == "cna")
        self.assertEqual("structured_direct", cna["route"])
        self.assertEqual("POST", cna["request_method"])
        self.assertEqual(500, cna["request_json"]["pagesize"])
        self.assertEqual(["ResultData", "NextPageIdx"], cna["json_exhaustion_path"])
        chinanews = next(
            route for route in config["routes"] if route["source_id"] == "chinanews"
        )
        self.assertEqual("</html>", chinanews["response_integrity_marker"])
        self.assertNotIn("source_exhaustion_marker", chinanews)

    def test_partial_discovery_success_does_not_fail_entire_fetch(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                route_config = root / "routes.json"
                output_dir = root / "out"
                route_config.write_text(json.dumps({
                    "schema_version": "1.1.0",
                    "minimum_ready_routes": 1,
                    "routes": [
                        {
                            "source_id": "ready", "route": "structured_direct",
                            "request_url_template": f"http://127.0.0.1:{server.server_port}/news",
                            "snapshot_name": "ready.bin",
                        },
                        {
                            "source_id": "failed", "route": "structured_direct",
                            "request_url_template": "http://127.0.0.1:1/unavailable",
                            "snapshot_name": "failed.bin",
                        },
                    ],
                }), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(PYTHON_FETCHER),
                     "--route-config", str(route_config),
                     "--output-dir", str(output_dir), "--timeout-seconds", "1"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                )
                self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
                coverage = json.loads(
                    (output_dir / "source-route-coverage.json").read_text(encoding="utf-8")
                )
                self.assertEqual(1, coverage["route_ready_count"])
                self.assertEqual("degraded", coverage["status"])
        finally:
            server.shutdown()
            server.server_close()

    def test_python_fetcher_persists_exact_snapshot_and_coverage(self):
        self.assertTrue(PYTHON_FETCHER.is_file())
        self._assert_fetcher_contract([sys.executable, str(PYTHON_FETCHER)])

    def test_python_fetcher_supports_canonical_json_post(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _PostHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                route_config = temp_path / "routes.json"
                output_dir = temp_path / "out"
                request_json = {
                    "action": "0", "category": "aall", "pagesize": 500, "pageidx": 1,
                }
                route_config.write_text(json.dumps({
                    "schema_version": "1.0.0",
                    "routes": [{
                        "source_id": "cna",
                        "route": "structured_direct",
                        "request_url_template": f"http://127.0.0.1:{server.server_port}/api/WNewsList",
                        "request_method": "POST",
                        "request_json": request_json,
                        "json_exhaustion_path": ["ResultData", "NextPageIdx"],
                        "snapshot_name": "cna.json",
                    }],
                }), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(PYTHON_FETCHER),
                     "--route-config", str(route_config),
                     "--output-dir", str(output_dir), "--timeout-seconds", "5"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                )
                self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
                self.assertEqual("POST", _PostHandler.received_method)
                self.assertEqual(request_json, _PostHandler.received_json)
                result = json.loads(
                    (output_dir / "source-route-coverage.json").read_text(encoding="utf-8-sig")
                )["results"][0]
                self.assertEqual("POST", result["request_method"])
                self.assertEqual(["ResultData", "NextPageIdx"], result["json_exhaustion_path"])
                self.assertEqual(_PostHandler.payload, Path(result["snapshot_path"]).read_bytes())
        finally:
            server.shutdown()
            server.server_close()

    def test_python_fetcher_retries_only_the_failed_route_once(self):
        _FlakyHandler.attempts = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FlakyHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                route_config = root / "routes.json"
                output_dir = root / "out"
                route_config.write_text(json.dumps({
                    "schema_version": "1.0.0",
                    "routes": [{
                        "source_id": "flaky", "route": "html_direct",
                        "request_url_template": f"http://127.0.0.1:{server.server_port}/news",
                        "snapshot_name": "flaky.bin",
                    }],
                }), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(PYTHON_FETCHER),
                     "--route-config", str(route_config),
                     "--output-dir", str(output_dir), "--timeout-seconds", "5"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                )
                self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
                self.assertEqual(2, _FlakyHandler.attempts)
                result = json.loads(
                    (output_dir / "source-route-coverage.json").read_text(encoding="utf-8-sig")
                )["results"][0]
                self.assertEqual(1, result["retry_count"])
        finally:
            server.shutdown()
            server.server_close()

    def test_python_fetcher_honors_retry_after_before_declaring_gdelt_failure(self):
        _RateLimitedThenReadyHandler.attempts = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), _RateLimitedThenReadyHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                route_config = root / "routes.json"
                output_dir = root / "out"
                route_config.write_text(json.dumps({
                    "minimum_ready_routes": 1,
                    "routes": [{
                        "source_id": "gdelt", "route": "aggregate_api",
                        "request_url_template": f"http://127.0.0.1:{server.server_port}/doc",
                        "snapshot_name": "gdelt.json", "max_attempts": 3,
                    }],
                }), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(PYTHON_FETCHER),
                     "--route-config", str(route_config),
                     "--output-dir", str(output_dir), "--timeout-seconds", "5"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                )
                self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
                self.assertEqual(2, _RateLimitedThenReadyHandler.attempts)
                result = json.loads(
                    (output_dir / "source-route-coverage.json").read_text(encoding="utf-8")
                )["results"][0]
                self.assertEqual(1, result["retry_count"])
                self.assertEqual("doc_api_optional", result["acquisition_mode"])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def _assert_fetcher_contract(self, command):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                route_config = temp_path / "routes.json"
                output_dir = temp_path / "out"
                route_config.write_text(json.dumps({
                    "schema_version": "1.0.0",
                    "routes": [{
                        "source_id": "local",
                        "route": "html_direct",
                        "request_url_template": f"http://127.0.0.1:{server.server_port}/{{yyyy-MM-dd}}/news",
                        "snapshot_name": "local.route-probe.bin",
                    }],
                }), encoding="utf-8")
                arguments = [
                    "--route-config", str(route_config),
                    "--output-dir", str(output_dir),
                    "--timeout-seconds", "5",
                ]
                completed = subprocess.run(
                    command + arguments,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=20,
                )
                self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
                coverage = json.loads((output_dir / "source-route-coverage.json").read_text(encoding="utf-8-sig"))
                self.assertEqual(1, coverage["route_ready_count"])
                result = coverage["results"][0]
                self.assertRegex(result["request_url"], r"/\d{4}-\d{2}-\d{2}/news$")
                snapshot = Path(result["snapshot_path"])
                self.assertEqual(_Handler.payload, snapshot.read_bytes())
                self.assertEqual(hashlib.sha256(_Handler.payload).hexdigest(), result["sha256"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
