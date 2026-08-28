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
import mobile_gate_assertions


SCHEMA_VERSION = "1.7.0"
EXECUTION_MODES = {"full-runtime", "mobile-native"}
DELIVERY_PROFILES = {"full-assets", "reader-canonical-capability-degraded"}
NATIVE_MEDIA_STATUSES = {"available", "unavailable"}
KNOWN_CAPABILITY_LIMITATIONS = {"NATIVE_MEDIA_UNAVAILABLE"}
IMAGE_FALLBACK_ATTEMPT_FIELDS = (
    "original_source_attempted",
    "official_fallback_attempted",
    "wire_fallback_attempted",
    "reliable_media_fallback_attempted",
)
IMAGE_DELIVERY_RESULTS = {
    "delivered",
    "delivery_unavailable",
    "source_exhausted",
}
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
        "window",
        "updated_at",
        "last_error",
        "delivery_status",
        "client_confirmation_supported",
        "reader_artifact",
        "candidate_audit_artifact",
        "verification_artifact",
        "map_decisions_artifact",
        "image_evidence_artifact",
        "gate_assertions_artifact",
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
    if record["stage_index"] < STAGE_INDEX["main-pinned"]:
        if record["main_sha"] is not None:
            raise ValueError("main_sha belongs to main-pinned stage")
    elif record["main_sha"] is None:
        raise ValueError("main-pinned and later stages require main_sha")
    if record["stage_index"] < STAGE_INDEX["executor-started"]:
        if record["window"] is not None:
            raise ValueError("window belongs to executor-started stage")
    elif record["window"] is None:
        raise ValueError("executor-started and later stages require window")
    else:
        _validate_window(record["window"], "run")
    if "NATIVE_MEDIA_UNAVAILABLE" in limitations and (
        record["current_stage"] != "visuals-completed"
        or record["status"] != "running"
    ):
        raise ValueError(
            "NATIVE_MEDIA_UNAVAILABLE requires running visuals-completed recovery"
        )
    if "NATIVE_MEDIA_UNAVAILABLE" in limitations and record.get(
        "image_evidence_artifact"
    ) is None:
        raise ValueError(
            "NATIVE_MEDIA_UNAVAILABLE requires run-scoped image evidence"
        )
    if record["last_completed_stage"] not in (None, *STAGES):
        raise ValueError("invalid last_completed_stage")
    if record["delivery_status"] not in DELIVERY_STATUSES:
        raise ValueError("invalid delivery_status")
    if record["delivery_status"] == "client_confirmed" and not record.get(
        "client_confirmation_supported"
    ):
        raise ValueError("client delivery cannot be confirmed without an external acknowledgement")
    future_artifact_boundaries = (
        ("candidate_audit_artifact", "candidate-audit", "candidate audit artifact"),
        ("verification_artifact", "selection-verified", "verification artifact"),
        ("map_decisions_artifact", "visuals-completed", "map decisions artifact"),
        ("image_evidence_artifact", "visuals-completed", "image evidence artifact"),
        ("reader_artifact", "reader-rendered", "reader artifact"),
        ("gate_assertions_artifact", "github-result-saved", "gate assertions artifact"),
    )
    for field, first_stage, label in future_artifact_boundaries:
        if record["stage_index"] < STAGE_INDEX[first_stage] and record.get(field) is not None:
            raise ValueError(f"{label} belongs to a future stage")
    for field, _, label in future_artifact_boundaries:
        if record.get(field) is not None:
            _validate_artifact_identity(record, field, label)
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
            _require_run_artifact(
                record,
                "gate_assertions_artifact",
                "gate-assertions.json",
                "gate assertions artifact",
            )
    if record["status"] == "completed":
        if record.get("reader_artifact") is None or record.get("candidate_audit_artifact") is None:
            raise ValueError("completed requires saved reader and candidate-audit artifacts")
        expected_audit_path = f"logs/runs/{record['run_id']}/candidate-audit.json"
        actual_audit_path = record["candidate_audit_artifact"].get("path")
        if actual_audit_path != expected_audit_path:
            raise ValueError("completed requires a run-scoped candidate audit")
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


