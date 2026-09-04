#!/usr/bin/env python3
"""Build an immutable canonical Scheduled Task prompt and install-only sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


REGION_PLACEHOLDER = "區域：<使用者指定區域；未指定則台灣、中國、世界>"
MONITOR_PLACEHOLDER = "監控類型：<使用者指定監控類型；未指定則預設>"
ALLOWED_EXTENSION_KEYS = {
    "schema_version",
    "scope",
    "saved_prompt_mutation_allowed",
    "one_time_delay_minutes",
    "smoke_fixture",
}
ALLOWED_SMOKE_KEYS = {
    "source_media_url",
    "source_page_url",
    "expected_byte_size",
    "expected_width",
    "expected_height",
    "expected_sha256",
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}-", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
        os.replace(temp_path, path)
    except OSError:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _write_json_atomic(path: Path, value: Any) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _write_bytes_atomic(path, payload)


def _replace_one_line(text: str, placeholder: str, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == placeholder]
    if len(matches) != 1:
        raise ValueError(f"placeholder must appear exactly once: {placeholder}")
    index = matches[0]
    newline = lines[index][len(lines[index].rstrip("\r\n")) :]
    lines[index] = replacement + newline
    return "".join(lines)


def _validate_extension(extension: Any) -> dict[str, Any]:
    if not isinstance(extension, dict):
        raise ValueError("test extension must be a JSON object")
    unknown = set(extension) - ALLOWED_EXTENSION_KEYS
    if unknown:
        raise ValueError(f"unknown test extension keys: {sorted(unknown)}")
    if extension.get("schema_version") != "1.0":
        raise ValueError("test extension schema_version must be 1.0")
    if extension.get("scope") != "installation_only":
        raise ValueError("test extension scope must be installation_only")
    if extension.get("saved_prompt_mutation_allowed") is not False:
        raise ValueError("test extension must prohibit saved prompt mutation")
    delay = extension.get("one_time_delay_minutes")
    if not isinstance(delay, int) or isinstance(delay, bool) or not 1 <= delay <= 60:
        raise ValueError("one_time_delay_minutes must be an integer from 1 to 60")
    fixture = extension.get("smoke_fixture")
    if not isinstance(fixture, dict):
        raise ValueError("smoke_fixture must be a JSON object")
    fixture_unknown = set(fixture) - ALLOWED_SMOKE_KEYS
    if fixture_unknown:
        raise ValueError(f"unknown smoke fixture keys: {sorted(fixture_unknown)}")
    if set(fixture) != ALLOWED_SMOKE_KEYS:
        raise ValueError("smoke_fixture must contain every required integrity field")
    for key in ("source_media_url", "source_page_url"):
        if not str(fixture.get(key, "")).startswith(("http://", "https://")):
            raise ValueError(f"{key} must be an absolute HTTP(S) URL")
    for key in ("expected_byte_size", "expected_width", "expected_height"):
        value = fixture.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{key} must be a positive integer")
    if not re.fullmatch(r"[0-9a-f]{64}", str(fixture.get("expected_sha256", ""))):
        raise ValueError("expected_sha256 must be a lowercase SHA-256")
    return extension


def build_payload(
    *,
    template_path: Path,
    output_dir: Path,
    region: str,
    monitor_type: str,
    main_sha: str,
    extension_path: Path | None = None,
) -> dict[str, Any]:
    """Create the canonical saved prompt, optional sidecar, and integrity receipt."""
    if not re.fullmatch(r"[0-9a-f]{40}", main_sha):
        raise ValueError("main_sha must be a lowercase 40-character Git SHA")
    if not region.strip() or "\n" in region or "\r" in region:
        raise ValueError("region must be one non-empty line")
    if not monitor_type.strip() or "\n" in monitor_type or "\r" in monitor_type:
        raise ValueError("monitor_type must be one non-empty line")

    template_bytes = template_path.read_bytes()
    template_text = template_bytes.decode("utf-8")
    saved_text = _replace_one_line(
        template_text, REGION_PLACEHOLDER, f"區域：{region.strip()}"
    )
    saved_text = _replace_one_line(
        saved_text, MONITOR_PLACEHOLDER, f"監控類型：{monitor_type.strip()}"
    )
    saved_bytes = saved_text.encode("utf-8")

    extension = None
    if extension_path is not None:
        extension = _validate_extension(
            json.loads(extension_path.read_text(encoding="utf-8"))
        )

    saved_path = output_dir / "saved-prompt.txt"
    receipt_path = output_dir / "install-receipt.json"
    emitted_extension_path = output_dir / "install-extension.json"
    receipt = {
        "schema_version": "1.0",
        "resolved_main_sha": main_sha,
        "template_path": str(template_path.resolve()),
        "template_byte_size": len(template_bytes),
        "template_sha256": _sha256(template_bytes),
        "saved_prompt_byte_size": len(saved_bytes),
        "saved_prompt_character_count": len(saved_text),
        "saved_prompt_sha256": _sha256(saved_bytes),
        "saved_prompt_lf_normalized_sha256": _sha256(
            saved_text.replace("\r\n", "\n").encode("utf-8")
        ),
        "authorized_substitution_count": 2,
        "region": region.strip(),
        "monitor_type": monitor_type.strip(),
        "extension_present": extension is not None,
        "extension_embedded_in_saved_prompt": False,
    }

    _write_bytes_atomic(saved_path, saved_bytes)
    if extension is not None:
        _write_json_atomic(emitted_extension_path, extension)
    _write_json_atomic(receipt_path, receipt)
    return {
        "saved_prompt_path": str(saved_path.resolve()),
        "receipt_path": str(receipt_path.resolve()),
        "extension_path": str(emitted_extension_path.resolve()) if extension else None,
        "receipt": receipt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--region", required=True)
    parser.add_argument("--monitor-type", required=True)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--test-extension", type=Path)
    args = parser.parse_args()
    result = build_payload(
        template_path=args.template,
        output_dir=args.output_dir,
        region=args.region,
        monitor_type=args.monitor_type,
        main_sha=args.main_sha,
        extension_path=args.test_extension,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
