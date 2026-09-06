#!/usr/bin/env python3
"""Materialize bounded, row-conserved mobile candidate-audit input batches.

This helper is transport-only. It does not cluster semantic events, score Public
Value V2 dimensions, verify claims, or select news. It projects the already
persisted source-row universe plus bounded hydration evidence into model-readable
batches so the scheduled host can perform those semantic steps without re-fetching
hundreds of articles or silently falling back to titles.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

BATCH_SIZE = 20
RESULT_RE = re.compile(r"batch-(\d{4})-result\.json$")
TERMINAL = {"content_ready", "outside_window", "unresolved_exhausted"}


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


def latest_hydration(content_evidence_dir: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    latest_sequence: dict[str, int] = {}
    for path in sorted(content_evidence_dir.glob("batch-*-result.json")):
        match = RESULT_RE.fullmatch(path.name)
        if not match:
            continue
        sequence = int(match.group(1))
        value = load(path)
        rows = value.get("rows") if isinstance(value, dict) else None
        if not isinstance(rows, list):
            raise ValueError(f"{path} rows must be an array")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("row_id"), str):
                raise ValueError(f"{path} contains invalid row evidence")
            row_id = row["row_id"]
            prior = latest.get(row_id)
            if prior is not None and prior.get("status") in TERMINAL:
                raise ValueError(f"terminal hydration row repeated: {row_id}")
            latest[row_id] = row
            latest_sequence[row_id] = sequence
    for row_id, row in latest.items():
        row["_batch_sequence"] = latest_sequence[row_id]
    return latest


def build(
    source_candidates_path: Path,
    admissions_path: Path,
    content_evidence_dir: Path,
    output_dir: Path,
    *,
    main_sha: str,
    timezone_name: str,
) -> dict[str, Any]:
    source = load(source_candidates_path)
    admissions = load(admissions_path)
    source_rows = source.get("items") if isinstance(source, dict) else None
    admitted_rows = admissions.get("rows") if isinstance(admissions, dict) else None
    if not isinstance(source_rows, list) or not isinstance(admitted_rows, list):
        raise ValueError("source candidates and admissions must contain row arrays")

    source_by_id = {str(row.get("row_id")): row for row in source_rows if isinstance(row, dict)}
    admission_by_id = {str(row.get("row_id")): row for row in admitted_rows if isinstance(row, dict)}
    if len(source_by_id) != len(source_rows):
        raise ValueError("source candidate row_id values must be unique")
    if len(admission_by_id) != len(admitted_rows):
        raise ValueError("admission row_id values must be unique")
    if set(source_by_id) != set(admission_by_id):
        raise ValueError("source-row admissions do not conserve the current source candidate universe")
    expected_count = admissions.get("source_row_count")
    if expected_count != len(source_rows) or admissions.get("admitted_row_count") != len(source_rows):
        raise ValueError("source-row admission counts do not match the source candidate universe")

    hydration = latest_hydration(content_evidence_dir)
    if set(hydration) != set(source_by_id):
        missing = sorted(set(source_by_id) - set(hydration))
        extra = sorted(set(hydration) - set(source_by_id))
        raise ValueError(
            f"hydration universe mismatch: missing={missing[:3]} extra={extra[:3]}"
        )
    if any(row.get("status") not in TERMINAL for row in hydration.values()):
        raise ValueError("audit input requires a fully terminal hydration universe")

    run_id = admissions.get("run_id")
    window_start = admissions.get("window_start")
    window_end = admissions.get("window_end")
    if not all(isinstance(value, str) and value for value in (run_id, window_start, window_end)):
        raise ValueError("admissions are missing run/window identity")
    if not re.fullmatch(r"[0-9a-f]{40}", main_sha):
        raise ValueError("main_sha must be a 40-character lowercase hex SHA")
    if not timezone_name:
        raise ValueError("timezone is required")

    rows: list[dict[str, Any]] = []
    insufficient_excerpt = 0
    for row_id in sorted(source_by_id):
        source_row = source_by_id[row_id]
        admission = admission_by_id[row_id]
        evidence = hydration[row_id]
        status = evidence["status"]
        excerpt = evidence.get("model_excerpt")
        if status == "content_ready":
            model_input_status = (
                "ready" if isinstance(excerpt, str) and excerpt.strip() else "insufficient_excerpt"
            )
            if model_input_status == "insufficient_excerpt":
                insufficient_excerpt += 1
        else:
            model_input_status = "terminal_without_content_review"
        summary = str(source_row.get("summary") or "")[:800]
        rows.append({
            "row_id": row_id,
            "candidate_id": source_row.get("candidate_id"),
            "provisional_group_id": source_row.get("provisional_group_id"),
            "source_id": source_row.get("source_id"),
            "section": source_row.get("section"),
            "title": source_row.get("title"),
            "summary": summary,
            "summary_quality": source_row.get("summary_quality"),
            "canonical_url": source_row.get("canonical_url"),
            "listing_published_at": source_row.get("published_at"),
            "admission_status": admission.get("admission_status"),
            "article_body_published_at": evidence.get("article_body_published_at"),
            "article_body_evidence_url": evidence.get("article_body_evidence_url"),
            "content_sha256": evidence.get("content_sha256"),
            "hydration_batch_sequence": evidence.get("_batch_sequence"),
            "model_excerpt": excerpt,
            "model_input_status": model_input_status,
            "failure_evidence": admission.get("failure_evidence"),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("batch-*.json"):
        stale.unlink()
    batch_files: list[str] = []
    for offset in range(0, len(rows), BATCH_SIZE):
        sequence = offset // BATCH_SIZE + 1
        batch_rows = rows[offset : offset + BATCH_SIZE]
        path = output_dir / f"batch-{sequence:04d}.json"
        atomic_write(path, {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "main_sha": main_sha,
            "window": {
                "start": window_start,
                "end": window_end,
                "timezone": timezone_name,
            },
            "batch_sequence": sequence,
            "row_count": len(batch_rows),
            "rows": batch_rows,
        })
        batch_files.append(path.name)

    manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "main_sha": main_sha,
        "window": {
            "start": window_start,
            "end": window_end,
            "timezone": timezone_name,
        },
        "source_row_count": len(rows),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batch_files),
        "batch_files": batch_files,
        "content_ready_count": sum(row["admission_status"] == "content_ready" for row in rows),
        "insufficient_excerpt_count": insufficient_excerpt,
        "ready_for_model_audit": insufficient_excerpt == 0,
    }
    atomic_write(output_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-candidates", required=True, type=Path)
    parser.add_argument("--source-row-admissions", required=True, type=Path)
    parser.add_argument("--content-evidence-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--timezone", required=True)
    args = parser.parse_args()
    manifest = build(
        args.source_candidates,
        args.source_row_admissions,
        args.content_evidence_dir,
        args.output_dir,
        main_sha=args.main_sha,
        timezone_name=args.timezone,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
