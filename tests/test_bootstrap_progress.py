import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "bootstrap" / "bootstrap_progress.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PROGRESS = load_module(MODULE_PATH, "bootstrap_progress_test")


class BootstrapProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "bootstrap-progress.json"

    def tearDown(self):
        self.temporary.cleanup()

    def test_interruption_after_chunk_40_keeps_valid_running_record(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        for completed in range(1, 41):
            progress = PROGRESS.record_chunk(
                progress,
                f"capsule.part{completed:04d}.txt",
                completed,
                4,
            )
        PROGRESS.atomic_write(self.path, progress)

        loaded = PROGRESS.load_progress(self.path)
        self.assertEqual(loaded["schema_version"], "1.0.0")
        self.assertEqual(loaded["chunks_completed"], 40)
        self.assertEqual(loaded["chunks_total"], 44)
        self.assertEqual(loaded["status"], "running")
        self.assertEqual(loaded["current_chunk"], "capsule.part0040.txt")
        self.assertIsNone(loaded["last_error"])

    def test_initial_attempt_plus_three_retries_is_bounded(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        for attempt in range(1, 5):
            progress = PROGRESS.record_attempt(
                progress,
                chunk_name="capsule.part0041.txt",
                block_index=3,
                blocks_total=4,
                attempt=attempt,
                byte_size=1024,
                sha256="b" * 64,
                error="sha mismatch",
            )

        self.assertEqual(len(progress["current_block_attempts"]), 4)
        self.assertEqual(progress["retry_count"], 3)
        self.assertEqual(progress["status"], "failed")
        self.assertEqual(progress["current_chunk"], "capsule.part0041.txt")
        self.assertEqual(progress["current_block"], 3)
        self.assertEqual(progress["last_error"], "sha mismatch")
        with self.assertRaisesRegex(ValueError, "attempt"):
            PROGRESS.record_attempt(
                progress,
                chunk_name="capsule.part0041.txt",
                block_index=3,
                blocks_total=4,
                attempt=5,
                byte_size=0,
                sha256=None,
                error="extra retry",
            )

    def test_successful_attempt_clears_current_error_and_attempt_history(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        progress = PROGRESS.record_attempt(
            progress,
            chunk_name="capsule.part0041.txt",
            block_index=1,
            blocks_total=4,
            attempt=1,
            byte_size=100,
            sha256="b" * 64,
            error="truncated",
        )
        progress = PROGRESS.record_attempt(
            progress,
            chunk_name="capsule.part0041.txt",
            block_index=1,
            blocks_total=4,
            attempt=2,
            byte_size=2056,
            sha256="c" * 64,
            error=None,
        )

        self.assertEqual(progress["status"], "running")
        self.assertIsNone(progress["last_error"])
        self.assertEqual(progress["retry_count"], 1)
        self.assertEqual(len(progress["current_block_attempts"]), 2)

    def test_atomic_write_replaces_existing_valid_json(self):
        first = PROGRESS.new_progress("run-1", "a" * 40, 44)
        PROGRESS.atomic_write(self.path, first)
        second = PROGRESS.record_chunk(first, "capsule.part0001.txt", 1, 4)
        PROGRESS.atomic_write(self.path, second)

        loaded = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["chunks_completed"], 1)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_receipt_reports_pre_checkpoint_failure_boundary(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        for completed in range(1, 41):
            progress = PROGRESS.record_chunk(
                progress,
                f"capsule.part{completed:04d}.txt",
                completed,
                4,
            )
        for attempt in range(1, 5):
            progress = PROGRESS.record_attempt(
                progress,
                chunk_name="capsule.part0041.txt",
                block_index=3,
                blocks_total=4,
                attempt=attempt,
                byte_size=1024,
                sha256="b" * 64,
                error="connector response truncated",
            )

        receipt = PROGRESS.render_receipt(progress)
        self.assertEqual(
            receipt,
            "\n".join(
                (
                    "RUN_RECEIPT",
                    "run_id: run-1",
                    f"main_sha: {'a' * 40}",
                    "last_completed_stage: bootstrap-capsule-retrieval",
                    "bootstrap_chunks: 40/44",
                    "current_chunk: capsule.part0041.txt",
                    "current_block: 3/4",
                    "last_error: connector response truncated",
                    "retry_count: 3",
                    "external_ledger: pending",
                    "canonical_delivery: false",
                )
            )
            + "\n",
        )

    def test_success_finalize_returns_receipt_then_removes_local_progress(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        progress = PROGRESS.set_stage(
            progress,
            stage="canonical-delivery",
            status="completed",
            canonical_delivery=True,
        )
        PROGRESS.atomic_write(self.path, progress)

        receipt = PROGRESS.finalize(
            self.path,
            progress,
            canonical_delivery=True,
            clear=True,
        )
        self.assertIn("canonical_delivery: true", receipt)
        self.assertFalse(self.path.exists())

    def test_failure_progress_cannot_be_cleared(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        PROGRESS.atomic_write(self.path, progress)
        with self.assertRaisesRegex(ValueError, "canonical delivery"):
            PROGRESS.finalize(
                self.path,
                progress,
                canonical_delivery=False,
                clear=True,
            )
        self.assertTrue(self.path.exists())

    def test_chunk_41_grouped_truncation_does_not_change_verified_first_40(self):
        progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
        for completed in range(1, 41):
            progress = PROGRESS.record_chunk(
                progress,
                f"capsule.part{completed:04d}.txt",
                completed,
                4,
            )
        first_raw = ("A" * 256 + "\n") * 8
        second_raw = ("B" * 256 + "\n") * 8
        first = {
            "start_line": 1,
            "end_line": 8,
            "size": len(first_raw.encode("ascii")),
            "sha256": hashlib.sha256(first_raw.encode("ascii")).hexdigest(),
        }
        second = {
            "start_line": 9,
            "end_line": 16,
            "size": len(second_raw.encode("ascii")),
            "sha256": hashlib.sha256(second_raw.encode("ascii")).hexdigest(),
        }

        with self.assertRaisesRegex(ValueError, "grouped fetch"):
            PROGRESS.validate_grouped_fetch(first_raw.encode("ascii"), first, second)
        self.assertEqual(progress["chunks_completed"], 40)
        self.assertEqual(progress["current_chunk"], "capsule.part0040.txt")

    def test_grouped_fetch_splits_and_validates_two_declared_blocks(self):
        first_raw = ("A" * 256 + "\n") * 8
        second_raw = ("B" * 256 + "\n") * 8
        first = {
            "start_line": 1,
            "end_line": 8,
            "size": len(first_raw.encode("ascii")),
            "sha256": hashlib.sha256(first_raw.encode("ascii")).hexdigest(),
        }
        second = {
            "start_line": 9,
            "end_line": 16,
            "size": len(second_raw.encode("ascii")),
            "sha256": hashlib.sha256(second_raw.encode("ascii")).hexdigest(),
        }

        blocks = PROGRESS.validate_grouped_fetch(
            (first_raw + second_raw).encode("ascii"),
            first,
            second,
        )
        self.assertEqual(blocks, [first_raw.encode("ascii"), second_raw.encode("ascii")])


if __name__ == "__main__":
    unittest.main()
