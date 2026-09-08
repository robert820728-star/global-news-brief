#!/usr/bin/env python3
"""Prepare and finalize run-bound mobile image-evidence artifacts."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any


FALLBACK_FIELDS = (
    "original_source_attempted",
    "official_fallback_attempted",
    "wire_fallback_attempted",
    "reliable_media_fallback_attempted",
)
BOOLEAN_FIELDS = (*FALLBACK_FIELDS, "direct_media_url_attempted", "qualified_image_found", "delivery_attempted")
DELIVERY_RESULTS = {"delivered", "delivery_unavailable", "source_exhausted"}


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
    matches = [item for item in audit.get("runs") or [] if isinstance(item, dict) and item.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError("candidate audit must contain exactly one requested run")
    selected: dict[str, dict[str, Any]] = {}
    for candidate in matches[0].get("candidates") or []:
        if not isinstance(candidate, dict) or candidate.get("decision") != "selected":
            continue
        event_id = candidate.get("selected_event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("selected candidate must have selected_event_id")
        if event_id in selected:
            raise ValueError("selected_event_id must be unique for image evidence")
        selected[event_id] = candidate
    return selected


def _events_by_id(value: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for item in value.get("events") or []:
        if not isinstance(item, dict) or not isinstance(item.get("event_id"), str):
            raise ValueError(f"{label} contains an invalid event")
        event_id = item["event_id"]
        if event_id in events:
            raise ValueError(f"{label} contains duplicate event_id")
        events[event_id] = item
    return events


def prepare(audit_path: Path, verification_path: Path, map_path: Path, output_dir: Path) -> dict[str, Any]:
    audit = load(audit_path)
    verification = load(verification_path)
    maps = load(map_path)
    identity = {field: verification.get(field) for field in ("run_id", "main_sha", "window")}
    if any(maps.get(field) != identity[field] for field in identity):
        raise ValueError("map decisions changed durable run/main/window identity")
    selected = _selected_candidates(audit, identity["run_id"])
    verification_by_id = _events_by_id(verification, "verification")
    maps_by_id = _events_by_id(maps, "map decisions")
    if set(selected) != set(verification_by_id) or set(selected) != set(maps_by_id):
        raise ValueError("selected, verification, and map event sets must match")

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("event-*.json"):
        stale.unlink()
    event_ids = sorted(selected)
    files: list[str] = []
    contexts: dict[str, Any] = {}
    for index, event_id in enumerate(event_ids, 1):
        context = {
            "event_id": event_id,
            "title": selected[event_id].get("title"),
            "verification": verification_by_id[event_id].get("verification"),
            "map": maps_by_id[event_id].get("map"),
        }
        contexts[event_id] = context
        path = output_dir / f"event-{index:03d}.json"
        atomic_write(path, {"schema_version": "1.0.0", **identity, "event": context})
        files.append(path.name)
    manifest = {
        "schema_version": "1.0.0", **identity,
        "selected_event_count": len(event_ids), "event_ids": event_ids,
        "input_files": files, "event_context": contexts,
    }
    atomic_write(output_dir / "manifest.json", manifest)
    return manifest


def evidence_errors(evidence: Any) -> list[str]:
    if not isinstance(evidence, dict):
        return ["image_evidence must be an object"]
    errors: list[str] = []
    for field in BOOLEAN_FIELDS:
        if not isinstance(evidence.get(field), bool):
            errors.append(f"{field} must be boolean")
    result = evidence.get("delivery_result")
    if result not in DELIVERY_RESULTS:
        errors.append("delivery_result is invalid")
        return errors
    if evidence.get("original_source_attempted") is not True:
        errors.append("original source inspection is required")
    if result in {"delivery_unavailable", "source_exhausted"}:
        if evidence.get("direct_media_url_attempted") is not True:
            errors.append("direct media URL attempt is required before exhaustion")
        if not all(evidence.get(field) is True for field in FALLBACK_FIELDS):
            errors.append("four-tier image fallback exhaustion is required")
    if result == "delivered" and not (
        evidence.get("qualified_image_found") is True and evidence.get("delivery_attempted") is True
    ):
        errors.append("delivered requires a qualified image and delivery attempt")
    if result == "delivery_unavailable" and not (
        evidence.get("qualified_image_found") is True and evidence.get("delivery_attempted") is True
    ):
        errors.append("delivery_unavailable requires a qualified image and delivery attempt")
    if result == "source_exhausted" and (
        evidence.get("qualified_image_found") is True or evidence.get("delivery_attempted") is True
    ):
        errors.append("source_exhausted forbids a found image or delivery attempt")
    return errors


def finalize(input_manifest_path: Path, patch_dir: Path, output: Path) -> dict[str, Any]:
    manifest = load(input_manifest_path)
    expected = manifest.get("event_ids")
    if not isinstance(expected, list) or len(expected) != len(set(expected)):
        raise ValueError("image input manifest has invalid event_ids")
    patches: dict[str, dict[str, Any]] = {}
    for path in sorted(patch_dir.glob("*.json")):
        patch = load(path)
        for field in ("run_id", "main_sha", "window"):
            if patch.get(field) != manifest.get(field):
                raise ValueError(f"{path} changed durable {field}")
        event_id = patch.get("event_id")
        if event_id not in expected or event_id in patches:
            raise ValueError(f"{path} has unknown or duplicate event_id")
        evidence = patch.get("image_evidence")
        errors = evidence_errors(evidence)
        if errors:
            raise ValueError("; ".join(errors))
        patches[event_id] = evidence
    missing = sorted(set(expected) - set(patches))
    if missing:
        raise ValueError("image evidence patches are incomplete: " + ", ".join(missing))
    undelivered = [event_id for event_id in expected if patches[event_id]["delivery_result"] == "delivery_unavailable"]
    result = {
        "schema_version": "1.0.0",
        "run_id": manifest["run_id"], "main_sha": manifest["main_sha"], "window": manifest["window"],
        "selected_event_count": len(expected),
        "events": [{"event_id": event_id, **patches[event_id]} for event_id in expected],
        "undelivered_event_ids": undelivered,
        "visible_delivery_complete": not undelivered,
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
    prepare_parser.add_argument("--map-decisions", required=True, type=Path)
    prepare_parser.add_argument("--output-dir", required=True, type=Path)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--input-manifest", required=True, type=Path)
    finalize_parser.add_argument("--patch-dir", required=True, type=Path)
    finalize_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = (
        prepare(args.candidate_audit, args.verification, args.map_decisions, args.output_dir)
        if args.cmd == "prepare"
        else finalize(args.input_manifest, args.patch_dir, args.output)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
