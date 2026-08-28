#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests" / "test_manage_mobile_run_log.py"
self_path = Path(__file__).resolve()
text = path.read_text(encoding="utf-8")
old = '''            "image_evidence_artifact": self.mobile_artifacts()["reader-rendered"][
                "image_evidence_artifact"
            ],
            "gate_assertions_artifact": self.mobile_artifacts()["reader-rendered"][
                "gate_assertions_artifact"
            ],
'''
new = '''            "image_evidence_artifact": self.mobile_artifacts()["reader-rendered"][
                "image_evidence_artifact"
            ],
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected one obsolete reader-stage gate block, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
self_path.unlink()