def _validate_artifact_identity(record: dict[str, Any], field: str, label: str) -> None:
    artifact = record[field]
    if artifact.get("run_id") != record["run_id"]:
        raise ValueError(f"{label} artifact run_id does not match current run")
    if artifact.get("main_sha") != record["main_sha"]:
        raise ValueError(f"{label} artifact main_sha does not match pinned main")
    window = artifact.get("window")
    _validate_window(window, f"{label} artifact")
    if window != record["window"]:
        raise ValueError(f"{label} artifact window does not match ledger")


def _bound_artifact_path(
    ledger_dir: Path, artifact: dict[str, Any], label: str
) -> Path:
    root = ledger_dir.parent if ledger_dir.name == "logs" else ledger_dir
    root = root.resolve()
    path = (root / str(artifact.get("path", ""))).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"{label} path escapes the run-logs checkout")
    return path


def _validate_bound_image_evidence(
    ledger_dir: Path | str, record: dict[str, Any]
) -> None:
    if record.get("execution_mode") != "mobile-native":
        return
    artifact = record.get("image_evidence_artifact")
    if not isinstance(artifact, dict):
        return
    path = _bound_artifact_path(Path(ledger_dir), artifact, "image evidence")
    if not path.is_file():
        raise ValueError("bound image evidence file is missing")
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("bound image evidence is not readable JSON") from error
    events = evidence.get("events") if isinstance(evidence, dict) else None
    if not isinstance(events, list):
        raise ValueError("bound image evidence must contain event checklists")

    audit_artifact = record.get("candidate_audit_artifact")
    if not isinstance(audit_artifact, dict):
        raise ValueError("bound image evidence requires candidate audit")
    audit_path = _bound_artifact_path(
        Path(ledger_dir), audit_artifact, "candidate audit"
    )
    if not audit_path.is_file():
        raise ValueError("bound candidate audit file is missing")
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("bound candidate audit is not readable JSON") from error
    matching_runs = [
        run
        for run in audit.get("runs", [])
        if isinstance(run, dict) and run.get("run_id") == record["run_id"]
    ] if isinstance(audit, dict) else []
    if len(matching_runs) != 1 or not isinstance(
        matching_runs[0].get("candidates"), list
    ):
        raise ValueError("bound candidate audit must contain the current run")
    selected_event_ids: list[str] = []
    for candidate in matching_runs[0]["candidates"]:
        if not isinstance(candidate, dict) or candidate.get("decision") != "selected":
            continue
        selected_event_id = candidate.get("selected_event_id")
        if not isinstance(selected_event_id, str) or not selected_event_id.strip():
            raise ValueError("selected candidate requires selected_event_id")
        selected_event_ids.append(selected_event_id)
    if len(selected_event_ids) != len(set(selected_event_ids)):
        raise ValueError("bound candidate audit contains duplicate selected_event_id values")

    unavailable_events = 0
    event_ids: list[str] = []
    for index, event in enumerate(events, 1):
        label = f"image evidence event[{index}]"
        if not isinstance(event, dict):
            raise ValueError(f"{label} must be an object")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError(f"{label} requires event_id")
        event_ids.append(event_id)
        for field in (
            *IMAGE_FALLBACK_ATTEMPT_FIELDS,
            "direct_media_url_attempted",
            "qualified_image_found",
            "delivery_attempted",
        ):
            if not isinstance(event.get(field), bool):
                raise ValueError(f"{label}.{field} must be boolean")
        result = event.get("delivery_result")
        if result not in IMAGE_DELIVERY_RESULTS:
            raise ValueError(f"{label}.delivery_result is invalid")
        if event["original_source_attempted"] is not True:
            raise ValueError(f"{label} requires original source inspection")

        fallback_exhausted = all(
            event[field] is True for field in IMAGE_FALLBACK_ATTEMPT_FIELDS
        )
        if (
            result in {"delivery_unavailable", "source_exhausted"}
            and event["direct_media_url_attempted"] is not True
        ):
            raise ValueError(
                f"{label} requires direct media URL attempt before exhaustion"
            )
        if result in {"delivery_unavailable", "source_exhausted"} and not fallback_exhausted:
            raise ValueError(
                f"{label} requires four-tier image fallback exhaustion"
            )
        if result == "delivered":
            if not event["qualified_image_found"] or not event["delivery_attempted"]:
                raise ValueError(f"{label} delivered result requires a qualified image and delivery attempt")
        elif result == "delivery_unavailable":
            unavailable_events += 1
            if not event["qualified_image_found"] or not event["delivery_attempted"]:
                raise ValueError(f"{label} unavailable result requires a qualified image and delivery attempt")
        elif event["qualified_image_found"] or event["delivery_attempted"]:
            raise ValueError(f"{label} source exhaustion forbids a found image or delivery attempt")

    if len(event_ids) != len(set(event_ids)):
        raise ValueError("bound image evidence contains duplicate event_id values")
    if set(event_ids) != set(selected_event_ids):
        raise ValueError(
            "bound image evidence event set does not match selected event set"
        )
    limitations = set(record.get("capability_limitations") or [])
    if unavailable_events and "NATIVE_MEDIA_UNAVAILABLE" not in limitations:
        raise ValueError("undelivered qualified images require NATIVE_MEDIA_UNAVAILABLE")
    if not unavailable_events and "NATIVE_MEDIA_UNAVAILABLE" in limitations:
        raise ValueError("NATIVE_MEDIA_UNAVAILABLE requires an undelivered qualified image")


