import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_unique_delivery_gate.py"
SPEC = importlib.util.spec_from_file_location("check_unique_delivery_gate_runtime_test", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeliveryRuntimeRevalidationTests(unittest.TestCase):
    def test_receipt_is_not_authority_and_publish_validators_run_again(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {}
            for name in ("checkpoint", "manifest", "audit", "source_pool"):
                path = root / f"{name}.json"
                path.write_text("{}", encoding="utf-8")
                files[name] = path
            brief = root / "brief.md"
            brief.write_text("brief", encoding="utf-8")
            files["brief"] = brief
            release = root / "release.md"
            release.write_text("release", encoding="utf-8")
            files["release"] = release
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({
                "artifacts": {name: {"path": str(path), "sha256": sha(path)} for name, path in files.items()}
            }), encoding="utf-8")

            main = sys.modules["__main__"]
            old = {}
            helpers = {
                "checkpoint_errors": lambda *args: ["REVALIDATED"],
                "candidate_errors": lambda *args: [],
                "attachment_errors": lambda *args: [],
                "validate_map_decisions": type("M", (), {"validate": staticmethod(lambda *args: [])}),
                "validate_news_brief": type(
                    "B",
                    (),
                    {"validate_canonical_reader": staticmethod(lambda *args: [])},
                ),
            }
            for name, value in helpers.items():
                old[name] = getattr(main, name, None)
                setattr(main, name, value)
            old_argv = sys.argv[:]
            try:
                sys.argv = ["publish_news_brief.py", "--deliver-receipt", str(receipt), "--checkpoint", str(files["checkpoint"])]
                errors = MODULE._runtime_revalidation_errors(ROOT)
            finally:
                sys.argv = old_argv
                for name, value in old.items():
                    if value is None:
                        delattr(main, name)
                    else:
                        setattr(main, name, value)
            self.assertIn("REVALIDATED", errors)


if __name__ == "__main__":
    unittest.main()
