#!/usr/bin/env python3
"""Create, rotate, and validate the compact mobile scheduled-run ledger."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import run_identity


SCHEMA_VERSION = "1.0.0"
STAGES = (
    "schedule-prepared",
    "executor-started",
    "main-pinned",
    "workspace-ready",
    "source-scan",
    "candidate-audit",
    "selection-verified",
    "visuals-completed",
    "reader-rendered",
    "github-result-saved",
    "delivery-handoff",
)
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}
STATUSES = {
    "awaiting_executor",
    "running",
    "completed",
    "failed",
    "interrupted_by_next_run",
}
DELIVERY_STATUSES = {
    "not_ready",
    "reader_saved",
    "handoff_started",
    "client_confirmed",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def validate_record(record: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "scheduled_for",
        "status",
        "current_stage",
        "stage_index",
        "last_completed_stage",
        "main_sha",
        "updated_at",
        "last_error",
        "delivery_status",
        "client_confirmation_supported",
        "reader_artifact",
    }
    missing = required.difference(record)
    if missing:
        raise ValueError(f"missing run-log fields: {', '.join(sorted(missing))}")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported run-log schema version")
    if not run_identity.is_valid_run_id(record["run_id"]):
        raise ValueError("run_id must use canonical format gnb-YYYYMMDDTHHMMSSZ-xxxxxxxx")
    if record["status"] not in STATUSES:
        raise ValueError(f"invalid status: {record['status']}")
    stage = record["current_stage"]
    if stage not in STAGE_INDEX or record["stage_index"] != STAGE_INDEX[stage]:
        raise ValueError("stage_index does not match current_stage")
    if record["last_completed_stage"] not in (None, *STAGES):
        raise ValueError("invalid last_completed_stage")
    if record["delivery_status"] not in DELIVERY_STATUSES:
        raise ValueError("invalid delivery_status")
    if record["delivery_status"] == "client_confirmed" and not record.get(
        "client_confirmation_supported"
    ):
        raise ValueError("client delivery cannot be confirmed without an external acknowledgement")


def prepare_run(
    ledger_dir: Path | str,
    *,
    run_id: str,
    scheduled_for: str,
    updated_at: str,
) -> dict[str, Any]:
    ledger_dir = Path(ledger_dir)
    current_path = ledger_dir / "current.json"
    previous_path = ledger_dir / "previous.json"

    if current_path.exists():
        previous = _read_json(current_path)
        validate_record(previous)
        if previous["status"] in {"awaiting_executor", "running"}:
            previous["status"] = "interrupted_by_next_run"
            previous["last_error"] = {
                "code": "executor_interrupted",
                "message": "The next scheduled run started before this run reached a terminal state.",
            }
            previous["updated_at"] = updated_at
        _atomic_write(previous_path, previous)

    current: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "scheduled_for": scheduled_for,
        "status": "awaiting_executor",
        "current_stage": "schedule-prepared",
        "stage_index": STAGE_INDEX["schedule-prepared"],
        "last_completed_stage": None,
        "main_sha": None,
        "updated_at": updated_at,
        "last_error": None,
        "delivery_status": "not_ready",
        "client_confirmation_supported": False,
        "reader_artifact": None,
    }
    validate_record(current)
    _atomic_write(current_path, current)
    return current


def advance_run(
    ledger_dir: Path | str,
    *,
    run_id: str,
    stage: str,
    updated_at: str,
    status: str = "running",
    delivery_status: str | None = None,
    client_ack: bool = False,
    main_sha: str | None = None,
    last_error: dict[str, str] | None = None,
    reader_artifact: dict[str, str] | None = None,
) -> dict[str, Any]:
    ledger_dir = Path(ledger_dir)
    current_path = ledger_dir / "current.json"
    current = _read_json(current_path)
    validate_record(current)
    if current["run_id"] != run_id:
        raise ValueError("run_id does not match current.json")
    if stage not in STAGE_INDEX:
        raise ValueError(f"unknown stage: {stage}")
    if STAGE_INDEX[stage] < current["stage_index"]:
        raise ValueError(
            f"stage regression: {current['current_stage']} -> {stage}"
        )
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status}")

    new_delivery_status = delivery_status or current["delivery_status"]
    if new_delivery_status == "client_confirmed" and not client_ack:
        raise ValueError("client delivery cannot be confirmed without an external acknowledgement")
    if status == "completed" and (
        stage != "delivery-handoff"
        or new_delivery_status not in {"handoff_started", "client_confirmed"}
    ):
        raise ValueError("completed requires the delivery-handoff stage")

    if STAGE_INDEX[stage] > current["stage_index"]:
        current["last_completed_stage"] = current["current_stage"]
    current["current_stage"] = stage
    current["stage_index"] = STAGE_INDEX[stage]
    current["status"] = status
    current["updated_at"] = updated_at
    current["delivery_status"] = new_delivery_status
    current["client_confirmation_supported"] = bool(client_ack)
    if main_sha is not None:
        current["main_sha"] = main_sha
    if reader_artifact is not None:
        current["reader_artifact"] = reader_artifact
    current["last_error"] = last_error
    validate_record(current)
    _atomic_write(current_path, current)
    return current


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--ledger-dir", type=Path, required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--scheduled-for", required=True)
    prepare.add_argument("--updated-at", required=True)

    advance = subparsers.add_parser("advance")
    advance.add_argument("--ledger-dir", type=Path, required=True)
    advance.add_argument("--run-id", required=True)
    advance.add_argument("--stage", choices=STAGES, required=True)
    advance.add_argument("--updated-at", required=True)
    advance.add_argument("--status", choices=sorted(STATUSES), default="running")
    advance.add_argument("--delivery-status", choices=sorted(DELIVERY_STATUSES))
    advance.add_argument("--client-ack", action="store_true")
    advance.add_argument("--main-sha")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        result = prepare_run(
            args.ledger_dir,
            run_id=args.run_id,
            scheduled_for=args.scheduled_for,
            updated_at=args.updated_at,
        )
    elif args.command == "advance":
        result = advance_run(
            args.ledger_dir,
            run_id=args.run_id,
            stage=args.stage,
            updated_at=args.updated_at,
            status=args.status,
            delivery_status=args.delivery_status,
            client_ack=args.client_ack,
            main_sha=args.main_sha,
        )
    else:
        result = _read_json(args.input)
        validate_record(result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
