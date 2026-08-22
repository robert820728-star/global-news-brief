#!/usr/bin/env python3
"""Download and materialize selected-news images for native media delivery."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_EDGE = 640
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 15
USER_AGENT = "global-news-brief-image-materializer/1.0"


def _safe_event_id(event_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", event_id.strip()).strip(".-")
    return safe or "event"


def _failed_record(
    *, event_id: str, source_url: str, source_page_url: str = "", alt: str, credit: str, error: str
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "source_url": source_url,
        "source_image_url": source_url,
        "source_page_url": source_page_url,
        "materialized_by": "scripts/materialize_news_images.py",
        "status": "failed",
        "alt": alt,
        "credit": credit,
        "error": error[:240],
    }


def materialize_image_bytes(
    raw: bytes,
    *,
    output_dir: Path,
    event_id: str,
    source_url: str,
    source_page_url: str = "",
    index: int = 1,
    alt: str = "",
    credit: str = "",
) -> dict[str, Any]:
    """Decode, normalize, resize, and atomically persist one JPEG asset."""
    try:
        with Image.open(io.BytesIO(raw)) as decoded:
            decoded.load()
            image = ImageOps.exif_transpose(decoded).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return _failed_record(
            event_id=event_id,
            source_url=source_url,
            source_page_url=source_page_url,
            alt=alt,
            credit=credit,
            error=f"decode failed: {exc}",
        )

    if image.width < 1 or image.height < 1:
        return _failed_record(
            event_id=event_id,
            source_url=source_url,
            source_page_url=source_page_url,
            alt=alt,
            credit=credit,
            error="decode failed: image has zero-sized dimensions",
        )

    if max(image.size) > MAX_EDGE:
        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)

    output_dir.mkdir(parents=True, exist_ok=True)
    asset_path = output_dir / f"{_safe_event_id(event_id)}-{index:02d}.jpg"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{asset_path.stem}-",
            suffix=".tmp",
            dir=output_dir,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
        image.save(temp_path, format="JPEG", quality=88, optimize=True)
        os.replace(temp_path, asset_path)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        return _failed_record(
            event_id=event_id,
            source_url=source_url,
            source_page_url=source_page_url,
            alt=alt,
            credit=credit,
            error=f"write failed: {exc}",
        )

    payload = asset_path.read_bytes()
    return {
        "event_id": event_id,
        "source_url": source_url,
        "source_image_url": source_url,
        "source_page_url": source_page_url,
        "materialized_by": "scripts/materialize_news_images.py",
        "status": "ready",
        "local_path": str(asset_path.resolve()),
        "mime_type": "image/jpeg",
        "width": image.width,
        "height": image.height,
        "byte_size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "alt": alt,
        "credit": credit,
    }


def download_image(source_url: str) -> bytes:
    parsed = urllib.parse.urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTP(S) URL")

    request = urllib.request.Request(source_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise ValueError("image exceeds the maximum download size")
        payload = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(payload) > MAX_DOWNLOAD_BYTES:
        raise ValueError("image exceeds the maximum download size")
    return payload


def materialize(inputs: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(inputs, start=1):
        event_id = str(item.get("event_id", "")).strip()
        source_url = str(item.get("source_image_url", item.get("source_url", ""))).strip()
        source_page_url = str(item.get("source_page_url", "")).strip()
        alt = str(item.get("alt", "")).strip()
        credit = str(item.get("credit", "")).strip()
        try:
            raw = download_image(source_url)
        except (OSError, ValueError) as exc:
            records.append(
                _failed_record(
                    event_id=event_id,
                    source_url=source_url,
                    source_page_url=source_page_url,
                    alt=alt,
                    credit=credit,
                    error=f"download failed: {exc}",
                )
            )
            continue
        records.append(
            materialize_image_bytes(
                raw,
                output_dir=output_dir,
                event_id=event_id,
                source_url=source_url,
                source_page_url=source_page_url,
                index=index,
                alt=alt,
                credit=credit,
            )
        )
    return records


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp_path, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    inputs = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(inputs, list):
        parser.error("--input must contain a JSON array")
    records = materialize(inputs, args.output_dir)
    _write_json_atomic(args.manifest, records)
    print(json.dumps({"total": len(records), "ready": sum(r["status"] == "ready" for r in records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
