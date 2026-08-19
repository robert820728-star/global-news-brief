#!/usr/bin/env python3
"""Build one auditable, dedup-ready list from validated per-source scans."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))


def normalized_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", value)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build(pool: dict, scan_dir: Path, start: datetime, end: datetime) -> dict:
    sources = pool.get("discovery_sources") or pool.get("sources", [])
    expected = {item["source_id"]: item for item in sources}
    if not expected or len(expected) != len(sources):
        raise ValueError("新聞發現來源必須至少有一個且 source_id 不得重複")

    minimum_ready = int(
        pool.get("discovery_policy", {}).get("minimum_ready_sources", len(expected))
    )
    available = {
        source_id: source
        for source_id, source in expected.items()
        if (scan_dir / f"{source_id}.json").is_file()
    }
    if len(available) < minimum_ready:
        raise ValueError(
            f"可用新聞發現清單不足：{len(available)}，最低需要 {minimum_ready}"
        )

    output = []
    completed = []
    for source_id, source in available.items():
        path = scan_dir / f"{source_id}.json"
        scan = load_json(path)
        if scan.get("source_id") != source_id:
            raise ValueError(f"來源掃描 ID 不符：{source_id}")
        completed.append(source_id)
        pages = list(scan.get("pages", [])) + list(scan.get("supplemental_pages", []))
        for page_index, page in enumerate(pages, 1):
            for raw in page.get("extracted_items", []):
                published = parse_time(str(raw.get("published_at", "")))
                if published < start or published > end:
                    continue
                title = str(raw.get("title", "")).strip()
                summary = str(raw.get("summary", "")).strip()
                hint = str(raw.get("importance_hint", "")).strip()
                url = str(raw.get("url", "")).strip()
                if not all((title, summary, hint, url)):
                    raise ValueError(f"{source_id} 第{page_index}頁候選缺少標題、摘要、重要性提示或網址")
                canon = canonical_url(url)
                norm = normalized_title(title)
                section = str(
                    raw.get("section")
                    or source.get("section")
                    or source.get("default_section")
                    or (source.get("sections") or [""])[0]
                ).strip()
                if section not in {"TWN", "CHN", "GLB"}:
                    raise ValueError(f"{source_id} 候選缺少有效板塊：{title}")
                seed = hashlib.sha256(f"{norm}|{published.date().isoformat()}".encode()).hexdigest()[:24]
                cid = hashlib.sha256(f"{source_id}|{canon}|{published.isoformat()}".encode()).hexdigest()[:20]
                output.append({
                    "candidate_id": cid,
                    "source_id": source_id,
                    "source_name": source["name"],
                    "section": section,
                    "title": title,
                    "summary": summary,
                    "published_at": published.isoformat(),
                    "url": url,
                    "categories": raw.get("categories") or source.get("categories", []),
                    "importance_hint": hint,
                    "acquisition_route": raw.get("acquisition_route") or scan.get("collector"),
                    "canonical_url": canon,
                    "normalized_title": norm,
                    "dedup_seed": seed,
                    "snapshot_path": page.get("snapshot_path", ""),
                    "page_index": page_index
                })
    output.sort(key=lambda item: (item["published_at"], item["source_id"], item["canonical_url"]), reverse=True)
    return {
        "schema_version": "1.0.0",
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "source_count": len(completed),
        "sources": sorted(completed),
        "items": output
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pool", required=True)
    parser.add_argument("--scan-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    args = parser.parse_args()
    result = build(load_json(Path(args.source_pool)), Path(args.scan_dir), parse_time(args.window_start), parse_time(args.window_end))
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