def _artifact_identity(artifact: dict[str, Any]) -> str:
    return f"{artifact['path']}@{artifact['blob_sha']}"


def _validate_bound_gate_assertions(ledger_dir: Path | str, record: dict[str, Any]) -> None:
    if record.get("execution_mode") != "mobile-native":
        return
    artifact = record.get("gate_assertions_artifact")
    if not isinstance(artifact, dict):
        return
    path = _bound_artifact_path(Path(ledger_dir), artifact, "gate assertions")
    if not path.is_file():
        raise ValueError("bound gate assertions file is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("bound gate assertions are not readable JSON") from error
    fields = (
        "candidate_audit_artifact", "verification_artifact", "map_decisions_artifact",
        "image_evidence_artifact", "reader_artifact",
    )
    artifacts = [record.get(field) for field in fields]
    if any(not isinstance(item, dict) for item in artifacts):
        raise ValueError("gate assertions require all publication evidence artifacts")
    allowed = {_artifact_identity(item) for item in artifacts}
    mobile_gate_assertions.validate_gate_assertions(
        value,
        record=record,
        allowed_evidence_refs=allowed,
        image_identity=_artifact_identity(record["image_evidence_artifact"]),
        reader_identity=_artifact_identity(record["reader_artifact"]),
    )


def _validate_window(window: Any, label: str) -> None:
    if (
        not isinstance(window, dict)
        or set(window) != {"start", "end", "timezone"}
        or any(not isinstance(window[key], str) or not window[key] for key in window)
    ):
        raise ValueError(f"{label} window identity is invalid")
    try:
        start = datetime.fromisoformat(window["start"])
        end = datetime.fromisoformat(window["end"])
    except ValueError as error:
        raise ValueError(f"{label} window timestamps must use ISO format") from error
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError(f"{label} window timestamps must include time zones")
    if (end - start).total_seconds() != 24 * 60 * 60:
        raise ValueError(f"{label} window must span exactly 24 hours")




def prepare_run(
    ledger_dir: Path | str,
    *,
    run_id: str,
    scheduled_for: str,
    updated_at: str,
    execution_mode: str,
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
        "window": None,
        "updated_at": updated_at,
        "last_error": None,
        "delivery_status": "not_ready",
        "client_confirmation_supported": False,
        "reader_artifact": None,
        "candidate_audit_artifact": None,
        "verification_artifact": None,
        "map_decisions_artifact": None,
        "image_evidence_artifact": None,
        "gate_assertions_artifact": None,
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
    window: dict[str, str] | None = None,
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
    gate_assertions_artifact: dict[str, str] | None = None,
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

    first_executor_start = (
        current["current_stage"] == "schedule-prepared"
        and stage == "executor-started"
    )
    if first_executor_start and window is not None:
        _validate_window(window, "run")
        try:
            executor_started_at = datetime.fromisoformat(updated_at)
        except ValueError as error:
            raise ValueError(
                "executor-started updated_at must use an ISO timestamp"
            ) from error
        if executor_started_at.tzinfo is None:
            raise ValueError("executor-started updated_at must include a time zone")
        window_end = datetime.fromisoformat(window["end"])
        if window_end != executor_started_at:
            raise ValueError("window end must match executor-started updated_at")

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
        if current["main_sha"] is not None and current["main_sha"] != main_sha:
            raise ValueError(
                "main_sha is immutable for the same scheduled occurrence"
            )
        current["main_sha"] = main_sha
    if window is not None:
        if current["window"] is not None and current["window"] != window:
            raise ValueError("window is immutable for the same scheduled occurrence")
        current["window"] = dict(window)
    if reader_artifact is not None:
        current["reader_artifact"] = reader_artifact
    if execution_mode is not None and execution_mode != current["execution_mode"]:
        raise ValueError(
            "execution_mode is immutable for the same scheduled occurrence"
        )
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
    if gate_assertions_artifact is not None:
        current["gate_assertions_artifact"] = gate_assertions_artifact
    if durable_audit_status is not None:
        current["durable_audit_status"] = durable_audit_status
    if durable_audit_artifact is not None:
        current["durable_audit_artifact"] = durable_audit_artifact
    current["last_error"] = last_error
    validate_record(current)
    if (
        current.get("image_evidence_artifact") is not None
        and (
            current["stage_index"] >= STAGE_INDEX["reader-rendered"]
            or "NATIVE_MEDIA_UNAVAILABLE" in current["capability_limitations"]
        )
    ):
        _validate_bound_image_evidence(ledger_dir, current)
    if (
        current.get("gate_assertions_artifact") is not None
        and current["stage_index"] >= STAGE_INDEX["github-result-saved"]
    ):
        _validate_bound_gate_assertions(ledger_dir, current)
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
    prepare.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES), required=True)
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
    advance.add_argument("--window-start")
    advance.add_argument("--window-end")
    advance.add_argument("--window-timezone")
    advance.add_argument("--reader-artifact", type=Path)
    advance.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES))
    advance.add_argument("--delivery-profile", choices=sorted(DELIVERY_PROFILES))
    advance.add_argument("--native-media-status", choices=sorted(NATIVE_MEDIA_STATUSES))
    advance.add_argument("--capability-limitation", action="append", choices=sorted(KNOWN_CAPABILITY_LIMITATIONS))
    advance.add_argument("--candidate-audit-artifact", type=Path)
    advance.add_argument("--verification-artifact", type=Path)
    advance.add_argument("--map-decisions-artifact", type=Path)
    advance.add_argument("--image-evidence-artifact", type=Path)
    advance.add_argument("--gate-assertions-artifact", type=Path)
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
        window_values = (args.window_start, args.window_end, args.window_timezone)
        if any(window_values) and not all(window_values):
            raise ValueError(
                "--window-start, --window-end, and --window-timezone must be supplied together"
            )
        window = (
            {
                "start": args.window_start,
                "end": args.window_end,
                "timezone": args.window_timezone,
            }
            if all(window_values)
            else None
        )
        result = advance_run(
            args.ledger_dir,
            run_id=args.run_id,
            stage=args.stage,
            updated_at=args.updated_at,
            status=args.status,
            delivery_status=args.delivery_status,
            client_ack=args.client_ack,
            main_sha=args.main_sha,
            window=window,
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
            gate_assertions_artifact=(
                _read_artifact_reference(args.gate_assertions_artifact)
                if args.gate_assertions_artifact else None
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
        if (
            result.get("image_evidence_artifact") is not None
            and (
                result["stage_index"] >= STAGE_INDEX["reader-rendered"]
                or "NATIVE_MEDIA_UNAVAILABLE" in result["capability_limitations"]
            )
        ):
            _validate_bound_image_evidence(args.input.parent, result)
        if (
            result.get("gate_assertions_artifact") is not None
            and result["stage_index"] >= STAGE_INDEX["github-result-saved"]
        ):
            _validate_bound_gate_assertions(args.input.parent, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

