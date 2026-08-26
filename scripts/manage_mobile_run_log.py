#!/usr/bin/env python3
"""Create, rotate, and validate the compact mobile scheduled-run ledger."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import run_identity


SCHEMA_VERSION = "1.5.0"
EXECUTION_MODES = {"full-runtime", "mobile-native"}
DELIVERY_PROFILES = {"full-assets", "reader-canonical-capability-degraded"}
NATIVE_MEDIA_STATUSES = {"available", "unavailable"}
KNOWN_CAPABILITY_LIMITATIONS = {"NATIVE_MEDIA_UNAVAILABLE"}
DURABLE_AUDIT_STATUSES = {
    "not_started",
    "updated",
    "preserved_merge_deferred",
    "current_run_only",
}
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
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported run-log schema version")
    return value


def _read_artifact_reference(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact reference must be an object")
    return value


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
        "execution_mode",
        "delivery_profile",
        "native_media_status",
        "capability_limitations",
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
        "candidate_audit_artifact",
        "verification_artifact",
        "map_decisions_artifact",
        "image_evidence_artifact",
        "durable_audit_status",
        "durable_audit_artifact",
    }
    missing = required.difference(record)
    if missing:
        raise ValueError(f"missing run-log fields: {', '.join(sorted(missing))}")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported run-log schema version")
    if record["execution_mode"] not in EXECUTION_MODES:
        raise ValueError("invalid execution_mode")
    if record["delivery_profile"] not in DELIVERY_PROFILES:
        raise ValueError("invalid delivery_profile")
    if record["native_media_status"] not in NATIVE_MEDIA_STATUSES:
        raise ValueError("invalid native_media_status")
    if record["durable_audit_status"] not in DURABLE_AUDIT_STATUSES:
        raise ValueError("invalid durable_audit_status")
    limitations = record["capability_limitations"]
    if (
        not isinstance(limitations, list)
        or len(limitations) != len(set(limitations))
        or any(item not in KNOWN_CAPABILITY_LIMITATIONS for item in limitations)
    ):
        raise ValueError("invalid capability_limitations")
    degraded = record["delivery_profile"] == "reader-canonical-capability-degraded"
    if degraded and (
        record["execution_mode"] != "mobile-native"
        or record["native_media_status"] != "unavailable"
        or "NATIVE_MEDIA_UNAVAILABLE" not in limitations
    ):
        raise ValueError("capability-degraded delivery requires mobile-native NATIVE_MEDIA_UNAVAILABLE")
    if not degraded and "NATIVE_MEDIA_UNAVAILABLE" in limitations:
        raise ValueError("NATIVE_MEDIA_UNAVAILABLE requires the capability-degraded delivery profile")
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
    if record["execution_mode"] == "mobile-native":
        if record["stage_index"] >= STAGE_INDEX["selection-verified"]:
            _require_run_artifact(
                record,
                "candidate_audit_artifact",
                "candidate-audit.json",
                "candidate audit artifact",
            )
        if record["stage_index"] >= STAGE_INDEX["visuals-completed"]:
            _require_run_artifact(record, "verification_artifact", "verification.json", "verification artifact")
        if record["stage_index"] >= STAGE_INDEX["reader-rendered"]:
            _require_run_artifact(record, "map_decisions_artifact", "map-decisions.json", "map decisions artifact")
            _require_run_artifact(
                record,
                "image_evidence_artifact",
                "image-evidence.json",
                "image evidence artifact",
            )
        if record["stage_index"] >= STAGE_INDEX["github-result-saved"]:
            _require_artifact(
                record,
                "reader_artifact",
                "logs/latest-reader.md",
                "reader artifact",
            )
    if record["status"] == "completed":
        if record.get("reader_artifact") is None or record.get("candidate_audit_artifact") is None:
            raise ValueError("completed requires saved reader and candidate-audit artifacts")
        expected_audit_path = f"logs/runs/{record['run_id']}/candidate-audit.json"
        actual_audit_path = record["candidate_audit_artifact"].get("path")
        if actual_audit_path != expected_audit_path:
            raise ValueError("completed requires a run-scoped candidate audit")
        if degraded and record.get("last_error") is not None:
            raise ValueError("a capability limitation is not a last_error")
        if degraded:
            evidence = record.get("image_evidence_artifact")
            expected_evidence_path = f"logs/runs/{record['run_id']}/image-evidence.json"
            if not isinstance(evidence, dict) or evidence.get("path") != expected_evidence_path:
                raise ValueError("capability-degraded completion requires run-scoped image evidence")
    durable_artifact = record.get("durable_audit_artifact")
    if record["durable_audit_status"] in {"updated", "preserved_merge_deferred"}:
        if not isinstance(durable_artifact, dict) or durable_artifact.get("path") != "logs/latest-candidate-audit.json":
            raise ValueError("durable audit status requires logs/latest-candidate-audit.json evidence")


def _require_run_artifact(
    record: dict[str, Any], field: str, filename: str, label: str
) -> None:
    expected_path = f"logs/runs/{record['run_id']}/{filename}"
    _require_artifact(record, field, expected_path, label)


def _require_artifact(
    record: dict[str, Any], field: str, expected_path: str, label: str
) -> None:
    artifact = record.get(field)
    if not isinstance(artifact, dict) or artifact.get("branch") != "run-logs":
        raise ValueError(f"mobile stage requires {label}")
    blob_sha = artifact.get("blob_sha")
    if artifact.get("path") != expected_path or not isinstance(blob_sha, str):
        raise ValueError(f"mobile stage requires {label}")
    if len(blob_sha) != 40 or any(character not in "0123456789abcdef" for character in blob_sha):
        raise ValueError(f"mobile stage requires Git blob binding for {label}")


def prepare_run(
    ledger_dir: Path | str,
    *,
    run_id: str,
    scheduled_for: str,
    updated_at: str,
    execution_mode: str = "full-runtime",
    delivery_profile: str = "full-assets",
    native_media_status: str = "available",
    capability_limitations: list[str] | None = None,
) -> dict[str, Any]:
    ledger_dir = Path(ledger_dir)
    current_path = ledger_dir / "current.json"
    previous_path = ledger_dir / "previous.json"

    if current_path.exists():
        previous = _read_json(current_path)
        validate_record(previous)
        try:
            incoming_occurrence = datetime.fromisoformat(scheduled_for)
            current_occurrence = datetime.fromisoformat(previous["scheduled_for"])
            if incoming_occurrence == current_occurrence:
                return previous
            if incoming_occurrence < current_occurrence:
                raise ValueError("cannot replace current.json with an older scheduled occurrence")
        except TypeError as error:
            raise ValueError("scheduled_for values must use comparable ISO timestamps") from error
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
        "execution_mode": execution_mode,
        "delivery_profile": delivery_profile,
        "native_media_status": native_media_status,
        "capability_limitations": list(capability_limitations or []),
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
        "candidate_audit_artifact": None,
        "verification_artifact": None,
        "map_decisions_artifact": None,
        "image_evidence_artifact": None,
        "durable_audit_status": "not_started",
        "durable_audit_artifact": None,
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
    execution_mode: str | None = None,
    delivery_profile: str | None = None,
    native_media_status: str | None = None,
    capability_limitations: list[str] | None = None,
    candidate_audit_artifact: dict[str, str] | None = None,
    verification_artifact: dict[str, str] | None = None,
    map_decisions_artifact: dict[str, str] | None = None,
    image_evidence_artifact: dict[str, str] | None = None,
    durable_audit_status: str | None = None,
    durable_audit_artifact: dict[str, str] | None = None,
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
    if STAGE_INDEX[stage] > current["stage_index"] + 1:
        raise ValueError(
            f"stage skip: {current['current_stage']} -> {stage}"
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
    if execution_mode is not None:
        current["execution_mode"] = execution_mode
    if delivery_profile is not None:
        current["delivery_profile"] = delivery_profile
    if native_media_status is not None:
        current["native_media_status"] = native_media_status
    if capability_limitations is not None:
        current["capability_limitations"] = list(capability_limitations)
    if candidate_audit_artifact is not None:
        current["candidate_audit_artifact"] = candidate_audit_artifact
    if verification_artifact is not None:
        current["verification_artifact"] = verification_artifact
    if map_decisions_artifact is not None:
        current["map_decisions_artifact"] = map_decisions_artifact
    if image_evidence_artifact is not None:
        current["image_evidence_artifact"] = image_evidence_artifact
    if durable_audit_status is not None:
        current["durable_audit_status"] = durable_audit_status
    if durable_audit_artifact is not None:
        current["durable_audit_artifact"] = durable_audit_artifact
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
    prepare.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES), default="full-runtime")
    prepare.add_argument("--delivery-profile", choices=sorted(DELIVERY_PROFILES), default="full-assets")
    prepare.add_argument("--native-media-status", choices=sorted(NATIVE_MEDIA_STATUSES), default="available")
    prepare.add_argument("--capability-limitation", action="append", choices=sorted(KNOWN_CAPABILITY_LIMITATIONS), default=[])

    advance = subparsers.add_parser("advance")
    advance.add_argument("--ledger-dir", type=Path, required=True)
    advance.add_argument("--run-id", required=True)
    advance.add_argument("--stage", choices=STAGES, required=True)
    advance.add_argument("--updated-at", required=True)
    advance.add_argument("--status", choices=sorted(STATUSES), default="running")
    advance.add_argument("--delivery-status", choices=sorted(DELIVERY_STATUSES))
    advance.add_argument("--client-ack", action="store_true")
    advance.add_argument("--main-sha")
    advance.add_argument("--reader-artifact", type=Path)
    advance.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES))
    advance.add_argument("--delivery-profile", choices=sorted(DELIVERY_PROFILES))
    advance.add_argument("--native-media-status", choices=sorted(NATIVE_MEDIA_STATUSES))
    advance.add_argument("--capability-limitation", action="append", choices=sorted(KNOWN_CAPABILITY_LIMITATIONS))
    advance.add_argument("--candidate-audit-artifact", type=Path)
    advance.add_argument("--verification-artifact", type=Path)
    advance.add_argument("--map-decisions-artifact", type=Path)
    advance.add_argument("--image-evidence-artifact", type=Path)
    advance.add_argument("--durable-audit-status", choices=sorted(DURABLE_AUDIT_STATUSES))
    advance.add_argument("--durable-audit-artifact", type=Path)

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
            execution_mode=args.execution_mode,
            delivery_profile=args.delivery_profile,
            native_media_status=args.native_media_status,
            capability_limitations=args.capability_limitation,
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
            reader_artifact=(
                _read_artifact_reference(args.reader_artifact)
                if args.reader_artifact else None
            ),
            execution_mode=args.execution_mode,
            delivery_profile=args.delivery_profile,
            native_media_status=args.native_media_status,
            capability_limitations=args.capability_limitation,
            candidate_audit_artifact=(
                _read_artifact_reference(args.candidate_audit_artifact)
                if args.candidate_audit_artifact else None
            ),
            verification_artifact=(
                _read_artifact_reference(args.verification_artifact)
                if args.verification_artifact else None
            ),
            map_decisions_artifact=(
                _read_artifact_reference(args.map_decisions_artifact)
                if args.map_decisions_artifact else None
            ),
            image_evidence_artifact=(
                _read_artifact_reference(args.image_evidence_artifact)
                if args.image_evidence_artifact else None
            ),
            durable_audit_status=args.durable_audit_status,
            durable_audit_artifact=(
                _read_artifact_reference(args.durable_audit_artifact)
                if args.durable_audit_artifact else None
            ),
        )
    else:
        result = _read_json(args.input)
        validate_record(result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

