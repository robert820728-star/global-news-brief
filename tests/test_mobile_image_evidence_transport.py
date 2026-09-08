import json
import tempfile
import unittest
from pathlib import Path

from scripts import materialize_mobile_image_evidence as images


RUN_ID = "gnb-20260908T010203Z-a1b2c3d4"
MAIN_SHA = "a" * 40
WINDOW = {
    "start": "2026-09-07T01:02:03+00:00",
    "end": "2026-09-08T01:02:03+00:00",
    "timezone": "Asia/Shanghai",
}


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def audit_fixture():
    return {
        "runs": [{"run_id": RUN_ID, "candidates": [{
            "candidate_id": "candidate-1",
            "title": "當期事件",
            "decision": "selected",
            "selected_event_id": "GLB-01",
        }]}],
    }


def verification_fixture():
    return {
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "events": [{
            "event_id": "GLB-01",
            "verification": {
                "status": "completed",
                "finding": "corroborated",
                "sources": [{
                    "source_id": "source-1",
                    "url": "https://example.com/current-event",
                }],
            },
        }],
    }


def map_fixture():
    return {
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "events": [{
            "event_id": "GLB-01",
            "map": {
                "required": False,
                "claim_critical": False,
                "status": "not_required",
                "rationale": "事件不需要地圖",
            },
        }],
    }


def delivered_patch():
    return {
        "run_id": RUN_ID,
        "main_sha": MAIN_SHA,
        "window": WINDOW,
        "event_id": "GLB-01",
        "image_evidence": {
            "claim_critical": False,
            "source_page_url": "https://example.com/current-event",
            "detected_image_urls": ["https://example.com/current-event.jpg"],
            "original_source_attempted": True,
            "direct_media_url_attempted": True,
            "official_fallback_attempted": False,
            "wire_fallback_attempted": False,
            "reliable_media_fallback_attempted": False,
            "qualified_image_found": True,
            "delivery_attempted": True,
            "delivery_result": "delivered",
        },
    }


class MobileImageEvidenceTransportTests(unittest.TestCase):
    def prepare(self, root: Path):
        write_json(root / "candidate-audit.json", audit_fixture())
        write_json(root / "verification.json", verification_fixture())
        write_json(root / "map-decisions.json", map_fixture())
        return images.prepare(
            root / "candidate-audit.json",
            root / "verification.json",
            root / "map-decisions.json",
            root / "inputs",
        )

    def test_prepare_emits_every_selected_event_with_verified_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.prepare(root)
            self.assertEqual(["GLB-01"], result["event_ids"])
            event = json.loads((root / "inputs/event-001.json").read_text(encoding="utf-8"))
            self.assertEqual("https://example.com/current-event", event["event"]["verification"]["sources"][0]["url"])

    def test_finalize_persists_exact_event_set_and_delivery_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            write_json(root / "patches/GLB-01.json", delivered_patch())
            result = images.finalize(
                root / "inputs/manifest.json", root / "patches", root / "image-evidence.json"
            )
            self.assertTrue(result["complete"])
            self.assertTrue(result["visible_delivery_complete"])
            self.assertEqual([], result["undelivered_event_ids"])

    def test_finalize_rejects_delivery_unavailable_without_four_tier_exhaustion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            patch = delivered_patch()
            patch["image_evidence"]["delivery_result"] = "delivery_unavailable"
            write_json(root / "patches/GLB-01.json", patch)
            with self.assertRaisesRegex(ValueError, "four-tier"):
                images.finalize(
                    root / "inputs/manifest.json", root / "patches", root / "image-evidence.json"
                )


if __name__ == "__main__":
    unittest.main()
