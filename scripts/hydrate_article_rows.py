#!/usr/bin/env python3
"""Fetch and terminally classify bounded article-body hydration rows."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 20
LOCAL_TZ = timezone(timedelta(hours=8))
ROW_ID_RE = re.compile(r"^row-[0-9a-f]{24}$")

META_DATE_KEYS = {
    "article:published_time",
    "article:modified_time",
    "datepublished",
    "datemodified",
    "publishdate",
    "pubdate",
    "publish_time",
    "published_time",
    "release_date",
    "date",
}
JSON_DATE_KEYS = ("datePublished", "dateModified")
HEADER_DATE_PATTERNS = (
    re.compile(
        r"(?P<label>發稿時間|发布时间|發佈時間|發布時間|更新时间|更新時間|刊登時間)"
        r"\s*[:：]?\s*(?P<value>20\d{2}[年/-]\d{1,2}[月/-]\d{1,2}日?"
        r"(?:\s+|T)\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:[+-]\d{2}:?\d{2}|Z))?)"
    ),
    re.compile(
        r"(?P<value>20\d{2}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}(?::\d{2})?)"
        r"\s*(?:来源|來源|Source)\s*[:：]"
    ),
)


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self.jsonld_parts: list[str] = []
        self._in_jsonld = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag.lower() == "meta":
            self.meta.append(attr)
        if tag.lower() == "script" and "ld+json" in attr.get("type", "").lower():
            self._in_jsonld = True
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_jsonld:
            self.jsonld_parts.append("".join(self._script_parts))
            self._in_jsonld = False
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._script_parts.append(data)
        else:
            value = data.strip()
            if value:
                self.text_parts.append(value)


def _decode_html(data: bytes, content_type: str = "") -> str:
    charset_match = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9._-]+)", content_type, re.I)
    candidates = [charset_match.group(1)] if charset_match else []
    head = data[:8192].decode("ascii", errors="ignore")
    meta_match = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9._-]+)", head, re.I)
    if meta_match:
        candidates.append(meta_match.group(1))
    candidates.extend(["utf-8", "gb18030", "big5"])
    seen: set[str] = set()
    for encoding in candidates:
        if not encoding:
            continue
        key = encoding.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _iter_json_date_values(value: Any):
    if isinstance(value, dict):
        for key in JSON_DATE_KEYS:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                yield key, item.strip()
        for item in value.values():
            yield from _iter_json_date_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_date_values(item)


def _normalize_datetime(value: str) -> datetime | None:
    raw = unescape(value).strip()
    raw = re.sub(r"\s+", " ", raw)
    iso = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed
    except ValueError:
        pass
    normalized = (
        raw.replace("年", "-")
        .replace("月", "-")
        .replace("日", " ")
        .replace("/", "-")
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    match = re.search(
        r"(?P<y>20\d{2})-(?P<m>\d{1,2})-(?P<d>\d{1,2})"
        r"(?:[ T](?P<h>\d{1,2}):(?P<min>\d{2})(?::(?P<s>\d{2}))?)?",
        normalized,
    )
    if not match:
        return None
    return datetime(
        int(match.group("y")),
        int(match.group("m")),
        int(match.group("d")),
        int(match.group("h") or 0),
        int(match.group("min") or 0),
        int(match.group("s") or 0),
        tzinfo=LOCAL_TZ,
    )


def extract_article_timestamp(html_text: str) -> tuple[datetime | None, str | None]:
    parser = _ArticleParser()
    parser.feed(html_text)

    for script in parser.jsonld_parts:
        try:
            value = json.loads(script.strip())
        except (json.JSONDecodeError, TypeError):
            continue
        for key, raw in _iter_json_date_values(value):
            parsed = _normalize_datetime(raw)
            if parsed is not None:
                return parsed, f"jsonld:{key}={raw}"

    for meta in parser.meta:
        key = (
            meta.get("property")
            or meta.get("name")
            or meta.get("itemprop")
            or ""
        ).strip().lower()
        content = meta.get("content", "").strip()
        if key in META_DATE_KEYS and content:
            parsed = _normalize_datetime(content)
            if parsed is not None:
                return parsed, f"meta:{key}={content}"

    header_text = " ".join(parser.text_parts[:250])
    for pattern in HEADER_DATE_PATTERNS:
        match = pattern.search(header_text)
        if not match:
            continue
        raw = match.group("value")
        parsed = _normalize_datetime(raw)
        if parsed is not None:
            label = match.groupdict().get("label") or "header"
            return parsed, f"text:{label}={raw}"
    return None, None


def _public_https(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and parsed.port in {None, 443}
    )


def _fetch(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[bytes, str, int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GlobalNewsBrief/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        if not _public_https(final_url):
            raise ValueError("article redirect target is not public HTTPS")
        status = int(getattr(response, "status", 200))
        content_type = str(response.headers.get("Content-Type", ""))
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("article response exceeds maximum size")
        if "html" not in content_type.lower() and not data.lstrip().startswith((b"<", b"\xef\xbb\xbf<")):
            raise ValueError(f"article response is not HTML: {content_type}")
        return data, final_url, status, content_type


def _terminal_unresolved(row: dict, reason: str, attempts: list[dict]) -> dict:
    url = str(row["canonical_url"])
    return {
        "row_id": row["row_id"],
        "article_body_published_at": None,
        "article_body_timestamp_evidence": None,
        "article_body_evidence_url": url,
        "content_sha256": None,
        "admission_status": "unresolved_exhausted",
        "model_evidence": {
            "review_status": "unresolved_exhausted",
            "reason": reason,
            "evidence_refs": [url],
        },
        "hydration_attempts": attempts,
    }


def hydrate_row(row: dict, *, window_start: datetime, window_end: datetime) -> dict:
    url = str(row["canonical_url"])
    attempts: list[dict] = []
    try:
        data, final_url, status, content_type = _fetch(url)
        content_hash = hashlib.sha256(data).hexdigest()
        attempts.append({
            "url": url,
            "actual_url": final_url,
            "status": "fetched",
            "http_status": status,
            "content_sha256": content_hash,
        })
    except (OSError, ValueError, urllib.error.URLError) as exc:
        attempts.append({
            "url": url,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        })
        return _terminal_unresolved(
            row,
            "Article body could not be fetched through the bounded hydration transport.",
            attempts,
        )

    html_text = _decode_html(data, content_type)
    published_at, timestamp_evidence = extract_article_timestamp(html_text)
    if published_at is None or timestamp_evidence is None:
        result = _terminal_unresolved(
            row,
            "Article body was fetched, but no attributable publication/update timestamp could be established.",
            attempts,
        )
        result["article_body_evidence_url"] = final_url
        result["content_sha256"] = content_hash
        return result

    published_at = published_at.astimezone(window_start.tzinfo or timezone.utc)
    inside = window_start <= published_at <= window_end
    status_name = "content_ready" if inside else "outside_window"
    review_status = "pending_semantic_review" if inside else "outside_window"
    reason = (
        "Article body and authoritative timestamp were persisted."
        if inside
        else "Article-body timestamp places this listing lead outside the exact run window."
    )
    return {
        "row_id": row["row_id"],
        "article_body_published_at": published_at.isoformat(),
        "article_body_timestamp_evidence": timestamp_evidence,
        "article_body_evidence_url": final_url,
        "content_sha256": content_hash,
        "admission_status": status_name,
        "model_evidence": {
            "review_status": review_status,
            "reason": reason,
            "evidence_refs": [final_url],
        },
        "hydration_attempts": attempts,
    }


def hydrate_rows(
    rows: list[dict],
    *,
    window_start: datetime,
    window_end: datetime,
) -> list[dict]:
    return [
        hydrate_row(row, window_start=window_start, window_end=window_end)
        for row in rows
    ]
