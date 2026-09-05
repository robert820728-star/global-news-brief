import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "materialize_source_row_admissions",
    ROOT / "scripts" / "materialize_source_row_admissions.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def candidate(index: int) -> dict:
    return {
        "row_id": f"row-{index:024x}",
        "candidate_id": f"candidate-{index % 17:04d}",
        "provisional_group_id": f"group-{index % 17:04d}",
        "source_id": "cna" if index % 2 else "chinanews",
        "section": "TWN" if index % 2 else "CHN",
        "url": f"https://example.test/article/{index}",
        "canonical_url": f"https://example.test/article/{index}",
        "published_at": "2026-09-04T08:00:00+08:00",
        "listing_timestamp_evidence": "2026-09-04 08:00",
    }


def gate_for(rows: list[dict]) -> dict:
    return {
        "schema_version": "1.0.0",
        "input_article_row_count": len(rows),
        "decisions": [{
            "row_id": row["row_id"],
            "candidate_id": row["candidate_id"],
            "source_id": row["source_id"],
            "canonical_url": row["canonical_url"],
            "route": "content_hydration",
            "reasons": ["fixture"],
            "matched_discovery_signals": {},
        } for row in rows],
    }


def ready_evidence(row: dict) -> dict:
    return {
        "row_id": row["row_id"],
        "article_body_published_at": "2026-09-04T08:00:00+08:00",
        "article_body_timestamp_evidence": "更新時間：2026/09/04 08:00",
        "article_body_evidence_url": row["canonical_url"],
        "content_sha256": "a" * 64,
        "admission_status": "content_ready",
        "model_evidence": {
            "review_status": "pending_semantic_review",
            "reason": "Article body and authoritative timestamp were persisted.",
            "evidence_refs": [row["canonical_url"]],
        },
    }


class SourceRowAdmissionLedgerTests(unittest.TestCase):
    def test_builds_lossless_132_row_admission_universe(self):
        rows = [candidate(index) for index in range(132)]
        ledger = MODULE.build(
            {
                "schema_version": "1.0.0",
                "window_start": "2026-09-03T09:00:00+08:00",
                "window_end": "2026-09-04T09:00:00+08:00",
                "items": rows,
            },
            gate_for(rows),
            {"schema_version": "1.0.0", "rows": [ready_evidence(row) for row in rows]},
            run_id="run-132",
        )
        self.assertEqual(132, ledger["source_row_count"])
        self.assertEqual(132, ledger["admitted_row_count"])
        self.assertEqual(132, ledger["content_ready_row_count"])
        self.assertEqual(0, ledger["outside_window_row_count"])
        self.assertEqual(0, ledger["unresolved_exhausted_row_count"])
        self.assertEqual([], MODULE.validate(ledger))

    def test_outside_window_body_timestamp_is_conserved_without_fabrication(self):
        row = candidate(1)
        evidence = ready_evidence(row)
        evidence.update({
            "article_body_published_at": "2026-09-02T08:00:00+08:00",
            "admission_status": "outside_window",
            "model_evidence": {
                "review_status": "outside_window",
                "reason": "Article body proves the listing lead is outside the run window.",
                "evidence_refs": [row["canonical_url"]],
            },
        })
        ledger = MODULE.build(
            {
                "schema_version": "1.0.0",
                "window_start": "2026-09-03T09:00:00+08:00",
                "window_end": "2026-09-04T09:00:00+08:00",
                "items": [row],
            },
            gate_for([row]),
            {"schema_version": "1.0.0", "rows": [evidence]},
            run_id="run-outside",
        )
        self.assertEqual("outside_window", ledger["rows"][0]["admission_status"])
        self.assertEqual(1, ledger["outside_window_row_count"])
        self.assertEqual([], MODULE.validate(ledger))

    def test_unresolved_exhausted_can_preserve_failed_fetch_without_fake_timestamp_or_hash(self):
        row = candidate(1)
        evidence = {
            "row_id": row["row_id"],
            "article_body_published_at": None,
            "article_body_timestamp_evidence": None,
            "article_body_evidence_url": row["canonical_url"],
            "content_sha256": None,
            "admission_status": "unresolved_exhausted",
            "model_evidence": {
                "review_status": "unresolved_exhausted",
                "reason": "Original and bounded recovery paths were exhausted.",
                "evidence_refs": [row["canonical_url"]],
            },
            "hydration_attempts": [{"url": row["canonical_url"], "status": "failed"}],
        }
        ledger = MODULE.build(
            {
                "schema_version": "1.0.0",
                "window_start": "2026-09-03T09:00:00+08:00",
                "window_end": "2026-09-04T09:00:00+08:00",
                "items": [row],
            },
            gate_for([row]),
            {"schema_version": "1.0.0", "rows": [evidence]},
            run_id="run-exhausted",
        )
        self.assertIsNone(ledger["rows"][0]["article_body_published_at"])
        self.assertIsNone(ledger["rows"][0]["content_sha256"])
        self.assertEqual(1, ledger["unresolved_exhausted_row_count"])
        self.assertEqual([], MODULE.validate(ledger))

    def test_missing_article_evidence_row_fails_closed(self):
        row = candidate(1)
        with self.assertRaisesRegex(ValueError, "article evidence.*exactly"):
            MODULE.build(
                {
                    "schema_version": "1.0.0",
                    "window_start": "2026-09-03T09:00:00+08:00",
                    "window_end": "2026-09-04T09:00:00+08:00",
                    "items": [row],
                },
                gate_for([row]),
                {"schema_version": "1.0.0", "rows": []},
                run_id="run-missing",
            )

    def test_duplicate_article_evidence_row_id_fails_closed(self):
        row = candidate(1)
        with self.assertRaisesRegex(ValueError, "article evidence row_id.*unique"):
            MODULE.build(
                {
                    "schema_version": "1.0.0",
                    "window_start": "2026-09-03T09:00:00+08:00",
                    "window_end": "2026-09-04T09:00:00+08:00",
                    "items": [row],
                },
                gate_for([row]),
                {"schema_version": "1.0.0", "rows": [ready_evidence(row), ready_evidence(row)]},
                run_id="run-duplicate",
            )


if __name__ == "__main__":
    unittest.main()
