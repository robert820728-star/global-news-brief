#!/usr/bin/env python3
"""Verify the generated bootstrap capsule against the current checkout."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BUILD = load_module(ROOT / "scripts/build_bootstrap_capsule.py", "build_bootstrap_capsule")
LOADER = load_module(ROOT / "bootstrap/bootstrap_loader.py", "bootstrap_loader")


def verify(root: Path = ROOT, manifest_path: Path | None = None) -> list[str]:
    root = root.resolve()
    manifest_path = (manifest_path or (root / "bootstrap/capsule-manifest.json")).resolve()
    errors: list[str] = []
    try:
        manifest = LOADER.load_manifest(manifest_path)
    except Exception as error:
        return [f"manifest invalid: {error}"]

    current_records = BUILD.runtime_records(root)
    current = {item["path"]: item for item in current_records}
    recorded = {item["path"]: item for item in manifest.get("runtime_files", [])}
    if set(current) != set(recorded):
        missing = sorted(set(current) - set(recorded))
        stale = sorted(set(recorded) - set(current))
        if missing:
            errors.append("manifest missing runtime paths: " + ", ".join(missing))
        if stale:
            errors.append("manifest contains stale runtime paths: " + ", ".join(stale))

    for rel in sorted(set(current) & set(recorded)):
        if current[rel] != recorded[rel]:
            errors.append(f"runtime record mismatch: {rel}")
    if BUILD.runtime_fingerprint(current_records) != manifest.get("runtime_fingerprint"):
        errors.append("runtime_fingerprint mismatch")

    try:
        payload = LOADER.verify_chunks(manifest, manifest_path.parent)
        with tempfile.TemporaryDirectory() as directory:
            LOADER.extract_verified(payload, manifest, Path(directory))
    except Exception as error:
        errors.append(f"capsule payload invalid: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--manifest")
    args = parser.parse_args()
    errors = verify(Path(args.root), Path(args.manifest) if args.manifest else None)
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"status": "completed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
