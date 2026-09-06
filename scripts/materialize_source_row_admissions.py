#!/usr/bin/env python3
"""Build and validate the immutable, lossless source-row admission universe."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1.0"
COMPAT_SCHEMA_VERSIONS = {"1.0.0", "1.1.0"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROW_ID = re.compile(r"^row-[0-9a-f]{24}$")
STATUSES = {"content_ready", "outside_window", "unresolved_exhausted"}
REVIEWS = {"pending_semantic_review", "outside_window", "unresolved_exhausted"}


def _rows(value: Any, label: str):
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} rows must be an array of objects")
    ids = [str(item.get("row_id", "")) for item in value]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{label} row_id values must be non-empty and unique")
    return value, dict(zip(ids, value))


def _required(value: dict, fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        if not str(value.get(field, "")).strip():
            raise ValueError(f"{label} missing {field}")


def _optional(value: Any):
    return None if value is None or str(value).strip() == "" else value


def build(source_candidates: dict, relevance_gate: dict, article_evidence: dict, *, run_id: str) -> dict:
    candidates, candidate_map = _rows(source_candidates.get("items"), "source candidate")
    decisions, decision_map = _rows(relevance_gate.get("decisions"), "relevance decision")
    evidence, evidence_map = _rows(article_evidence.get("rows"), "article evidence")
    expected = set(candidate_map)
    if set(decision_map) != expected or set(evidence_map) != expected:
        raise ValueError("relevance decisions and article evidence must match source rows exactly")
    if relevance_gate.get("input_article_row_count") != len(candidates):
        raise ValueError("relevance gate input count must equal source row count")

    rows = []
    for candidate in candidates:
        row_id = candidate["row_id"]
        decision = decision_map[row_id]
        evidence_row = evidence_map[row_id]
        _required(
            candidate,
            (
                "candidate_id", "provisional_group_id", "source_id", "section", "url",
                "canonical_url", "published_at", "listing_timestamp_evidence",
            ),
            f"source row {row_id}",
        )
        if (
            decision.get("candidate_id") != candidate.get("candidate_id")
            or decision.get("source_id") != candidate.get("source_id")
            or decision.get("canonical_url") != candidate.get("canonical_url")
        ):
            raise ValueError(f"relevance decision mismatch for {row_id}")

        status = evidence_row.get("admission_status")
        if status not in STATUSES:
            raise ValueError(f"article evidence {row_id} admission_status is invalid")
        model = evidence_row.get("model_evidence")
        if (
            not isinstance(model, dict)
            or model.get("review_status") not in REVIEWS
            or not str(model.get("reason", "")).strip()
            or not isinstance(model.get("evidence_refs"), list)
            or not model["evidence_refs"]
        ):
            raise ValueError(f"article evidence {row_id} model_evidence is invalid")
        expected_review = {
            "content_ready": "pending_semantic_review",
            "outside_window": "outside_window",
            "unresolved_exhausted": "unresolved_exhausted",
        }[status]
        if model.get("review_status") != expected_review:
            raise ValueError(f"article evidence {row_id} review_status must be {expected_review}")

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
            "relevance_route": decision["route"],
            "relevance_reasons": decision["reasons"],
            "admission_status": status,
            "model_evidence": model,
        }

        if status in {"content_ready", "outside_window"}:
            _required(
                evidence_row,
                (
                    "article_body_published_at", "article_body_timestamp_evidence",
                    "article_body_evidence_url", "content_sha256",
                ),
                f"article evidence {row_id}",
            )
            content_sha = str(evidence_row["content_sha256"]).lower()
            if not HEX64.fullmatch(content_sha):
                raise ValueError(f"article evidence {row_id} content_sha256 is invalid")
            row.update({
                "article_body_published_at": evidence_row["article_body_published_at"],
                "article_body_timestamp_evidence": evidence_row["article_body_timestamp_evidence"],
                "article_body_evidence_url": evidence_row["article_body_evidence_url"],
                "content_sha256": content_sha,
                "failure_evidence": None,
            })
        else:
            failure = evidence_row.get("failure_evidence")
            if (
                not isinstance(failure, dict)
                or not str(failure.get("attempted_url", "")).strip()
                or not str(failure.get("error", "")).strip()
            ):
                raise ValueError(f"exhausted article evidence {row_id} requires failure_evidence")
            content_sha = _optional(evidence_row.get("content_sha256"))
            if content_sha is not None:
                content_sha = str(content_sha).lower()
                if not HEX64.fullmatch(content_sha):
                    raise ValueError(f"exhausted article evidence {row_id} content_sha256 is invalid")
            row.update({
                "article_body_published_at": _optional(evidence_row.get("article_body_published_at")),
                "article_body_timestamp_evidence": _optional(evidence_row.get("article_body_timestamp_evidence")),
                "article_body_evidence_url": _optional(evidence_row.get("article_body_evidence_url")),
                "content_sha256": content_sha,
                "failure_evidence": failure,
            })
        rows.append(row)

    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window_start": source_candidates.get("window_start"),
        "window_end": source_candidates.get("window_end"),
        "source_row_count": len(candidates),
        "admitted_row_count": len(rows),
        "rows": rows,
    }
    errors = validate(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    schema_version = data.get("schema_version")
    if schema_version not in COMPAT_SCHEMA_VERSIONS:
        errors.append(f"schema_version must be one of {sorted(COMPAT_SCHEMA_VERSIONS)}")
    rows = data.get("rows")
    if not isinstance(rows, list):
        return errors + ["rows must be an array"]
    ids = [item.get("row_id") for item in rows if isinstance(item, dict)]
    if len(ids) != len(rows) or any(not item for item in ids) or len(set(ids)) != len(ids):
        errors.append("admission row_id values must be present and unique")
    try:
        start = datetime.fromisoformat(str(data.get("window_start", "")).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(data.get("window_end", "")).replace("Z", "+00:00"))
    except ValueError:
        start = end = None
        errors.append("run window is invalid")

    legacy = schema_version == "1.0.0"
    for index, item in enumerate(rows, 1):
        if not isinstance(item, dict):
            continue
        label = f"rows[{index}]"
        status = item.get("admission_status")
        if not ROW_ID.fullmatch(str(item.get("row_id", ""))):
            errors.append(f"{label}.row_id is invalid")
        for field in (
            "candidate_id", "provisional_group_id", "source_id", "section", "url",
            "canonical_url", "listing_published_at", "listing_timestamp_evidence",
        ):
            if not str(item.get(field, "")).strip():
                errors.append(f"{label}.{field} is required")
        if item.get("relevance_route") not in {"content_hydration", "lightweight_semantic_review"}:
            errors.append(f"{label}.relevance_route is invalid")

        if legacy:
            if status != "content_ready":
                errors.append(f"{label}.legacy admission_status must be content_ready")
            allowed_reviews = {"pending_semantic_review"}
        else:
            if status not in STATUSES:
                errors.append(f"{label}.admission_status is invalid")
            allowed_reviews = REVIEWS
        model = item.get("model_evidence")
        if (
            not isinstance(model, dict)
            or model.get("review_status") not in allowed_reviews
            or not str(model.get("reason", "")).strip()
            or not isinstance(model.get("evidence_refs"), list)
            or not model.get("evidence_refs")
        ):
            errors.append(f"{label}.model_evidence is invalid")

        effective_status = "content_ready" if legacy else status
        if effective_status in {"content_ready", "outside_window"}:
            expected_review = "pending_semantic_review" if effective_status == "content_ready" else "outside_window"
            if isinstance(model, dict) and model.get("review_status") != expected_review:
                errors.append(f"{label}.model_evidence.review_status must be {expected_review}")
            for field in (
                "article_body_published_at", "article_body_timestamp_evidence",
                "article_body_evidence_url", "content_sha256",
            ):
                if not str(item.get(field, "")).strip():
                    errors.append(f"{label}.{field} is required for {effective_status}")
            if not HEX64.fullmatch(str(item.get("content_sha256", ""))):
                errors.append(f"{label}.content_sha256 is invalid")
            if start and end:
                try:
                    timestamp = datetime.fromisoformat(
                        str(item.get("article_body_published_at", "")).replace("Z", "+00:00")
                    )
                    inside = start <= timestamp <= end
                    if effective_status == "content_ready" and not inside:
                        errors.append(f"{label}.content_ready article timestamp must be inside run window")
                    if effective_status == "outside_window" and inside:
                        errors.append(f"{label}.outside_window article timestamp must be outside run window")
                except ValueError:
                    errors.append(f"{label}.article_body_published_at is invalid")
            if not legacy and item.get("failure_evidence") is not None:
                errors.append(f"{label}.failure_evidence must be null for {effective_status}")
        elif effective_status == "unresolved_exhausted":
            if isinstance(model, dict) and model.get("review_status") != "unresolved_exhausted":
                errors.append(f"{label}.model_evidence.review_status must be unresolved_exhausted")
            failure = item.get("failure_evidence")
            if (
                not isinstance(failure, dict)
                or not str(failure.get("attempted_url", "")).strip()
                or not str(failure.get("error", "")).strip()
            ):
                errors.append(f"{label}.failure_evidence is required for unresolved_exhausted")
            content_sha = item.get("content_sha256")
            if content_sha is not None and not HEX64.fullmatch(str(content_sha)):
                errors.append(f"{label}.content_sha256 is invalid when present")

    if data.get("source_row_count") != len(rows) or data.get("admitted_row_count") != len(rows):
        errors.append("row counts must equal durable row count")
    if sum(Counter(item.get("admission_status") for item in rows if isinstance(item, dict)).values()) != len(rows):
        errors.append("admission status count must conserve all rows")
    return errors


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    for name in ("source-candidates", "relevance-gate", "article-evidence", "run-id", "output"):
        build_parser.add_argument("--" + name, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            errors = validate(load(args.input))
            for error in errors:
                print("FAIL:", error)
            if not errors:
                print("OK")
            return int(bool(errors))
        result = build(
            load(args.source_candidates),
            load(args.relevance_gate),
            load(args.article_evidence),
            run_id=args.run_id,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("FAIL:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
