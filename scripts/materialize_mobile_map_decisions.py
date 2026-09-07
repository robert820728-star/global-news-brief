#!/usr/bin/env python3
"""Prepare and finalize run-bound mobile map-decision artifacts."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts import validate_map_decisions
except ImportError:  # pragma: no cover - direct CLI execution
    import validate_map_decisions


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def _selected_candidates(audit: dict[str, Any], run_id: str) -> dict[str, dict[str, Any]]:
    runs = audit.get("runs")
    matches = [item for item in runs or [] if isinstance(item, dict) and item.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError("candidate audit must contain exactly one requested run")
    events: dict[str, dict[str, Any]] = {}
    for candidate in matches[0].get("candidates") or []:
        if not isinstance(candidate, dict) or candidate.get("decision") != "selected":
            continue
        event_id = candidate.get("selected_event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("selected candidate must have selected_event_id")
        if event_id in events:
            raise ValueError("selected_event_id must be unique for map decisions")
        events[event_id] = candidate
    return events


def prepare(audit_path: Path, verification_path: Path, output_dir: Path) -> dict[str, Any]:
    audit = load(audit_path)
    verification = load(verification_path)
    run_id = verification.get("run_id")
    main_sha = verification.get("main_sha")
    window = verification.get("window")
    selected = _selected_candidates(audit, run_id)
    verification_by_id = {
        item.get("event_id"): item.get("verification")
        for item in verification.get("events") or [] if isinstance(item, dict)
    }
    if set(selected) != set(verification_by_id):
        raise ValueError("verification event set must equal selected event set")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("event-*.json"):
        stale.unlink()
    event_ids = sorted(selected)
    files: list[str] = []
    event_context: dict[str, Any] = {}
    for index, event_id in enumerate(event_ids, 1):
        candidate = selected[event_id]
        context = {
            "event_id": event_id,
            "title": candidate.get("title"),
            "selection": {
                "category": candidate.get("category"),
                "impact_scope": candidate.get("impact_scope"),
                "reason": candidate.get("grade_reason") or candidate.get("reason"),
            },
            "verification": verification_by_id[event_id],
        }
        event_context[event_id] = context
        path = output_dir / f"event-{index:03d}.json"
        atomic_write(path, {
            "schema_version": "1.0.0", "run_id": run_id, "main_sha": main_sha,
            "window": window, "event": context,
        })
        files.append(path.name)
    manifest = {
        "schema_version": "1.0.0", "run_id": run_id, "main_sha": main_sha,
        "window": window, "selected_event_count": len(event_ids),
        "event_ids": event_ids, "input_files": files, "event_context": event_context,
    }
    atomic_write(output_dir / "manifest.json", manifest)
    return manifest


def finalize(input_manifest_path: Path, patch_dir: Path, output: Path) -> dict[str, Any]:
    manifest = load(input_manifest_path)
    expected = manifest.get("event_ids")
    if not isinstance(expected, list) or len(expected) != len(set(expected)):
        raise ValueError("map input manifest has invalid event_ids")
    patches: dict[str, dict[str, Any]] = {}
    for path in sorted(patch_dir.glob("*.json")):
        patch = load(path)
        for field in ("run_id", "main_sha", "window"):
            if patch.get(field) != manifest.get(field):
                raise ValueError(f"{path} changed durable {field}")
        event_id = patch.get("event_id")
        decision = patch.get("map")
        if event_id not in expected or event_id in patches:
            raise ValueError(f"{path} has unknown or duplicate event_id")
        if not isinstance(decision, dict):
            raise ValueError(f"{path}.map must be an object")
        patches[event_id] = decision
    missing = sorted(set(expected) - set(patches))
    if missing:
        raise ValueError("map patches are incomplete: " + ", ".join(missing))
    projected_events = []
    for event_id in expected:
        context = manifest["event_context"][event_id]
        projected_events.append({**context, "map": patches[event_id]})
    errors = validate_map_decisions.validate({"events": projected_events})
    if errors:
        raise ValueError("; ".join(errors))
    result = {
        "schema_version": "1.0.0", "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"], "window": manifest["window"],
        "selected_event_count": len(expected),
        "events": [{"event_id": event_id, "map": patches[event_id]} for event_id in expected],
        "required_map_count": sum(bool(patches[event_id].get("required")) for event_id in expected),
        "claim_critical_map_count": sum(bool(patches[event_id].get("claim_critical")) for event_id in expected),
        "complete": True,
    }
    atomic_write(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--candidate-audit", required=True, type=Path)
    prepare_parser.add_argument("--verification", required=True, type=Path)
    prepare_parser.add_argument("--output-dir", required=True, type=Path)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--input-manifest", required=True, type=Path)
    finalize_parser.add_argument("--patch-dir", required=True, type=Path)
    finalize_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = (prepare(args.candidate_audit, args.verification, args.output_dir)
              if args.cmd == "prepare" else finalize(args.input_manifest, args.patch_dir, args.output))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
