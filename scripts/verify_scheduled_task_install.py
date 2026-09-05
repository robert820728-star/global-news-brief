#!/usr/bin/env python3
"""Verify canonical Scheduled Task outbound bytes and optional exact-ID readback."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.build_scheduled_task_install_payload import (
    MONITOR_PLACEHOLDER,
    REGION_PLACEHOLDER,
    _replace_one_line,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalized_text(payload: bytes) -> str:
    return payload.decode("utf-8").replace("\r\n", "\n").rstrip("\n")


def verify_install(
    *,
    template_path: Path,
    saved_prompt_path: Path,
    receipt_path: Path,
    expected_main_sha: str,
    readback_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        template_bytes = template_path.read_bytes()
        saved_bytes = saved_prompt_path.read_bytes()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"verified": False, "readback_verified": False, "errors": [str(exc)]}

    if receipt.get("resolved_main_sha") != expected_main_sha:
        errors.append("receipt main SHA does not match expected main SHA")
    if receipt.get("template_sha256") != _sha256(template_bytes):
        errors.append("template hash does not match receipt")
    if receipt.get("template_byte_size") != len(template_bytes):
        errors.append("template byte size does not match receipt")

    try:
        expected_text = template_bytes.decode("utf-8")
        expected_text = _replace_one_line(
            expected_text, REGION_PLACEHOLDER, f"區域：{receipt['region']}"
        )
        expected_text = _replace_one_line(
            expected_text, MONITOR_PLACEHOLDER, f"監控類型：{receipt['monitor_type']}"
        )
        expected_bytes = expected_text.encode("utf-8")
    except (UnicodeDecodeError, KeyError, ValueError) as exc:
        errors.append(f"cannot reconstruct canonical saved prompt: {exc}")
        expected_bytes = b""

    if saved_bytes != expected_bytes:
        errors.append("saved prompt is not the exact canonical template after two substitutions")
    if receipt.get("saved_prompt_sha256") != _sha256(saved_bytes):
        errors.append("saved prompt hash does not match receipt")
    if receipt.get("saved_prompt_byte_size") != len(saved_bytes):
        errors.append("saved prompt byte size does not match receipt")
    if receipt.get("authorized_substitution_count") != 2:
        errors.append("authorized substitution count is not two")
    if receipt.get("extension_embedded_in_saved_prompt") is not False:
        errors.append("install extension is marked as embedded in saved prompt")

    readback_verified = False
    if readback_path is not None:
        try:
            readback_verified = _normalized_text(readback_path.read_bytes()) == _normalized_text(saved_bytes)
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot read exact-ID readback: {exc}")
        if not readback_verified:
            errors.append("exact-ID readback does not match saved prompt")

    return {
        "verified": not errors,
        "readback_verified": readback_verified if readback_path is not None else None,
        "saved_prompt_sha256": _sha256(saved_bytes),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--saved-prompt", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--readback", type=Path)
    args = parser.parse_args()
    report = verify_install(
        template_path=args.template,
        saved_prompt_path=args.saved_prompt,
        receipt_path=args.receipt,
        expected_main_sha=args.expected_main_sha,
        readback_path=args.readback,
    )
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
