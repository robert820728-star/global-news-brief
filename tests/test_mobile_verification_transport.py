import json
import tempfile
import unittest
from pathlib import Path

from scripts import materialize_mobile_verification as verification


RUN_ID = "gnb-20260907T010203Z-a1b2c3d4"
MAIN_SHA = "a" * 40
WINDOW_START = "2026-09-06T01:02:03+00:00"
WINDOW_END = "2026-09-07T01:02:03+00:00"


def audit_fixture():
    return {
        "schema_version": "1.2.0",
        "runs": [{
            "run_id": RUN_ID,
            "candidates": [{
                "candidate_id": "c1",
                "title": "測試事件",
                "provisional_grade": "C",
                "grade_status": "validated",
                "decision": "selected",
                "selected_event_id": "GLB-01",
                "semantic_event_id": "semantic-1",
                "candidate_urls": ["https://example.com/original"],
                "event_identity": {"who_or_what": "測試事件"},
                "grade_reason": "達到 C 級門檻",
                "evidence_facts": [{"fact_id": "F01", "fact": "已發生事實"}],
                "grading_evidence": {"impact_scope_level": "international"},
            }],
        }],
    }


def completed_verification(finding="corroborated"):
    sources = [
        {
            "source_id": "s1", "name": "Source 1", "url": "https://example.com/1",
            "role": "original", "producer": "p1", "independence_group": "g1",
            "published_at": "2026-09-06T02:00:00Z", "accessed_at": "2026-09-07T01:10:00Z",
            "evidence_type": "supports", "claim_ids": ["claim-1"], "limitations": [],
        },
        {
            "source_id": "s2", "name": "Source 2", "url": "https://example.com/2",
            "role": "independent", "producer": "p2", "independence_group": "g2",
            "published_at": "2026-09-06T03:00:00Z", "accessed_at": "2026-09-07T01:11:00Z",
            "evidence_type": "supports", "claim_ids": ["claim-1"], "limitations": [],
        },
    ]
    return {
        "status": "completed",
        "finding": finding,
        "search_performed": True,
        "independent_source_count": 2,
        "sources": sources,
        "claims": [{
            "claim_id": "claim-1", "text": "核心主張", "status": "supported",
            "source_ids": ["s1", "s2"],
        }],
        "uncertainties": [],
        "source_limit_note": None,
        "positions": [],
        "reader_wording": "核心主張獲兩個獨立來源支持。",
        "verified_at": "2026-09-07T01:12:00Z",
    }


class MobileVerificationTransportTests(unittest.TestCase):
    def test_prepare_emits_one_file_per_selected_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audit = root / "audit.json"
            audit.write_text(json.dumps(audit_fixture()), encoding="utf-8")
            manifest = verification.prepare(
                audit, root / "input", run_id=RUN_ID, main_sha=MAIN_SHA,
                window_start=WINDOW_START, window_end=WINDOW_END,
                timezone_name="Asia/Shanghai",
            )
            self.assertEqual(1, manifest["selected_event_count"])
            self.assertEqual(["GLB-01"], manifest["event_ids"])
            item = json.loads((root / "input/event-001.json").read_text(encoding="utf-8"))
            self.assertEqual("GLB-01", item["event"]["event_id"])
            self.assertEqual(["https://example.com/original"], item["event"]["candidate_urls"])

    def test_finalize_requires_every_selected_event_and_preserves_run_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audit = root / "audit.json"
            audit.write_text(json.dumps(audit_fixture()), encoding="utf-8")
            verification.prepare(
                audit, root / "input", run_id=RUN_ID, main_sha=MAIN_SHA,
                window_start=WINDOW_START, window_end=WINDOW_END,
                timezone_name="Asia/Shanghai",
            )
            patch_dir = root / "patches"
            patch_dir.mkdir()
            patch = {
                "run_id": RUN_ID,
                "main_sha": MAIN_SHA,
                "window": {"start": WINDOW_START, "end": WINDOW_END, "timezone": "Asia/Shanghai"},
                "event_id": "GLB-01",
                "verification": completed_verification(),
            }
            (patch_dir / "GLB-01.json").write_text(json.dumps(patch), encoding="utf-8")
            result = verification.finalize(root / "input/manifest.json", patch_dir, root / "verification.json")
            self.assertTrue(result["complete"])
            self.assertEqual(1, result["publishable_event_count"])
            self.assertEqual([], result["failed_event_ids"])
            self.assertEqual(RUN_ID, result["run_id"])

    def test_insufficient_finding_must_fail_verification(self):
        value = completed_verification()
        value["finding"] = "insufficient"
        self.assertIn("insufficient finding must have status=failed", verification.verification_errors(value))
        value["status"] = "failed"
        self.assertNotIn("insufficient finding must have status=failed", verification.verification_errors(value))

    def test_corroborated_requires_two_independence_groups(self):
        value = completed_verification()
        value["sources"][1]["independence_group"] = "g1"
        errors = verification.verification_errors(value)
        self.assertIn("corroborated finding requires at least two independence groups", errors)


if __name__ == "__main__":
    unittest.main()
