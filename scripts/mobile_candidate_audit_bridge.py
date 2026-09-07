#!/usr/bin/env python3
"""Run-bound issue-comment bridge for mobile candidate-audit checkpoints."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scripts import materialize_mobile_candidate_audit as transport
from scripts import materialize_mobile_map_decisions as map_transport
from scripts import materialize_mobile_verification as verification_transport


MARKER = "<!-- gnb-mobile-candidate-audit:v1 -->"
RUN_ID_RE = re.compile(r"^gnb-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
COMMON_KEYS = {"schema_version", "operation", "run_id", "main_sha", "window"}
OPERATION_KEYS = {
    "candidate_audit_review": {"batch_sequence", "rows"},
    "candidate_audit_prepare_scoring": set(),
    "candidate_audit_score": {"batch_sequence", "events"},
    "candidate_audit_finalize": {"generated_at", "section_scopes"},
    "verification_prepare": set(),
    "verification_event": {"event_id", "verification"},
    "verification_finalize": set(),
    "map_prepare": set(),
    "map_event": {"event_id", "map"},
    "map_finalize": set(),
}
MAX_COMMENT_REQUEST_BYTES = 60_000


def write_json(path: Path, value: Any) -> None:
    transport.atomic_write(path, value)


def parse_time(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be an ISO date-time") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a time zone")
    return parsed


def extract_request_from_comment(body: str) -> dict[str, Any]:
    if body.count(MARKER) != 1:
        raise ValueError("candidate-audit marker must appear exactly once")
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", body, flags=re.DOTALL | re.IGNORECASE)
    if len(blocks) != 1:
        raise ValueError("issue comment must contain exactly one fenced JSON request")
    value = json.loads(blocks[0])
    if not isinstance(value, dict):
        raise ValueError("candidate-audit request must be an object")
    return value


def validate(value: dict[str, Any], expected_main_sha: str) -> dict[str, Any]:
    operation = value.get("operation")
    if operation not in OPERATION_KEYS:
        raise ValueError("candidate-audit operation is invalid")
    expected_keys = COMMON_KEYS | OPERATION_KEYS[operation]
    if set(value) != expected_keys:
        raise ValueError("candidate-audit request must contain exactly the canonical fields")
    if value.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    if not RUN_ID_RE.fullmatch(str(value.get("run_id", ""))):
        raise ValueError("run_id is invalid")
    if value.get("main_sha") != expected_main_sha:
        raise ValueError("main_sha is invalid or stale")
    window = value.get("window")
    if not isinstance(window, dict) or set(window) != {"start", "end", "timezone"}:
        raise ValueError("window must contain exactly start, end, and timezone")
    start = parse_time(window["start"], "window.start")
    end = parse_time(window["end"], "window.end")
    if end - start != timedelta(hours=24):
        raise ValueError("window must be exactly 24 hours")
    if not isinstance(window["timezone"], str) or not window["timezone"].strip():
        raise ValueError("window.timezone is required")

    if operation in {"candidate_audit_review", "candidate_audit_score"}:
        sequence = value.get("batch_sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ValueError("batch_sequence must be a positive integer")
        field = "rows" if operation == "candidate_audit_review" else "events"
        maximum = 20 if field == "rows" else 4
        items = value.get(field)
        if not isinstance(items, list) or not 1 <= len(items) <= maximum:
            raise ValueError(f"{field} must contain 1..{maximum} bounded results")
        if any(not isinstance(item, dict) for item in items):
            raise ValueError(f"{field} entries must be objects")
    if operation == "candidate_audit_finalize":
        parse_time(value.get("generated_at"), "generated_at")
        scopes = value.get("section_scopes")
        if not isinstance(scopes, list) or not scopes:
            raise ValueError("section_scopes must contain at least one scope")
        codes = []
        for scope in scopes:
            if not isinstance(scope, dict) or set(scope) != {"code", "member_country_codes", "fallback"}:
                raise ValueError("section_scopes entries must use the canonical fields")
            if not re.fullmatch(r"[A-Z]{3}", str(scope.get("code", ""))):
                raise ValueError("section scope code must be three uppercase letters")
            if not isinstance(scope.get("member_country_codes"), list) or not isinstance(scope.get("fallback"), bool):
                raise ValueError("section scope members/fallback are invalid")
            codes.append(scope["code"])
        if len(codes) != len(set(codes)) or sum(scope["fallback"] for scope in scopes) != 1:
            raise ValueError("section scopes require unique codes and exactly one fallback")
    if operation in {"verification_event", "map_event"}:
        if re.fullmatch(r"[A-Z]{3}-[0-9]{2,}", str(value.get("event_id", ""))) is None:
            raise ValueError(f"{operation} event_id is invalid")
        payload_field = "verification" if operation == "verification_event" else "map"
        if not isinstance(value.get(payload_field), dict):
            raise ValueError(f"{payload_field} payload must be an object")
    if len(transport.canonical_bytes(value)) > MAX_COMMENT_REQUEST_BYTES:
        raise ValueError("candidate-audit request exceeds the issue-comment transport limit")
    return value


def execute(request: dict[str, Any], runtime_root: Path, runlogs_root: Path) -> dict[str, Any]:
    run_root = runlogs_root / "logs" / "runs" / request["run_id"]
    input_root = run_root / "audit-input"
    work_root = run_root / "candidate-audit-work"
    operation = request["operation"]
    if operation == "candidate_audit_review":
        result = {
            "schema_version": "1.0.0", "run_id": request["run_id"],
            "main_sha": request["main_sha"], "window": request["window"],
            "batch_sequence": request["batch_sequence"], "rows": request["rows"],
        }
        temporary = work_root / "requests" / f"review-{request['batch_sequence']:04d}.json"
        write_json(temporary, result)
        return transport.record_review_result(
            input_root / "manifest.json",
            input_root / f"batch-{request['batch_sequence']:04d}.json",
            temporary,
            work_root / "row-review",
        )
    if operation == "candidate_audit_prepare_scoring":
        return transport.prepare_scoring(
            input_root / "manifest.json", work_root / "row-review", work_root / "score-input"
        )
    if operation == "candidate_audit_score":
        result = {
            "schema_version": "1.0.0", "run_id": request["run_id"],
            "main_sha": request["main_sha"], "window": request["window"],
            "batch_sequence": request["batch_sequence"], "events": request["events"],
        }
        temporary = work_root / "requests" / f"score-{request['batch_sequence']:04d}.json"
        write_json(temporary, result)
        return transport.record_score_result(
            work_root / "score-input" / "manifest.json",
            work_root / "score-input" / f"batch-{request['batch_sequence']:04d}.json",
            temporary,
            work_root / "score-results",
        )

    verification_root = run_root / "verification-work"
    if operation == "verification_prepare":
        return verification_transport.prepare(
            run_root / "candidate-audit.json", verification_root / "input",
            run_id=request["run_id"], main_sha=request["main_sha"],
            window_start=request["window"]["start"], window_end=request["window"]["end"],
            timezone_name=request["window"]["timezone"],
        )
    if operation == "verification_event":
        patch = {
            "schema_version": "1.0.0", "run_id": request["run_id"],
            "main_sha": request["main_sha"], "window": request["window"],
            "event_id": request["event_id"], "verification": request["verification"],
        }
        input_manifest = json.loads(
            (verification_root / "input" / "manifest.json").read_text(encoding="utf-8")
        )
        if transport.identity(patch) != transport.identity(input_manifest):
            raise ValueError("verification patch changed durable run/main/window identity")
        if request["event_id"] not in input_manifest.get("event_ids", []):
            raise ValueError("verification patch references an unknown selected event")
        errors = verification_transport.verification_errors(request["verification"])
        if errors:
            raise ValueError("verification payload is invalid: " + "; ".join(errors))
        stored = transport.append_only_write(
            verification_root / "patches" / f"{request['event_id']}.json", patch
        )
        return {
            "schema_version": "1.0.0", "run_id": request["run_id"],
            "main_sha": request["main_sha"], "window": request["window"],
            "event_id": request["event_id"], "result_sha256": transport.digest(stored),
            "status": "terminal",
        }
    if operation == "verification_finalize":
        return verification_transport.finalize(
            verification_root / "input" / "manifest.json",
            verification_root / "patches", run_root / "verification.json",
        )

    map_root = run_root / "map-work"
    if operation == "map_prepare":
        return map_transport.prepare(
            run_root / "candidate-audit.json", run_root / "verification.json",
            map_root / "input",
        )
    if operation == "map_event":
        patch = {
            "schema_version": "1.0.0", "run_id": request["run_id"],
            "main_sha": request["main_sha"], "window": request["window"],
            "event_id": request["event_id"], "map": request["map"],
        }
        input_manifest = json.loads((map_root / "input" / "manifest.json").read_text(encoding="utf-8"))
        if transport.identity(patch) != transport.identity(input_manifest):
            raise ValueError("map patch changed durable run/main/window identity")
        if request["event_id"] not in input_manifest.get("event_ids", []):
            raise ValueError("map patch references an unknown selected event")
        stored = transport.append_only_write(map_root / "patches" / f"{request['event_id']}.json", patch)
        return {
            "schema_version": "1.0.0", "run_id": request["run_id"],
            "main_sha": request["main_sha"], "window": request["window"],
            "event_id": request["event_id"], "result_sha256": transport.digest(stored),
            "status": "terminal",
        }
    if operation == "map_finalize":
        return map_transport.finalize(
            map_root / "input" / "manifest.json", map_root / "patches",
            run_root / "map-decisions.json",
        )

    coverage_path = run_root / "remote-acquisition" / "source-coverage.json"
    if not coverage_path.is_file():
        raise ValueError("candidate audit finalize requires durable source coverage")
    run_base = {
        "run_id": request["run_id"],
        "generated_at": request["generated_at"],
        "window_start": request["window"]["start"],
        "window_end": request["window"]["end"],
        "section_scopes": request["section_scopes"],
        "source_coverage": json.loads(coverage_path.read_text(encoding="utf-8")),
    }
    run_base_path = work_root / "run-base.json"
    transport.append_only_write(run_base_path, run_base)
    return transport.finalize(
        input_root / "manifest.json", work_root / "row-review",
        work_root / "score-input" / "manifest.json", work_root / "score-results",
        run_base_path, run_root / "source-row-admissions.json",
        runtime_root / "news-source-pool.json", runlogs_root / "logs" / "latest-candidate-audit.json",
        run_root / "candidate-audit.json",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    parse = sub.add_parser("parse-comment")
    parse.add_argument("--comment-env", required=True)
    parse.add_argument("--expected-main-sha", required=True)
    parse.add_argument("--output", required=True, type=Path)
    run = sub.add_parser("execute")
    run.add_argument("--request", required=True, type=Path)
    run.add_argument("--expected-main-sha", required=True)
    run.add_argument("--runtime-root", required=True, type=Path)
    run.add_argument("--run-logs-root", required=True, type=Path)
    args = parser.parse_args()
    if args.cmd == "parse-comment":
        request = validate(extract_request_from_comment(os.environ.get(args.comment_env, "")), args.expected_main_sha)
        write_json(args.output, request)
        print(json.dumps(request, ensure_ascii=False, sort_keys=True))
        return 0
    request = validate(json.loads(args.request.read_text(encoding="utf-8")), args.expected_main_sha)
    result = execute(request, args.runtime_root, args.run_logs_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
