import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "manage_mobile_run_log.py"

RUN_A = "gnb-20260827T173900Z-10000001"
RUN_B = "gnb-20260827T220000Z-10000002"
ADHOC_FOR = "2026-08-28T01:39:00+08:00"
FORMAL_FOR = "2026-08-28T06:00:00+08:00"
ADHOC_END = "2026-08-27T17:39:00Z"
FORMAL_END = "2026-08-27T22:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("manage_mobile_run_log_rc16", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def window(end_utc, start_utc):
    return {"start": start_utc, "end": end_utc, "timezone": "Asia/Taipei"}


class PristineReservationTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, run_id, scheduled_for, updated_at):
        return self.module.prepare_run(
            self.ledger,
            run_id=run_id,
            scheduled_for=scheduled_for,
            updated_at=updated_at,
            execution_mode="mobile-native",
        )

    def test_earlier_adhoc_replaces_pristine_future_reservation_without_previous(self):
        self.prepare(RUN_B, FORMAL_FOR, "2026-08-27T14:05:29Z")
        current = self.prepare(RUN_A, ADHOC_FOR, ADHOC_END)
        self.assertEqual(RUN_A, current["run_id"])
        self.assertEqual(ADHOC_FOR, current["scheduled_for"])
        self.assertFalse((self.ledger / "previous.json").exists())

    def test_earlier_adhoc_cannot_replace_started_future_occurrence(self):
        self.prepare(RUN_B, FORMAL_FOR, "2026-08-27T14:05:29Z")
        self.module.advance_run(
            self.ledger,
            run_id=RUN_B,
            stage="executor-started",
            updated_at=FORMAL_END,
            window=window(FORMAL_END, "2026-08-26T22:00:00Z"),
        )
        with self.assertRaisesRegex(ValueError, "older scheduled occurrence"):
            self.prepare(RUN_A, ADHOC_FOR, ADHOC_END)

    def test_later_formal_occurrence_rotates_running_adhoc_normally(self):
        self.prepare(RUN_A, ADHOC_FOR, "2026-08-27T17:38:00Z")
        self.module.advance_run(
            self.ledger,
            run_id=RUN_A,
            stage="executor-started",
            updated_at=ADHOC_END,
            window=window(ADHOC_END, "2026-08-26T17:39:00Z"),
        )
        current = self.prepare(RUN_B, FORMAL_FOR, FORMAL_END)
        previous = self.module._read_json(self.ledger / "previous.json")
        self.assertEqual(RUN_B, current["run_id"])
        self.assertEqual("interrupted_by_next_run", previous["status"])
        self.assertEqual(RUN_A, previous["run_id"])

    def test_matching_pristine_reservation_resumes_same_run(self):
        original = self.prepare(RUN_B, FORMAL_FOR, "2026-08-27T14:05:29Z")
        resumed = self.prepare(RUN_A, FORMAL_FOR, "2026-08-27T17:39:00Z")
        self.assertEqual(original["run_id"], resumed["run_id"])
        self.assertEqual("schedule-prepared", resumed["current_stage"])
        self.assertFalse((self.ledger / "previous.json").exists())


if __name__ == "__main__":
    unittest.main()
