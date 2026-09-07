import json
import tempfile
import unittest
from pathlib import Path

from scripts import materialize_mobile_map_decisions as maps


RUN_ID = "gnb-20260907T010203Z-a1b2c3d4"
MAIN_SHA = "a" * 40
WINDOW = {
    "start": "2026-09-06T01:02:03+00:00",
    "end": "2026-09-07T01:02:03+00:00",
    "timezone": "Asia/Shanghai",
}


def audit_fixture():
    return {
        "runs": [{"run_id": RUN_ID, "candidates": [{
            "candidate_id": "c1", "title": "跨境洪水持續擴散", "decision": "selected",
            "selected_event_id": "GLB-01", "grade_status": "validated",
            "provisional_grade": "C", "category": "disaster",
            "impact_scope": "跨境流域", "grade_reason": "洪水影響多國流域",
        }]}],
    }


def verification_fixture():
    return {
        "run_id": RUN_ID, "main_sha": MAIN_SHA, "window": WINDOW,
        "events": [{"event_id": "GLB-01", "verification": {
            "status": "completed", "finding": "corroborated", "claims": [
                {"claim_id": "c1", "text": "洪水跨境擴散", "status": "supported", "source_ids": ["s1"]}
            ],
        }}],
    }


class MobileMapDecisionTransportTests(unittest.TestCase):
    def test_prepare_emits_every_selected_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "audit.json").write_text(json.dumps(audit_fixture()), encoding="utf-8")
            (root / "verification.json").write_text(json.dumps(verification_fixture()), encoding="utf-8")
            result = maps.prepare(root / "audit.json", root / "verification.json", root / "inputs")
            self.assertEqual(["GLB-01"], result["event_ids"])
            self.assertTrue((root / "inputs/event-001.json").exists())

    def test_finalize_requires_exact_event_set_and_rejects_weak_spatial_omission(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "audit.json").write_text(json.dumps(audit_fixture()), encoding="utf-8")
            (root / "verification.json").write_text(json.dumps(verification_fixture()), encoding="utf-8")
            maps.prepare(root / "audit.json", root / "verification.json", root / "inputs")
            patches = root / "patches"
            patches.mkdir()
            patch = {
                "run_id": RUN_ID, "main_sha": MAIN_SHA, "window": WINDOW,
                "event_id": "GLB-01",
                "map": {"required": False, "claim_critical": False, "status": "not_required", "rationale": "不需要地圖"},
            }
            (patches / "GLB-01.json").write_text(json.dumps(patch), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "疑似漏判"):
                maps.finalize(root / "inputs/manifest.json", patches, root / "map-decisions.json")

    def test_finalize_accepts_required_ready_map(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "audit.json").write_text(json.dumps(audit_fixture()), encoding="utf-8")
            (root / "verification.json").write_text(json.dumps(verification_fixture()), encoding="utf-8")
            maps.prepare(root / "audit.json", root / "verification.json", root / "inputs")
            patches = root / "patches"
            patches.mkdir()
            patch = {
                "run_id": RUN_ID, "main_sha": MAIN_SHA, "window": WINDOW,
                "event_id": "GLB-01",
                "map": {"required": True, "claim_critical": False, "status": "ready", "rationale": "跨境洪水範圍增加理解", "assets": []},
            }
            (patches / "GLB-01.json").write_text(json.dumps(patch), encoding="utf-8")
            result = maps.finalize(root / "inputs/manifest.json", patches, root / "map-decisions.json")
            self.assertTrue(result["complete"])
            self.assertEqual(1, result["required_map_count"])


if __name__ == "__main__":
    unittest.main()
