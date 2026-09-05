import json
import unittest

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
    elif operation == "source_scan":
        value["source_ids"] = ["cna", "chinanews"]
    else:
        value["batch_sequence"] = 1
        value["article_inputs"] = [{
            "row_id": "row-" + "1" * 24,
            "candidate_id": "candidate-1",
            "source_id": "cna",
            "canonical_url": "https://www.cna.com.tw/news/aopl/202609060006.aspx",
            "title": "規範致命自主武器邁出重要一步",
            "listing_published_at": "2026-09-06T04:59:00+08:00",
        }]
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

    def test_article_hydration_is_bounded_to_twenty_rows(self):
        payload = request("article_hydration")
        payload["article_inputs"] *= 21
        for index, row in enumerate(payload["article_inputs"]):
            row = dict(row)
            row["row_id"] = "row-" + f"{index + 1:024x}"
            payload["article_inputs"][index] = row
        with self.assertRaisesRegex(ValueError, "1 to 20"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

    def test_article_hydration_requires_batch_sequence_and_window_bound_listing_time(self):
        payload = request("article_hydration")
        payload.pop("batch_sequence")
        with self.assertRaisesRegex(ValueError, "batch_sequence"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

        payload = request("article_hydration")
        payload["article_inputs"][0]["listing_published_at"] = "2026-09-04T04:59:00+08:00"
        with self.assertRaisesRegex(ValueError, "inside window"):
            validate_request(payload, expected_main_sha=MAIN_SHA)

    def test_article_hydration_accepts_valid_regional_row(self):
        payload = request("article_hydration")
        validated = validate_request(payload, expected_main_sha=MAIN_SHA)
        self.assertEqual("article_hydration", validated["operation"])
        self.assertEqual(1, validated["batch_sequence"])

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
