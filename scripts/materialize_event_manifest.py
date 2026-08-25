#!/usr/bin/env python3
"""Bind validated candidate-audit scores into an existing event manifest."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path


READER_GRADES = {
    "SS", "S+", "S", "S-", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"
}
SCORE_BINDINGS = {
    "scoring_method": "scoring_method",
    "importance_score": "validated_importance_score",
    "provisional_grade": "validated_grade",
    "grade_status": "grade_status",
    "evidence_confidence": "evidence_confidence",
    "confidence_band": "confidence_band",
}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"top-level JSON object required: {path}")
    return value


def bind_validated_scores(audit: dict, manifest: dict) -> dict:
    runs = audit.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("candidate audit must contain a latest run")
    candidates = runs[-1].get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("latest candidate run must contain candidates")
    selected = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if (
            candidate.get("provisional_grade") not in READER_GRADES
            or candidate.get("decision") not in {"selected", "merged"}
        ):
            continue
        event_id = candidate.get("selected_event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("selected candidate must contain selected_event_id")
        if event_id in selected:
            raise ValueError(f"duplicate selected_event_id: {event_id}")
        if candidate.get("grade_status") != "validated":
            raise ValueError(f"{event_id} candidate grade_status must be validated")
        if candidate.get("scoring_method") != "public_value_v2":
            raise ValueError(f"{event_id} candidate scoring_method must be public_value_v2")
        if candidate.get("weighted_score") != candidate.get("importance_score"):
            raise ValueError(f"{event_id} weighted_score must equal importance_score")
        selected[event_id] = candidate

    output = copy.deepcopy(manifest)
    events = output.get("events")
    if not isinstance(events, list):
        raise ValueError("manifest must contain events")
    manifest_by_id = {
        event.get("event_id"): event for event in events if isinstance(event, dict)
    }
    if set(selected) != set(manifest_by_id):
        raise ValueError("candidate and manifest event set mismatch")
    for event_id, candidate in selected.items():
        event = manifest_by_id[event_id]
        for candidate_field, manifest_field in SCORE_BINDINGS.items():
            event[manifest_field] = candidate[candidate_field]
        event["grade"] = candidate["provisional_grade"]
    return output


def atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = bind_validated_scores(
        load_json(Path(args.audit)), load_json(Path(args.manifest))
    )
    atomic_write_json(Path(args.output), output)
    print(json.dumps({"status": "completed", "events": len(output["events"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
