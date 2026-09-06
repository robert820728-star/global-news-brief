#!/usr/bin/env python3
"""Hydrate a bounded set of source rows with recoverable article-body evidence."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

UA = "Mozilla/5.0 CodexNewsValidation/1.0"
MAX_RESPONSE_BYTES = 8_000_000
DATE_KEYS = {
    "article:published_time", "article:modified_time", "datepublished", "datemodified",
    "pubdate", "publishdate", "date", "dcterms.date", "parsely-pub-date",
}
SOURCE_ROOTS = {"cna": "cna.com.tw", "chinanews": "chinanews.com.cn"}


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag.lower() == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key in DATE_KEYS and a.get("content"):
                self.dates.append(a["content"])
        if tag.lower() == "time" and a.get("datetime"):
            self.dates.append(a["datetime"])


def parse_dt(raw: str) -> datetime | None:
    s = html.unescape(raw).strip().replace("Z", "+00:00")
    for candidate in (s, s.replace("/", "-")):
        try:
            d = datetime.fromisoformat(candidate)
            if d.tzinfo is not None:
                return d
        except ValueError:
            pass
    m = re.search(
        r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?",
        s,
    )
    if m:
        return datetime.fromisoformat(
            f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}T{int(m[4]):02d}:{int(m[5]):02d}:{int(m[6] or 0):02d}+08:00"
        )
    return None


def body_date(text: str) -> tuple[datetime | None, str | None]:
    p = MetaParser()
    try:
        p.feed(text)
    except Exception:
        pass
    candidates = list(p.dates)
    candidates += re.findall(r'"datePublished"\s*:\s*"([^"]+)"', text, flags=re.I)
    candidates += re.findall(r'"dateModified"\s*:\s*"([^"]+)"', text, flags=re.I)
    candidates += re.findall(
        r"(20\d{2}[年/\-.]\d{1,2}[月/\-.]\d{1,2}日?\s+\d{1,2}:\d{2}(?::\d{2})?)",
        text,
    )
    for raw in candidates:
        d = parse_dt(raw)
        if d:
            return d, raw
    return None, None


def _same_source(url: str, source_id: str) -> bool:
    root = SOURCE_ROOTS.get(source_id)
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
        port = parts.port
    except ValueError:
        return False
    return bool(
        root
        and parts.scheme.lower() == "https"
        and parts.username is None
        and parts.password is None
        and port in {None, 443}
        and (host == root or host.endswith("." + root))
    )


def _decode(data: bytes, content_type: str) -> str:
    match = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9._-]+)", content_type, flags=re.I)
    encodings = [match.group(1)] if match else []
    head = data[:8192].decode("ascii", errors="ignore")
    meta = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9._-]+)", head, flags=re.I)
    if meta:
        encodings.append(meta.group(1))
    encodings += ["utf-8", "gb18030", "big5"]
    seen: set[str] = set()
    for encoding in encodings:
        key = encoding.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def fetch(url: str, source_id: str) -> tuple[bytes, str, str]:
    if not _same_source(url, source_id):
        raise ValueError(f"hydration URL must remain on configured {source_id} source site")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        final = r.geturl()
        ctype_header = str(r.headers.get("Content-Type", ""))
        ctype = r.headers.get_content_type()
        data = r.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("article response exceeds maximum size")
    if ctype not in {"text/html", "application/xhtml+xml"}:
        raise ValueError(f"unsupported content type {ctype}")
    if not _same_source(final, source_id):
        raise ValueError("article redirect left the configured same-source site")
    return data, final, ctype_header or ctype


def hydrate(
    source_candidates: dict,
    row_ids: list[str],
    start: datetime,
    end: datetime,
    *,
    fetch_overrides: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    by_id = {
        str(x.get("row_id")): x
        for x in source_candidates.get("items", [])
        if isinstance(x, dict)
    }
    if len(row_ids) != len(set(row_ids)) or any(r not in by_id for r in row_ids):
        raise ValueError("row_ids must be unique and belong to source-candidates")
    overrides = fetch_overrides or {}
    if set(overrides) - set(row_ids):
        raise ValueError("fetch_overrides may only reference this batch row_ids")

    out = []
    for row_id in row_ids:
        item = by_id[row_id]
        canonical_url = str(item["canonical_url"])
        source_id = str(item["source_id"])
        requested_url = str(overrides.get(row_id) or canonical_url)
        base = {
            "row_id": row_id,
            "candidate_id": item["candidate_id"],
            "canonical_url": canonical_url,
            "requested_url": requested_url,
            "source_id": source_id,
        }
        try:
            data, final, ctype = fetch(requested_url, source_id)
            content_hash = hashlib.sha256(data).hexdigest()
            text = _decode(data, ctype)
            d, raw = body_date(text)
            if d is None:
                out.append({
                    **base,
                    "status": "unresolved",
                    "actual_url": final,
                    "content_type": ctype,
                    "content_sha256": content_hash,
                    "article_body_published_at": None,
                    "article_body_timestamp_evidence": None,
                    "article_body_evidence_url": final,
                    "error": "authoritative article-body publication timestamp not found; same-source recovery remains",
                })
                continue
            record = {
                **base,
                "actual_url": final,
                "content_type": ctype,
                "content_sha256": content_hash,
                "article_body_published_at": d.isoformat(),
                "article_body_timestamp_evidence": raw,
                "article_body_evidence_url": final,
                "error": None,
            }
            record["status"] = "content_ready" if start <= d <= end else "outside_window"
            out.append(record)
        except Exception as e:
            out.append({
                **base,
                "status": "unresolved",
                "actual_url": None,
                "content_type": None,
                "content_sha256": None,
                "article_body_published_at": None,
                "article_body_timestamp_evidence": None,
                "article_body_evidence_url": None,
                "error": f"{type(e).__name__}: {e}"[:1000],
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-candidates", required=True)
    ap.add_argument("--row-ids", required=True)
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--fetch-overrides")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    src = json.loads(Path(a.source_candidates).read_text(encoding="utf-8"))
    ids = json.loads(Path(a.row_ids).read_text(encoding="utf-8"))
    if not isinstance(ids, list) or not 1 <= len(ids) <= 20:
        raise SystemExit("row-id batch must contain 1..20 rows")
    overrides = {}
    if a.fetch_overrides:
        overrides = json.loads(Path(a.fetch_overrides).read_text(encoding="utf-8"))
        if not isinstance(overrides, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in overrides.items()):
            raise SystemExit("fetch-overrides must be a JSON object of row_id -> URL")
    rows = hydrate(
        src,
        [str(x) for x in ids],
        datetime.fromisoformat(a.window_start.replace("Z", "+00:00")),
        datetime.fromisoformat(a.window_end.replace("Z", "+00:00")),
        fetch_overrides=overrides,
    )
    p = Path(a.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"schema_version": "1.1", "rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
