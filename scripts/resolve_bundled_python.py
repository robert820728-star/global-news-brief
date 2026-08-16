#!/usr/bin/env python3
"""Resolve and verify the host's bundled Python without using PATH as runtime."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping


ENV_PYTHON_KEYS = (
    "CODEX_BUNDLED_PYTHON",
    "CODEX_PRIMARY_RUNTIME_PYTHON",
)
ENV_RUNTIME_KEYS = (
    "CODEX_BUNDLED_RUNTIME",
    "CODEX_BUNDLED_RUNTIME_PATH",
    "CODEX_PRIMARY_RUNTIME",
)
PROBE_CODE = (
    "import json, sys; import PIL; from PIL import Image; "
    "print(json.dumps({'executable': sys.executable, 'pillow': PIL.__version__}))"
)


def expand_candidate(path: Path) -> list[Path]:
    if path.is_file() or path.suffix.lower() in {".exe", ".com"} or path.name.startswith("python"):
        return [path]
    return [
        path / "dependencies/python/python.exe",
        path / "dependencies/python/bin/python3",
        path / "dependencies/python/bin/python",
        path / "dependencies/python/python3",
        path / "dependencies/python/python",
        path / "python/python.exe",
        path / "bin/python3",
        path / "bin/python",
    ]


def platform_defaults(home: Path) -> list[Path]:
    runtime = home / ".cache/codex-runtimes/codex-primary-runtime"
    return expand_candidate(runtime)


def candidate_paths(
    preferred: str = "",
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    only_preferred: bool = False,
) -> list[tuple[str, Path]]:
    environ = environ or os.environ
    candidates: list[tuple[str, Path]] = []
    if preferred.strip():
        candidates.extend(("preferred", item) for item in expand_candidate(Path(preferred)))
    if not only_preferred:
        for key in ENV_PYTHON_KEYS:
            value = environ.get(key, "").strip()
            if value:
                candidates.extend((key, item) for item in expand_candidate(Path(value)))
        for key in ENV_RUNTIME_KEYS:
            value = environ.get(key, "").strip()
            if value:
                candidates.extend((key, item) for item in expand_candidate(Path(value)))
        candidates.extend(("platform-default", item) for item in platform_defaults(home or Path.home()))

    unique: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for source, path in candidates:
        resolved = path.expanduser().resolve(strict=False)
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append((source, resolved))
    return unique


def probe_python(path: Path, timeout_seconds: int = 15) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, f"bundled Python does not exist: {path}"
    try:
        completed = subprocess.run(
            [str(path), "-c", PROBE_CODE],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return None, f"bundled Python dependency probe failed for {path}: {error}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        return None, f"bundled Python dependency probe failed for {path}: {detail}"
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return None, f"bundled Python dependency probe failed for {path}: invalid JSON: {error}"
    if not result.get("pillow"):
        return None, f"bundled Python dependency probe failed for {path}: Pillow version missing"
    return result, None


def resolve(candidates: Iterable[tuple[str, Path]]) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    for source, path in candidates:
        result, error = probe_python(path)
        if result is not None:
            return {
                "status": "ready",
                "python": str(path),
                "pillow": str(result["pillow"]),
                "source": source,
            }, errors
        if error:
            errors.append(error)
    return None, errors


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--preferred-python", default="")
    parser.add_argument("--only-preferred", action="store_true")
    args = parser.parse_args()
    candidates = candidate_paths(
        preferred=args.preferred_python,
        only_preferred=args.only_preferred,
    )
    result, errors = resolve(candidates)
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 3
    print("no bundled Python candidates were provided or discovered", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
