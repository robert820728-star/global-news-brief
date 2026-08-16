#!/usr/bin/env python3
"""Fail closed when a selection references anything outside the current run pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


GRADE_ORDER = [
    "E", "D", "C-", "C", "C+", "B-", "B", "B+",
    "A-", "A", "A+", "S-", "S", "S+", "SS",
]


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_items(source: Any) -> list[dict[str, Any]]:
    if isinstance(source, dict):
        items = source.get("items")
    else:
        items = source
    if not isinstance(items, list):
        raise ValueError("source candidates must contain an items array")
    return [item for item in items if isinstance(item, dict)]


def _urls(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [url for url in value if isinstance(url, str) and url.strip()]


def _is_c_or_above(grade: Any) -> bool:
    return isinstance(grade, str) and grade in GRADE_ORDER and GRADE_ORDER.index(grade) >= GRADE_ORDER.index("C")


def validate_selection_freshness(selection: Any, source: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(selection, dict):
        return ["selection must be an object"]

    fresh_urls: set[str] = set()
    for item in _source_items(source):
        for key in ("url", "canonical_url"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                fresh_urls.add(value)

    events = selection.get("selected_events")
    if not isinstance(events, list):
        return ["selection.selected_events must be an array"]
    candidates = selection.get("candidates")
    if not isinstance(candidates, list):
        return ["selection.candidates must be an array"]

    event_ids: set[str] = set()
    event_urls: dict[str, set[str]] = {}
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"selected_events[{index}] must be an object")
            continue
        event_id = event.get("event_id")
        label = event_id if isinstance(event_id, str) and event_id else f"selected_events[{index}]"
        if not isinstance(event_id, str) or not event_id:
            errors.append(f"{label} missing event_id")
            continue
        if event_id in event_ids:
            errors.append(f"duplicate event_id: {event_id}")
        event_ids.add(event_id)
        payload = event.get("selection")
        urls = _urls(payload.get("candidate_urls") if isinstance(payload, dict) else None)
        if not urls:
            errors.append(f"{event_id} has no current-run candidate URL")
            continue
        stale = sorted(set(urls) - fresh_urls)
        if stale:
            errors.append(f"{event_id} URL is outside the current fresh pool: {', '.join(stale)}")
        event_urls[event_id] = set(urls)

    mapped_event_ids: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            errors.append(f"candidates[{index}] must be an object")
            continue
        candidate_id = candidate.get("candidate_id") or f"candidates[{index}]"
        urls = _urls(candidate.get("candidate_urls"))
        stale = sorted(set(urls) - fresh_urls)
        if stale:
            errors.append(f"{candidate_id} URL is outside the current fresh pool: {', '.join(stale)}")
        selected_event_id = candidate.get("selected_event_id")
        if _is_c_or_above(candidate.get("provisional_grade")):
            if not isinstance(selected_event_id, str) or not selected_event_id:
                errors.append(f"{candidate_id} is C-or-above but has no selected_event_id")
            elif selected_event_id not in event_ids:
                errors.append(f"{candidate_id} maps to missing event_id: {selected_event_id}")
            else:
                mapped_event_ids.add(selected_event_id)
                if urls and not set(urls).intersection(event_urls.get(selected_event_id, set())):
                    errors.append(
                        f"{candidate_id} does not share a fresh URL with {selected_event_id}"
                    )

    for event_id in sorted(event_ids - mapped_event_ids):
        errors.append(f"{event_id} has no mapped C-or-above current-run candidate")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--source-candidates", required=True)
    args = parser.parse_args(argv)
    try:
        selection = load_json(args.selection)
        source = load_json(args.source_candidates)
        errors = validate_selection_freshness(selection, source)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 1
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(
        f"OK selected_events={len(selection['selected_events'])} "
        f"candidates={len(selection['candidates'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
