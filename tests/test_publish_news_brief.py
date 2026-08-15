import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from test_validate_news_brief import valid_brief, valid_manifest


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_news_brief.py"


def write_valid_audit(root):
    source_pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
    coverage = []
    for item in source_pool["sources"]:
        source_id = item["source_id"]
        ranked_items = [{
            "url": f"https://example.com/{source_id}", "title": source_id,
            "published_at": "2026-08-14T05:00:00+00:00", "importance_score": 80,
            "importance_reason": "具有公共影響",
        }]
        coverage.append({
            "source_id": source_id,
            "status": "completed",
            "within_window_count": 1,
            "ranked_count": 1,
            "ranked_items": ranked_items,
            "selected_for_pool_count": 1,
            "selected_item_urls": [f"https://example.com/{source_id}"],
            "mandatory_overflow_items": [],
            "ranking_completed": True,
            "ranking_method": "public_value_v1",
            "failure_reason": None,
        })
    candidate = {
        "candidate_id": "cand-1", "dedup_key": "test-event", "title": "測試事件",
        "section": "TWN", "provisional_grade": "B", "grade_reason": "具有公共影響",
        "decision": "selected", "reason_code": "selected_threshold_met", "reason": "達到B級",
        "selected_event_id": "TWN-01", "candidate_urls": [url for item in coverage for url in item["selected_item_urls"]],
        "source_ids": [item["source_id"] for item in source_pool["sources"]],
        "source_audit": {"search_performed": True, "reliable_source_count": 1, "independent_group_count": 1, "official_or_primary_found": False, "source_limit_note": "單一來源"},
        "continuity": {"status": "new", "material_changes": [], "unchanged_elements": [], "comparison_note": "首次"},
    }
    audit = {
        "schema_version": "1.1.0", "retention_days": 14,
        "updated_at": "2026-08-14T06:00:00+08:00",
        "runs": [{"run_id": "run-1", "generated_at": "2026-08-14T06:00:00+08:00", "window_start": "2026-08-13T06:00:00+08:00", "window_end": "2026-08-14T06:00:00+08:00", "source_coverage": coverage, "raw_item_count": 10, "deduplicated_candidate_count": 1, "candidates": [candidate]}],
    }
    path = root / "audit.json"
    path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    return path


class PublisherTests(unittest.TestCase):
    def test_publish_requires_existing_attachments_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "map.png"
            image_path = root / "image.png"
            source_check_path = root / "source-check.png"
            professional_check_path = root / "professional-check.png"
            Image.new("RGB", (100, 100), "#f3e6b8").save(map_path)
            Image.new("RGB", (100, 100), "#cccccc").save(image_path)
            Image.new("RGB", (100, 100), "#ffffff").save(source_check_path)
            Image.new("RGB", (100, 100), "#ffffff").save(professional_check_path)
            manifest = valid_manifest()
            manifest["events"][0]["map"]["assets"][0]["path"] = str(map_path)
            manifest["events"][0]["images"]["assets"][0]["path"] = str(image_path)
            manifest["events"][0]["images"]["source_checks"][0]["evidence_path"] = str(source_check_path)
            manifest["events"][0]["images"]["professional_source_checks"][0]["evidence_path"] = str(professional_check_path)
            brief = valid_brief().replace(
                "sandbox:/tmp/map.png", str(map_path)
            ).replace(
                "sandbox:/tmp/image.png", str(image_path)
            )
            manifest_path = root / "manifest.json"
            audit_path = write_valid_audit(root)
            brief_path = root / "brief.md"
            release_dir = root / "release"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            brief_path.write_text(brief, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--manifest",
                    str(manifest_path),
                    "--audit",
                    str(audit_path),
                    "--brief",
                    str(brief_path),
                    "--output-dir",
                    str(release_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((release_dir / "news-brief.md").is_file())
            receipt = json.loads(
                (release_dir / "release-receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["status"], "ready")

    def test_publish_blocks_blue_map_even_when_metadata_claims_canonical_style(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "map.png"
            image_path = root / "image.png"
            source_check_path = root / "source-check.png"
            professional_check_path = root / "professional-check.png"
            Image.new("RGB", (100, 100), "#4d88c7").save(map_path)
            Image.new("RGB", (100, 100), "#cccccc").save(image_path)
            Image.new("RGB", (100, 100), "#ffffff").save(source_check_path)
            Image.new("RGB", (100, 100), "#ffffff").save(professional_check_path)
            manifest = valid_manifest()
            manifest["events"][0]["map"]["assets"][0]["path"] = str(map_path)
            manifest["events"][0]["images"]["assets"][0]["path"] = str(image_path)
            manifest["events"][0]["images"]["source_checks"][0]["evidence_path"] = str(source_check_path)
            manifest["events"][0]["images"]["professional_source_checks"][0]["evidence_path"] = str(professional_check_path)
            brief = valid_brief().replace(
                "sandbox:/tmp/map.png", str(map_path)
            ).replace(
                "sandbox:/tmp/image.png", str(image_path)
            )
            manifest_path = root / "manifest.json"
            audit_path = write_valid_audit(root)
            brief_path = root / "brief.md"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            brief_path.write_text(brief, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--manifest",
                    str(manifest_path),
                    "--audit",
                    str(audit_path),
                    "--brief",
                    str(brief_path),
                    "--output-dir",
                    str(root / "release"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("藍色背景比例過高", result.stderr)
            self.assertFalse((root / "release" / "news-brief.md").exists())

    def test_publish_blocks_missing_attachment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = valid_manifest()
            manifest_path = root / "manifest.json"
            audit_path = write_valid_audit(root)
            brief_path = root / "brief.md"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            brief_path.write_text(valid_brief(), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--manifest",
                    str(manifest_path),
                    "--audit",
                    str(audit_path),
                    "--brief",
                    str(brief_path),
                    "--output-dir",
                    str(root / "release"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("附件不存在或為空", result.stderr)
            self.assertFalse((root / "release" / "news-brief.md").exists())

    def test_publish_blocks_incomplete_source_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_path = write_valid_audit(root)
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["runs"][0]["source_coverage"][0]["status"] = "failed"
            audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(valid_manifest(), ensure_ascii=False), encoding="utf-8")
            brief_path = root / "brief.md"
            brief_path.write_text(valid_brief(), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(PUBLISHER), "--manifest", str(manifest_path),
                "--audit", str(audit_path), "--brief", str(brief_path),
                "--output-dir", str(root / "release")
            ], capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("來源掃描未完成", result.stderr)

    def test_publish_blocks_selected_candidate_missing_from_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_path = write_valid_audit(root)
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            extra = dict(audit["runs"][0]["candidates"][0])
            extra.update({"candidate_id": "cand-2", "dedup_key": "event-2", "title": "漏放事件", "selected_event_id": "GLB-01"})
            audit["runs"][0]["candidates"].append(extra)
            audit["runs"][0]["deduplicated_candidate_count"] = 2
            audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(valid_manifest(), ensure_ascii=False), encoding="utf-8")
            brief_path = root / "brief.md"
            brief_path.write_text(valid_brief(), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(PUBLISHER), "--manifest", str(manifest_path),
                "--audit", str(audit_path), "--brief", str(brief_path),
                "--output-dir", str(root / "release")
            ], capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("入選事件與 manifest 不一致", result.stderr)


if __name__ == "__main__":
    unittest.main()
