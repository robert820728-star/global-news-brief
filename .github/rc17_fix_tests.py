from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one target, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


replace_once(
    "tests/test_manage_mobile_run_log.py",
    '''        workflow = (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("HEAD:main", workflow)
''',
    '''        self.assertFalse(
            (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").exists()
        )
''',
)

replace_once(
    "tests/test_pipeline_contract.py",
    '            "mobile-native 沿用既有 occurrence ledger",\n',
    '            "mobile-native 在 capability routing 選定後建立或 resume",\n',
)

print("rc17 stale test expectations fixed")
