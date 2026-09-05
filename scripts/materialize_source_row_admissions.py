#!/usr/bin/env python3
"""Build the immutable, lossless source-row admission universe."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1.0"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROW_ID = re.compile(r"^row-[0-9a-f]{24}$")
ADMISSION_STATUSES = {"content_ready", "outside_window", "unresolved_exhausted"}
REVIEW_STATUSES = {"pending_semantic_review", "outside_window", "unresolved_exhausted"}


def _unique_rows(value: Any, label: str) -> tuple[list[dict], dict[str, dict]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} rows must be an array of objects")
    ids = [str(item.get("row_id", "")) for item in value]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"{label} row_id values must be non-empty and unique")
    return value, dict(zip(ids, value))


def _optional_string(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def build(
    source_candidates: dict,
    relevance_gate: dict,
    article_evidence: dict,
    *,
    run_id: str,
) -> dict:
    candidates, candidate_by_id = _unique_rows(
        source_candidates.get("items"), "source candidate"
    )
    decisions, decision_by_id = _unique_rows(
        relevance_gate.get("decisions"), "relevance decision"
    )
    evidence_rows, evidence_by_id = _unique_rows(
        article_evidence.get("rows"), "article evidence"
    )
    expected = set(candidate_by_id)
    if set(decision_by_id) != expected:
        raise ValueError("relevance decisions must match source rows exactly")
    if set(evidence_by_id) != expected:
        raise ValueError("article evidence must match source rows exactly")
    if relevance_gate.get("input_article_row_count") != len(candidates):
        raise ValueError("relevance gate input count must equal source row count")

    rows = []
    for candidate in candidates:
        row_id = candidate["row_id"]
        decision = decision_by_id[row_id]
        evidence = evidence_by_id[row_id]
        for field in (
            "candidate_id", "provisional_group_id", "source_id", "section",
            "url", "canonical_url", "published_at", "listing_timestamp_evidence",
        ):
            if not str(candidate.get(field, "")).strip():
                raise ValueError(f"source row {row_id} missing {field}")
        if decision.get("candidate_id") != candidate.get("candidate_id"):
            raise ValueError(f"relevance decision candidate mismatch for {row_id}")
        if decision.get("source_id") != candidate.get("source_id"):
            raise ValueError(f"relevance decision source mismatch for {row_id}")
        if decision.get("canonical_url") != candidate.get("canonical_url"):
            raise ValueError(f"relevance decision canonical URL mismatch for {row_id}")

        status = evidence.get("admission_status")
        if status not in ADMISSION_STATUSES:
            raise ValueError(f"article evidence {row_id} admission_status is invalid")

        body_time = _optional_string(evidence.get("article_body_published_at"))
        timestamp_evidence = _optional_string(evidence.get("article_body_timestamp_evidence"))
        evidence_url = _optional_string(evidence.get("article_body_evidence_url"))
        content_sha = _optional_string(evidence.get("content_sha256"))

        if status in {"content_ready", "outside_window"}:
            if not body_time:
                raise ValueError(f"article evidence {row_id} missing article_body_published_at")
            if not timestamp_evidence:
                raise ValueError(f"article evidence {row_id} missing article_body_timestamp_evidence")
            if not evidence_url:
                raise ValueError(f"article evidence {row_id} missing article_body_evidence_url")
            if not content_sha or not HEX64.fullmatch(content_sha.lower()):
                raise ValueError(f"article evidence {row_id} content_sha256 must be 64 lowercase hex")
        else:
            if content_sha and not HEX64.fullmatch(content_sha.lower()):
                raise ValueError(f"article evidence {row_id} content_sha256 must be 64 lowercase hex when present")
            if not evidence_url:
                evidence_url = candidate["canonical_url"]

        model = evidence.get("model_evidence")
        if not isinstance(model, dict):
            raise ValueError(f"article evidence {row_id} missing model_evidence")
        if model.get("review_status") not in REVIEW_STATUSES:
            raise ValueError(f"article evidence {row_id} model review_status is invalid")
        if status == "content_ready" and model.get("review_status") != "pending_semantic_review":
            raise ValueError(f"article evidence {row_id} ready row must await semantic review")
        if status == "outside_window" and model.get("review_status") != "outside_window":
            raise ValueError(f"article evidence {row_id} outside-window row must preserve outside-window review")
        if status == "unresolved_exhausted" and model.get("review_status") != "unresolved_exhausted":
            raise ValueError(f"article evidence {row_id} exhausted row must preserve exhausted review")
        if not str(model.get("reason", "")).strip():
            raise ValueError(f"article evidence {row_id} model reason is required")
        refs = model.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not all(str(item).strip() for item in refs):
            raise ValueError(f"article evidence {row_id} model evidence_refs are required")

        row = {
            "row_id": row_id,
            "candidate_id": candidate["candidate_id"],
            "provisional_group_id": candidate["provisional_group_id"],
            "source_id": candidate["source_id"],
            "section": candidate["section"],
            "url": candidate["url"],
            "canonical_url": candidate["canonical_url"],
            "listing_published_at": candidate["published_at"],
            "listing_timestamp_evidence": candidate["listing_timestamp_evidence"],
            "article_body_published_at": body_time,
            "article_body_timestamp_evidence": timestamp_evidence,
            "article_body_evidence_url": evidence_url,
            "content_sha256": content_sha.lower() if content_sha else None,
            "relevance_route": decision["route"],
            "relevance_reasons": decision["reasons"],
            "admission_status": status,
            "model_evidence": model,
        }
        attempts = evidence.get("hydration_attempts")
        if isinstance(attempts, list) and attempts:
            row["hydration_attempts"] = attempts
        rows.append(row)

    status_counts = Counter(row["admission_status"] for row in rows)
    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window_start": source_candidates.get("window_start"),
        "window_end": source_candidates.get("window_end"),
        "source_row_count": len(candidates),
        "admitted_row_count": len(rows),
        "content_ready_row_count": status_counts["content_ready"],
        "outside_window_row_count": status_counts["outside_window"],
        "unresolved_exhausted_row_count": status_counts["unresolved_exhausted"],
        "rows": rows,
    }
    errors = validate(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    rows = data.get("rows")
    if not isinstance(rows, list):
        return errors + ["rows must be an array"]
    ids = [item.get("row_id") for item in rows if isinstance(item, dict)]
    if len(ids) != len(rows) or any(not item for item in ids):
        errors.append("every admission row must be an object with row_id")
    elif len(set(ids)) != len(ids):
        errors.append("admission row_id values must be unique")

    try:
        start = datetime.fromisoformat(str(data.get("window_start", "")).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(data.get("window_end", "")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        start = end = None
        errors.append("run window timestamps are invalid")

    for index, item in enumerate(rows, 1):
        label = f"rows[{index}]"
        if not isinstance(item, dict):
            continue
        if not ROW_ID.fullmatch(str(item.get("row_id", ""))):
            errors.append(f"{label}.row_id must be row- plus 24 lowercase hex characters")
        for field in (
            "candidate_id", "provisional_group_id", "source_id", "section", "url",
            "canonical_url", "listing_published_at", "listing_timestamp_evidence",
            "article_body_evidence_url",
        ):
            if not str(item.get(field, "")).strip():
                errors.append(f"{label}.{field} is required")
        status = item.get("admission_status")
        if status not in ADMISSION_STATUSES:
            errors.append(f"{label}.admission_status is invalid")

        body_time = item.get("article_body_published_at")
        timestamp_evidence = item.get("article_body_timestamp_evidence")
        content_sha = item.get("content_sha256")
        if status in {"content_ready", "outside_window"}:
            if not str(body_time or "").strip():
                errors.append(f"{label}.article_body_published_at is required")
            if not str(timestamp_evidence or "").strip():
                errors.append(f"{label}.article_body_timestamp_evidence is required")
            if not HEX64.fullmatch(str(content_sha or "")):
                errors.append(f"{label}.content_sha256 must be 64 lowercase hex characters")
            try:
                parsed = datetime.fromisoformat(str(body_time).replace("Z", "+00:00"))
                if start is not None and end is not None:
                    inside = start <= parsed <= end
                    if status == "content_ready" and not inside:
                        errors.append(f"{label}.content_ready timestamp must be inside the run window")
                    if status == "outside_window" and inside:
                        errors.append(f"{label}.outside_window timestamp must be outside the run window")
            except (TypeError, ValueError):
                errors.append(f"{label}.article_body_published_at is invalid")
        else:
            if content_sha is not None and not HEX64.fullmatch(str(content_sha)):
                errors.append(f"{label}.content_sha256 must be null or 64 lowercase hex characters")
            if body_time is not None:
                try:
                    datetime.fromisoformat(str(body_time).replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    errors.append(f"{label}.article_body_published_at must be null or a valid timestamp")

        if item.get("relevance_route") not in {
            "content_hydration", "lightweight_semantic_review"
        }:
            errors.append(f"{label}.relevance_route is invalid")
        reasons = item.get("relevance_reasons")
        if not isinstance(reasons, list) or not reasons or not all(str(value).strip() for value in reasons):
            errors.append(f"{label}.relevance_reasons are required")
        model = item.get("model_evidence")
        if not isinstance(model, dict):
            errors.append(f"{label}.model_evidence is required")
        else:
            review = model.get("review_status")
            if review not in REVIEW_STATUSES:
                errors.append(f"{label}.model_evidence.review_status is invalid")
            expected_review = {
                "content_ready": "pending_semantic_review",
                "outside_window": "outside_window",
                "unresolved_exhausted": "unresolved_exhausted",
            }.get(status)
            if expected_review and review != expected_review:
                errors.append(f"{label}.model_evidence.review_status must be {expected_review}")
            if not str(model.get("reason", "")).strip():
                errors.append(f"{label}.model_evidence.reason is required")
            refs = model.get("evidence_refs")
            if not isinstance(refs, list) or not refs or not all(str(value).strip() for value in refs):
                errors.append(f"{label}.model_evidence.evidence_refs are required")
        attempts = item.get("hydration_attempts")
        if attempts is not None and (
            not isinstance(attempts, list)
            or not all(isinstance(value, dict) for value in attempts)
        ):
            errors.append(f"{label}.hydration_attempts must be an array of objects")

    for field in ("source_row_count", "admitted_row_count"):
        if data.get(field) != len(rows):
            errors.append(f"{field} must equal the durable row count {len(rows)}")
    counts = Counter(
        item.get("admission_status") for item in rows if isinstance(item, dict)
    )
    expected_counts = {
        "content_ready_row_count": counts["content_ready"],
        "outside_window_row_count": counts["outside_window"],
        "unresolved_exhausted_row_count": counts["unresolved_exhausted"],
    }
    for field, expected in expected_counts.items():
        if data.get(field) != expected:
            errors.append(f"{field} must equal {expected}")
    if sum(counts.values()) != len(rows):
        errors.append("admission status count must conserve all rows")
    return errors


def _load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--source-candidates", required=True)
    build_parser.add_argument("--relevance-gate", required=True)
    build_parser.add_argument("--article-evidence", required=True)
    build_parser.add_argument("--run-id", required=True)
    build_parser.add_argument("--output", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            errors = validate(_load(args.input))
            for error in errors:
                print("FAIL:", error)
            if not errors:
                print("OK")
            return int(bool(errors))
        result = build(
            _load(args.source_candidates),
            _load(args.relevance_gate),
            _load(args.article_evidence),
            run_id=args.run_id,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("FAIL:", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
