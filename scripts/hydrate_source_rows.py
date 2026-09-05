#!/usr/bin/env python3
"""Hydrate a bounded set of source rows with article-body evidence."""
from __future__ import annotations

import argparse, hashlib, html, json, re, urllib.error, urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

UA = "Mozilla/5.0 CodexNewsValidation/1.0"
DATE_KEYS = {"article:published_time", "datepublished", "pubdate", "publishdate", "date", "dcterms.date", "parsely-pub-date"}

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.dates=[]
    def handle_starttag(self, tag, attrs):
        a={str(k).lower(): str(v or "") for k,v in attrs}
        if tag.lower()=="meta":
            key=(a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key in DATE_KEYS and a.get("content"): self.dates.append(a["content"])
        if tag.lower()=="time" and a.get("datetime"): self.dates.append(a["datetime"])

def parse_dt(raw: str) -> datetime | None:
    s=html.unescape(raw).strip().replace("Z", "+00:00")
    for candidate in (s, s.replace("/", "-")):
        try:
            d=datetime.fromisoformat(candidate)
            if d.tzinfo is not None: return d
        except ValueError: pass
    m=re.search(r"(20\d{2})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?\s*(\d{1,2}):(\d{2})", s)
    if m:
        # CNA/ChinaNews are UTC+8 publications.
        return datetime.fromisoformat(f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}T{int(m[4]):02d}:{int(m[5]):02d}:00+08:00")
    return None

def body_date(text: str) -> tuple[datetime | None, str | None]:
    p=MetaParser()
    try: p.feed(text)
    except Exception: pass
    candidates=list(p.dates)
    candidates += re.findall(r'"datePublished"\s*:\s*"([^"]+)"', text, flags=re.I)
    candidates += re.findall(r'(20\d{2}[年/\-.]\d{1,2}[月/\-.]\d{1,2}日?\s+\d{1,2}:\d{2})', text)
    for raw in candidates:
        d=parse_dt(raw)
        if d: return d, raw
    return None, None

def fetch(url: str) -> tuple[bytes, str, str]:
    req=urllib.request.Request(url, headers={"User-Agent":UA, "Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=25) as r:
        final=r.geturl(); ctype=r.headers.get_content_type(); data=r.read(4_000_000)
    if ctype not in {"text/html", "application/xhtml+xml"}: raise ValueError(f"unsupported content type {ctype}")
    return data, final, ctype

def hydrate(source_candidates: dict, row_ids: list[str], start: datetime, end: datetime) -> list[dict[str, Any]]:
    by_id={str(x.get("row_id")):x for x in source_candidates.get("items",[]) if isinstance(x,dict)}
    if len(row_ids)!=len(set(row_ids)) or any(r not in by_id for r in row_ids): raise ValueError("row_ids must be unique and belong to source-candidates")
    out=[]
    for row_id in row_ids:
        item=by_id[row_id]; url=str(item["canonical_url"]); base={"row_id":row_id,"candidate_id":item["candidate_id"],"requested_url":url}
        try:
            data, final, ctype=fetch(url); text=data.decode("utf-8",errors="replace"); d, raw=body_date(text)
            if d is None: raise ValueError("authoritative article-body publication timestamp not found")
            if not start <= d <= end: raise ValueError(f"article-body timestamp outside run window: {d.isoformat()}")
            out.append({**base,"status":"content_ready","actual_url":final,"content_type":ctype,"content_sha256":hashlib.sha256(data).hexdigest(),"article_body_published_at":d.isoformat(),"article_body_timestamp_evidence":raw,"article_body_evidence_url":final,"error":None})
        except Exception as e:
            out.append({**base,"status":"unresolved_exhausted","actual_url":None,"content_type":None,"content_sha256":None,"article_body_published_at":None,"article_body_timestamp_evidence":None,"article_body_evidence_url":None,"error":f"{type(e).__name__}: {e}"[:1000]})
    return out

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--source-candidates",required=True); ap.add_argument("--row-ids",required=True); ap.add_argument("--window-start",required=True); ap.add_argument("--window-end",required=True); ap.add_argument("--output",required=True)
    a=ap.parse_args(); src=json.loads(Path(a.source_candidates).read_text(encoding="utf-8")); ids=json.loads(Path(a.row_ids).read_text(encoding="utf-8"));
    if not isinstance(ids,list) or not 1<=len(ids)<=20: raise SystemExit("row-id batch must contain 1..20 rows")
    rows=hydrate(src,[str(x) for x in ids],datetime.fromisoformat(a.window_start.replace("Z","+00:00")),datetime.fromisoformat(a.window_end.replace("Z","+00:00")))
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps({"schema_version":"1.0","rows":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(p); return 0
if __name__=="__main__": raise SystemExit(main())
