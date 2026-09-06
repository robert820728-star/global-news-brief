#!/usr/bin/env python3
"""Prepare and finalize run-bound mobile verification artifacts.

This helper never performs web research. It only exposes one selected semantic
event per bounded input file, validates model-produced verification patches, and
assembles the durable verification.json required by the mobile run ledger.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

RUN_ID_RE = re.compile(r"^gnb-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PUBLISHABLE_FINDINGS = {"corroborated", "single_reliable_source", "conflicting"}
ALL_FINDINGS = PUBLISHABLE_FINDINGS | {"insufficient"}
CLAIM_STATUSES = {"supported", "partially_supported", "conflicting", "unverified"}
EVIDENCE_TYPES = {"supports", "partially_supports", "contradicts", "background"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temp = Path(stream.name)
    temp.replace(path)


def selected_events(audit: dict[str, Any], run_id: str) -> dict[str, dict[str, Any]]:
    runs = audit.get("runs")
    if not isinstance(runs, list):
        raise ValueError("candidate audit must contain runs")
    matches = [run for run in runs if isinstance(run, dict) and run.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError("candidate audit must contain exactly one requested run_id")
    candidates = matches[0].get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidate audit run must contain candidates")

    events: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        event_id = candidate.get("selected_event_id")
        if not isinstance(event_id, str) or not event_id:
            continue
        if candidate.get("grade_status") != "validated":
            raise ValueError(f"selected event {event_id} is not validated")
        grade = candidate.get("provisional_grade")
        if grade in {"C-", "D", "E", None}:
            raise ValueError(f"selected event {event_id} is below publication threshold")
        current = events.setdefault(event_id, {
            "event_id": event_id,
            "title": candidate.get("title"),
            "grade": grade,
            "candidate_ids": [],
            "candidate_urls": [],
            "semantic_event_ids": [],
            "event_identity": candidate.get("event_identity"),
            "grade_reason": candidate.get("grade_reason"),
            "evidence_facts": [],
            "grading_evidence": candidate.get("grading_evidence"),
        })
        current["candidate_ids"].append(candidate.get("candidate_id"))
        current["candidate_urls"].extend(candidate.get("candidate_urls") or [])
        if candidate.get("semantic_event_id"):
            current["semantic_event_ids"].append(candidate["semantic_event_id"])
        current["evidence_facts"].extend(candidate.get("evidence_facts") or [])
    for event in events.values():
        event["candidate_ids"] = list(dict.fromkeys(event["candidate_ids"]))
        event["candidate_urls"] = list(dict.fromkeys(event["candidate_urls"]))
        event["semantic_event_ids"] = list(dict.fromkeys(event["semantic_event_ids"]))
        fact_by_id = {}
        for fact in event["evidence_facts"]:
            if isinstance(fact, dict) and isinstance(fact.get("fact_id"), str):
                fact_by_id[fact["fact_id"]] = fact
        event["evidence_facts"] = list(fact_by_id.values())
    return events


def prepare(
    audit_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    main_sha: str,
    window_start: str,
    window_end: str,
    timezone_name: str,
) -> dict[str, Any]:
    if not RUN_ID_RE.fullmatch(run_id) or not SHA_RE.fullmatch(main_sha):
        raise ValueError("invalid run identity")
    events = selected_events(load(audit_path), run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("event-*.json"):
        stale.unlink()
    files = []
    for index, event_id in enumerate(sorted(events), 1):
        path = output_dir / f"event-{index:03d}.json"
        atomic_write(path, {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "main_sha": main_sha,
            "window": {"start": window_start, "end": window_end, "timezone": timezone_name},
            "event": events[event_id],
        })
        files.append(path.name)
    manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "main_sha": main_sha,
        "window": {"start": window_start, "end": window_end, "timezone": timezone_name},
        "selected_event_count": len(events),
        "event_ids": sorted(events),
        "input_files": files,
    }
    atomic_write(output_dir / "manifest.json", manifest)
    return manifest


def verification_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "status", "finding", "search_performed", "independent_source_count",
        "sources", "claims", "uncertainties", "source_limit_note", "positions",
        "reader_wording", "verified_at",
    }
    missing = sorted(required - set(value))
    if missing:
        return ["missing verification fields: " + ", ".join(missing)]
    status = value.get("status")
    finding = value.get("finding")
    if finding not in ALL_FINDINGS:
        errors.append("finding must be a terminal verification finding")
    if finding == "insufficient" and status != "failed":
        errors.append("insufficient finding must have status=failed")
    if finding in PUBLISHABLE_FINDINGS and status != "completed":
        errors.append("publishable verification finding must have status=completed")
    if value.get("search_performed") is not True:
        errors.append("terminal verification requires search_performed=true")
    count = value.get("independent_source_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        errors.append("independent_source_count must be a non-negative integer")
    sources = value.get("sources")
    claims = value.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list) or not claims:
        errors.append("sources must be an array and claims must be a non-empty array")
        return errors
    source_ids: set[str] = set()
    independence_groups: set[str] = set()
    evidence_types: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            errors.append("every verification source must be an object")
            continue
        for field in (
            "source_id", "name", "url", "role", "producer", "independence_group",
            "published_at", "accessed_at", "evidence_type", "claim_ids", "limitations",
        ):
            if field not in source:
                errors.append(f"verification source missing {field}")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            errors.append("source_id must be unique non-empty strings")
        else:
            source_ids.add(source_id)
        group = source.get("independence_group")
        if isinstance(group, str) and group:
            independence_groups.add(group)
        evidence_type = source.get("evidence_type")
        if evidence_type not in EVIDENCE_TYPES:
            errors.append("invalid evidence_type")
        else:
            evidence_types.add(evidence_type)
        if not isinstance(source.get("claim_ids"), list):
            errors.append("source.claim_ids must be an array")
        if not isinstance(source.get("limitations"), list):
            errors.append("source.limitations must be an array")
    if isinstance(count, int) and count > len(independence_groups):
        errors.append("independent_source_count exceeds distinct independence groups")
    if finding == "corroborated" and len(independence_groups) < 2:
        errors.append("corroborated finding requires at least two independence groups")
    if finding == "conflicting" and not ({"supports", "contradicts"} <= evidence_types):
        errors.append("conflicting finding requires supporting and contradicting evidence")

    claim_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            errors.append("every claim must be an object")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id or claim_id in claim_ids:
            errors.append("claim_id must be unique non-empty strings")
        else:
            claim_ids.add(claim_id)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            errors.append("claim.text must be non-empty")
        if claim.get("status") not in CLAIM_STATUSES:
            errors.append("invalid claim status")
        refs = claim.get("source_ids")
        if not isinstance(refs, list) or any(ref not in source_ids for ref in refs):
            errors.append("claim.source_ids must reference known verification sources")
    for source in sources:
        if isinstance(source, dict) and isinstance(source.get("claim_ids"), list):
            if any(claim_id not in claim_ids for claim_id in source["claim_ids"]):
                errors.append("source.claim_ids must reference known claims")
    if status in {"completed", "failed"} and not isinstance(value.get("verified_at"), str):
        errors.append("terminal verification requires verified_at")
    if not isinstance(value.get("uncertainties"), list) or not isinstance(value.get("positions"), list):
        errors.append("uncertainties and positions must be arrays")
    if not isinstance(value.get("reader_wording"), str):
        errors.append("reader_wording must be a string")
    return errors


def finalize(input_manifest_path: Path, patch_dir: Path, output: Path) -> dict[str, Any]:
    manifest = load(input_manifest_path)
    expected_ids = manifest.get("event_ids")
    if not isinstance(expected_ids, list) or len(expected_ids) != len(set(expected_ids)):
        raise ValueError("verification input manifest has invalid event_ids")
    patches: dict[str, dict[str, Any]] = {}
    for path in sorted(patch_dir.glob("*.json")):
        value = load(path)
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain an object")
        for field in ("run_id", "main_sha", "window"):
            if value.get(field) != manifest.get(field):
                raise ValueError(f"{path} changed durable {field}")
        event_id = value.get("event_id")
        verification = value.get("verification")
        if event_id not in expected_ids or event_id in patches:
            raise ValueError(f"{path} has unknown or duplicate event_id")
        if not isinstance(verification, dict):
            raise ValueError(f"{path}.verification must be an object")
        errors = verification_errors(verification)
        if errors:
            raise ValueError(f"{path}: " + "; ".join(errors))
        patches[event_id] = verification
    missing = sorted(set(expected_ids) - set(patches))
    if missing:
        raise ValueError("verification patches are incomplete: " + ", ".join(missing))
    result = {
        "schema_version": "1.0.0",
        "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"],
        "window": manifest["window"],
        "selected_event_count": len(expected_ids),
        "events": [
            {"event_id": event_id, "verification": patches[event_id]}
            for event_id in expected_ids
        ],
        "publishable_event_count": sum(
            patches[event_id]["finding"] in PUBLISHABLE_FINDINGS for event_id in expected_ids
        ),
        "failed_event_ids": [
            event_id for event_id in expected_ids if patches[event_id]["finding"] == "insufficient"
        ],
        "complete": True,
    }
    atomic_write(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--candidate-audit", required=True, type=Path)
    prepare_parser.add_argument("--output-dir", required=True, type=Path)
    prepare_parser.add_argument("--run-id", required=True)
    prepare_parser.add_argument("--main-sha", required=True)
    prepare_parser.add_argument("--window-start", required=True)
    prepare_parser.add_argument("--window-end", required=True)
    prepare_parser.add_argument("--timezone", required=True)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--input-manifest", required=True, type=Path)
    finalize_parser.add_argument("--patch-dir", required=True, type=Path)
    finalize_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.cmd == "prepare":
        result = prepare(
            args.candidate_audit,
            args.output_dir,
            run_id=args.run_id,
            main_sha=args.main_sha,
            window_start=args.window_start,
            window_end=args.window_end,
            timezone_name=args.timezone,
        )
    else:
        result = finalize(args.input_manifest, args.patch_dir, args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
