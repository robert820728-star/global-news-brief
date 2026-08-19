#!/usr/bin/env python3
"""Apply one stage-owned event-field patch without jq or shell interpolation."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


STAGE_FIELDS = {
    "verify-news-events": "verification",
}


def load_object(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def apply_stage_patch(
    manifest: dict[str, Any], patch: dict[str, Any], stage: str
) -> dict[str, Any]:
    owned_field = STAGE_FIELDS.get(stage)
    if owned_field is None:
        raise ValueError(f"unsupported stage: {stage}")
    if patch.get("stage") != stage:
        raise ValueError(f"patch stage must be {stage}")

    manifest_events = manifest.get("events")
    patch_events = patch.get("events")
    if not isinstance(manifest_events, list) or not isinstance(patch_events, list):
        raise ValueError("manifest.events and patch.events must be arrays")

    by_id: dict[str, dict[str, Any]] = {}
    for item in manifest_events:
        if not isinstance(item, dict) or not isinstance(item.get("event_id"), str):
            raise ValueError("every manifest event must have a string event_id")
        event_id = item["event_id"]
        if event_id in by_id:
            raise ValueError(f"duplicate manifest event_id: {event_id}")
        by_id[event_id] = item

    seen: set[str] = set()
    for item in patch_events:
        if not isinstance(item, dict):
            raise ValueError("every patch event must be an object")
        if set(item) != {"event_id", owned_field}:
            raise ValueError(
                f"patch events may contain only event_id and {owned_field}"
            )
        event_id = item.get("event_id")
        if not isinstance(event_id, str) or event_id not in by_id:
            raise ValueError(f"unknown patch event_id: {event_id}")
        if event_id in seen:
            raise ValueError(f"duplicate patch event_id: {event_id}")
        if not isinstance(item.get(owned_field), dict):
            raise ValueError(f"{event_id}.{owned_field} must be an object")
        seen.add(event_id)
        by_id[event_id][owned_field] = item[owned_field]

    return manifest


def atomic_write_json(path: str | Path, value: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_FIELDS))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = apply_stage_patch(
        load_object(args.manifest), load_object(args.patch), args.stage
    )
    atomic_write_json(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
