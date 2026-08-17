#!/usr/bin/env python3
"""Generate and validate canonical daily-news run identifiers."""

from __future__ import annotations

import argparse
import re
import secrets
from datetime import datetime, timezone


RUN_ID_PATTERN = re.compile(r"^gnb-\d{8}T\d{6}Z-[0-9a-f]{8}$")


def is_valid_run_id(value: object) -> bool:
    return isinstance(value, str) and RUN_ID_PATTERN.fullmatch(value) is not None


def generate_run_id(now: datetime | None = None, *, suffix: str | None = None) -> str:
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("run id timestamp must be timezone-aware")
    token = suffix or secrets.token_hex(4)
    if re.fullmatch(r"[0-9a-f]{8}", token) is None:
        raise ValueError("run id suffix must be eight lowercase hexadecimal characters")
    timestamp = instant.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"gnb-{timestamp}-{token}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate",))
    args = parser.parse_args(argv)
    if args.command == "generate":
        print(generate_run_id())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
