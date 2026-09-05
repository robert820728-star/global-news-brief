import json
import tempfile
import unittest
from pathlib import Path

from scripts.remote_acquisition_bridge import (
    extract_request_from_comment,
    validate_request,
)


MAIN_SHA = "a9a8ec2d3340fc123b1aae116b6226d1ece6f86e"
RUN_ID = "gnb-20260905T220000Z-a1b2c3d4"


def request(operation="media_fetch"):
    value = {
        "schema_version": "1.0",
        "operation": operation,
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": {
            "start": "2026-09-05T06:00:00+08:00",
            "end": "2026-09-06T06:00:00+08:00",
        },
    }
    if operation == "media_fetch":
        value["media_inputs"] = [{
            "event_id": "TWN-01",
            "source_page_url": "https://www.cna.com.tw/news/ahel/202609050001.aspx",
            "source_image_url": "https://imgcdn.cna.com.tw/example.jpg",
            "expected_source_sha256": "1" * 64,
        }]
    else:
        value["source_ids"] = ["cna", "chinanews"]
    return value


class RemoteAcquisitionBridgeTests(unittest.TestCase):
    def test_issue_comment_envelope_is_exact_and_main_bound(self):
        payload = request()
        body = "<!-- gnb-remote-acquisition:v1 -->\n```json\n" + json.dumps(payload) + "\n```"
        parsed = extract_request_from_comment(body)
        validated = validate_request(parsed, expected_main_sha=MAIN_SHA)
        self.assertEqual(RUN_ID, validated["run_id"])
        self.assertEqual("media_fetch", validated["operation"])

    def test_stale_main_and_untrusted_output_path_are_rejected(self):
        payload = request("source_scan")
        payload["output_prefix"] = "../main"
        with self.assertRaisesRegex(ValueError, "unknown request keys"):
            validate_request(payload, expected_main_sha=MAIN_SHA)
        payload.pop("output_prefix")
        with self.assertRaisesRegex(ValueError, "main_sha"):
            validate_request(payload, expected_main_sha="2" * 40)

    def test_source_scan_is_limited_to_regional_routes(self):
        payload = request("source_scan")
        payload["source_ids"] = ["gdelt"]
        with self.assertRaisesRegex(ValueError, "regional"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

    def test_media_urls_reject_private_targets_credentials_and_nondefault_ports(self):
        blocked_urls = (
            "https://169.254.169.254/latest/meta-data",
            "https://127.0.0.1/image.jpg",
            "https://user:secret@example.com/image.jpg",
            "https://example.com:8443/image.jpg",
        )
        for blocked_url in blocked_urls:
            with self.subTest(blocked_url=blocked_url):
                payload = request()
                payload["media_inputs"][0]["source_image_url"] = blocked_url
                with self.assertRaisesRegex(ValueError, "public HTTPS"):
                    validate_request(payload, expected_main_sha=MAIN_SHA)

    def test_window_must_be_exactly_twenty_four_hours(self):
        payload = request("source_scan")
        payload["window"]["start"] = "2026-09-05T07:00:00+08:00"
        with self.assertRaisesRegex(ValueError, "24 hours"):
            validate_request(payload, expected_main_sha=MAIN_SHA)


if __name__ == "__main__":
    unittest.main()
