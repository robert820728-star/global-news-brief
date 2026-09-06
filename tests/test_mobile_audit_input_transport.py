import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts import hydrate_source_rows as hydration
from scripts import materialize_mobile_audit_input as audit_input


MAIN_SHA = "a" * 40
RUN_ID = "gnb-20260907T000000Z-a1b2c3d4"
WINDOW_START = "2026-09-06T00:00:00+08:00"
WINDOW_END = "2026-09-07T00:00:00+08:00"
URL = "https://www.cna.com.tw/news/aipl/202609060001.aspx"
ROW_ID = "row-" + "1" * 24


class HydrationModelExcerptTests(unittest.TestCase):
    def test_hydration_persists_bounded_model_excerpt_without_script_noise(self):
        source = {
            "items": [{
                "row_id": ROW_ID,
                "candidate_id": "candidate-1",
                "source_id": "cna",
                "canonical_url": URL,
            }]
        }
        body = (
            '<meta property="article:published_time" content="2026-09-06T12:00:00+08:00">'
            '<meta name="description" content="摘要證據">'
            '<script>SECRET_SCRIPT_NOISE</script>'
            '<h1>事件標題</h1><p>第一段正文。</p><p>第二段正文。</p>'
        ).encode("utf-8")
        with patch.object(hydration, "fetch", return_value=(body, URL, "text/html; charset=utf-8")):
            row = hydration.hydrate(
                source,
                [ROW_ID],
                datetime.fromisoformat(WINDOW_START),
                datetime.fromisoformat(WINDOW_END),
            )[0]
        self.assertEqual("content_ready", row["status"])
        self.assertIn("摘要證據", row["model_excerpt"])
        self.assertIn("第一段正文", row["model_excerpt"])
        self.assertNotIn("SECRET_SCRIPT_NOISE", row["model_excerpt"])
        self.assertLessEqual(len(row["model_excerpt"]), hydration.MAX_MODEL_EXCERPT_CHARS)


class MobileAuditInputTests(unittest.TestCase):
    def _write_fixture(self, root: Path, *, with_excerpt: bool = True, count: int = 21):
        source_rows = []
        admission_rows = []
        evidence_dir = root / "content-evidence"
        evidence_dir.mkdir(parents=True)
        hydration_rows = []
        for index in range(count):
            row_id = f"row-{index + 1:024x}"
            candidate_id = f"candidate-{index + 1}"
            url = f"https://www.cna.com.tw/news/aipl/20260906{index + 1:04d}.aspx"
            source_rows.append({
                "row_id": row_id,
                "candidate_id": candidate_id,
                "provisional_group_id": f"group-{index + 1}",
                "source_id": "cna",
                "section": "TWN",
                "title": f"title {index + 1}",
                "summary": f"summary {index + 1}",
                "summary_quality": "title_only",
                "canonical_url": url,
                "published_at": "2026-09-06T12:00:00+08:00",
            })
            admission_rows.append({
                "row_id": row_id,
                "candidate_id": candidate_id,
                "admission_status": "content_ready",
                "failure_evidence": None,
            })
            hydration_rows.append({
                "row_id": row_id,
                "candidate_id": candidate_id,
                "status": "content_ready",
                "article_body_published_at": "2026-09-06T12:00:00+08:00",
                "article_body_evidence_url": url,
                "content_sha256": f"{index + 1:064x}"[-64:],
                "model_excerpt": f"body evidence {index + 1}" if with_excerpt or index else None,
            })
        source = {
            "schema_version": "1.0.0",
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
            "items": source_rows,
        }
        admissions = {
            "schema_version": "1.1.0",
            "run_id": RUN_ID,
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
            "source_row_count": count,
            "admitted_row_count": count,
            "rows": admission_rows,
        }
        (root / "source-candidates.json").write_text(json.dumps(source), encoding="utf-8")
        (root / "source-row-admissions.json").write_text(json.dumps(admissions), encoding="utf-8")
        (evidence_dir / "batch-0001-result.json").write_text(
            json.dumps({"schema_version": "1.1", "rows": hydration_rows}), encoding="utf-8"
        )
        return evidence_dir

    def test_materializer_conserves_rows_and_batches_twenty(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = self._write_fixture(root, count=21)
            manifest = audit_input.build(
                root / "source-candidates.json",
                root / "source-row-admissions.json",
                evidence,
                root / "audit-input",
                main_sha=MAIN_SHA,
                timezone_name="Asia/Shanghai",
            )
            self.assertEqual(21, manifest["source_row_count"])
            self.assertEqual(2, manifest["batch_count"])
            self.assertTrue(manifest["ready_for_model_audit"])
            first = json.loads((root / "audit-input/batch-0001.json").read_text(encoding="utf-8"))
            second = json.loads((root / "audit-input/batch-0002.json").read_text(encoding="utf-8"))
            self.assertEqual(20, first["row_count"])
            self.assertEqual(1, second["row_count"])
            self.assertEqual(21, len(first["rows"]) + len(second["rows"]))

    def test_content_ready_without_excerpt_fails_model_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = self._write_fixture(root, with_excerpt=False, count=1)
            manifest = audit_input.build(
                root / "source-candidates.json",
                root / "source-row-admissions.json",
                evidence,
                root / "audit-input",
                main_sha=MAIN_SHA,
                timezone_name="Asia/Shanghai",
            )
            batch = json.loads((root / "audit-input/batch-0001.json").read_text(encoding="utf-8"))
            self.assertEqual(1, manifest["insufficient_excerpt_count"])
            self.assertFalse(manifest["ready_for_model_audit"])
            self.assertEqual("insufficient_excerpt", batch["rows"][0]["model_input_status"])


if __name__ == "__main__":
    unittest.main()
